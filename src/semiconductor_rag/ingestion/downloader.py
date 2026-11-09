"""스트리밍 다운로드, 임시 파일 정리, 제한된 재시도."""

import math
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from semiconductor_rag.ingestion.errors import IngestionError

RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Download:
    path: Path
    attempts: int
    http_status: int
    final_url: str
    content_type: str


def validate_url(url: str) -> None:
    try:
        parts = urlsplit(url)
        valid = parts.scheme in {"http", "https"} and parts.hostname and not parts.username
        _ = parts.port
    except ValueError:
        valid = False
    if not valid:
        raise IngestionError("invalid_url", "사용자 정보 없는 HTTP(S) URL이 필요합니다")


def retry_delay(value: str | None, attempt: int) -> float:
    fallback = float(2 ** (attempt - 1))
    if not value:
        return fallback
    try:
        delay = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            delay = (when - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return fallback
    if delay > 60:
        raise IngestionError("retry_after_limit", "Retry-After가 대기 한도 60초를 초과합니다")
    return delay if 0 <= delay <= 60 else fallback


def _download(client, url, temp_dir, *, max_attempts, timeout, max_bytes, sleep):
    for attempt in range(1, max_attempts + 1):
        temporary = None
        keep = False
        delay = float(2 ** (attempt - 1))
        try:
            with client.stream("GET", url, follow_redirects=True, timeout=timeout) as response:
                status = response.status_code
                final_url = str(response.url)
                if status in RETRY_STATUSES and attempt < max_attempts:
                    try:
                        delay = retry_delay(response.headers.get("Retry-After"), attempt)
                    except IngestionError as exc:
                        raise IngestionError(
                            exc.code,
                            str(exc),
                            attempts=attempt,
                            http_status=status,
                            final_url=final_url,
                        ) from exc
                elif not 200 <= status < 300:
                    raise IngestionError(
                        "http_error",
                        f"HTTP {status}",
                        attempts=attempt,
                        http_status=status,
                        final_url=final_url,
                    )
                else:
                    with tempfile.NamedTemporaryFile(
                        dir=temp_dir, suffix=".part", delete=False
                    ) as file:
                        temporary = Path(file.name)
                        size = 0
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > max_bytes:
                                raise IngestionError(
                                    "file_too_large",
                                    "다운로드 크기 한도 초과",
                                    attempts=attempt,
                                    http_status=status,
                                    final_url=final_url,
                                )
                            file.write(chunk)
                    keep = True
                    return Download(
                        temporary,
                        attempt,
                        status,
                        final_url,
                        response.headers.get("Content-Type", ""),
                    )
        except (httpx.TransportError, httpx.TooManyRedirects) as exc:
            if attempt == max_attempts or isinstance(exc, httpx.TooManyRedirects):
                code = "timeout" if isinstance(exc, httpx.TimeoutException) else "network_error"
                raise IngestionError(code, str(exc), attempts=attempt) from exc
        except httpx.InvalidURL as exc:
            raise IngestionError("invalid_url", str(exc), attempts=attempt) from exc
        except httpx.RequestError as exc:
            raise IngestionError("response_error", str(exc), attempts=attempt) from exc
        except OSError as exc:
            raise IngestionError("io_error", str(exc), attempts=attempt) from exc
        finally:
            if temporary is not None and not keep:
                temporary.unlink(missing_ok=True)
        sleep(delay)
    raise AssertionError("download attempts exhausted")


def download_pdf(
    url: str,
    temp_dir: Path,
    *,
    client=None,
    max_attempts=3,
    timeout=30.0,
    max_bytes=64 * 1024 * 1024,
    sleep=time.sleep,
) -> Download:
    validate_url(url)
    if max_attempts < 1 or not math.isfinite(timeout) or timeout <= 0 or max_bytes < 1:
        raise ValueError("시도 횟수·타임아웃·크기 한도는 양수여야 합니다")
    temp_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "max_attempts": max_attempts,
        "timeout": timeout,
        "max_bytes": max_bytes,
        "sleep": sleep,
    }
    if client is not None:
        return _download(client, url, temp_dir, **options)
    with httpx.Client(trust_env=False, max_redirects=10) as owned_client:
        return _download(owned_client, url, temp_dir, **options)
