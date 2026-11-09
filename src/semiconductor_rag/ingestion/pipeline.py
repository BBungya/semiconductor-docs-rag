"""입력 검증, 로컬/HTTP 수집과 상태·버전 기록을 연결한다."""

import math
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4

from semiconductor_rag.ingestion.downloader import download_pdf
from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.manifest import load_manifest
from semiconductor_rag.ingestion.storage import Store, now
from semiconductor_rag.ingestion.validation import validate_file, validate_local


def finish_report(report):
    counts = Counter(result["status"] for result in report["results"])
    report["summary"] = dict(counts)
    for name, status in (
        ("new_documents", "registered"),
        ("changed_documents", "changed"),
        ("unchanged_documents", "unchanged"),
        ("failed_documents", "failed"),
        ("invalid_documents", "invalid"),
        ("skipped_documents", "skipped"),
    ):
        report[name] = [
            item["document_id"] for item in report["results"] if item["status"] == status
        ]
    report["exit_code"] = 1 if counts["failed"] or counts["invalid"] else 0
    return report


def choose_entries(entries, state, document_id, retry_failed):
    if document_id is not None:
        entries = [entry for entry in entries if entry.document_id == document_id]
        if not entries:
            raise IngestionError("unknown_document", f"목록에 없는 문서 ID: {document_id}")
    if retry_failed:
        entries = [
            entry
            for entry in entries
            if state["last_attempts"].get(entry.document_id, {}).get("status")
            in {"failed", "invalid"}
        ]
    return entries


def run_ingestion(
    manifest_path: str | Path,
    project_root: str | Path,
    *,
    dry_run=False,
    document_id=None,
    retry_failed=False,
    client=None,
    sleep=time.sleep,
    max_attempts=3,
    timeout=30.0,
    max_bytes=64 * 1024 * 1024,
) -> dict:
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise IngestionError("invalid_root", "프로젝트 루트 폴더가 없습니다")
    if max_attempts < 1 or not math.isfinite(timeout) or timeout <= 0 or max_bytes < 1:
        raise IngestionError("invalid_config", "횟수·타임아웃·크기 한도는 양수여야 합니다")
    entries = load_manifest(manifest_path)
    if document_id is not None and not any(entry.document_id == document_id for entry in entries):
        raise IngestionError("unknown_document", f"목록에 없는 문서 ID: {document_id}")
    store = Store(root)
    report = {
        "schema_version": 1,
        "run_id": None if dry_run else uuid4().hex,
        "started_at": now(),
        "finished_at": None,
        "complete": False,
        "dry_run": dry_run,
        "manifest": str(Path(manifest_path).resolve()),
        "results": [],
    }

    if dry_run:
        selected = choose_entries(entries, store.read(), document_id, retry_failed)
        for entry in selected:
            report["results"].append(
                {
                    "line_number": entry.line_number,
                    "document_id": entry.document_id,
                    "status": {
                        "local": "planned_local",
                        "download": "planned_download",
                        "skip": "skipped",
                        "error": "invalid",
                    }[entry.action],
                    "reason": entry.reason,
                }
            )
        report.update(complete=True, finished_at=now())
        return finish_report(report)

    with store.lock():
        state = store.read()
        selected = choose_entries(entries, state, document_id, retry_failed)
        finish_report(report)
        store.checkpoint(state, report)
        for entry in selected:
            result = {
                "line_number": entry.line_number,
                "document_id": entry.document_id,
                "timestamp": now(),
                "run_id": report["run_id"],
                "attempts": 0,
                "reason": entry.reason,
                "source_url": entry.data.get("source_url", ""),
            }
            temporary = None
            if entry.action in {"skip", "error"}:
                result["status"] = "skipped" if entry.action == "skip" else "invalid"
                if entry.action == "error":
                    result["error_code"] = "invalid_manifest_row"
            else:
                try:
                    if entry.action == "local":
                        source, info = validate_local(
                            root, entry.data["local_path"], max_bytes=max_bytes
                        )
                    else:
                        downloaded = download_pdf(
                            entry.data["download_url"],
                            store.temp,
                            client=client,
                            sleep=sleep,
                            max_attempts=max_attempts,
                            timeout=timeout,
                            max_bytes=max_bytes,
                        )
                        temporary = source = downloaded.path
                        result.update(
                            attempts=downloaded.attempts,
                            http_status=downloaded.http_status,
                            final_url=downloaded.final_url,
                            content_type=downloaded.content_type,
                        )
                        info = validate_file(source, ".pdf", max_bytes=max_bytes)
                    store.register(state, entry, source, info, result)
                except IngestionError as exc:
                    result.update(
                        status="failed",
                        error_code=exc.code,
                        error_message=str(exc),
                        attempts=exc.attempts or result["attempts"],
                    )
                    if exc.http_status is not None:
                        result["http_status"] = exc.http_status
                    if exc.final_url is not None:
                        result["final_url"] = exc.final_url
                except OSError as exc:
                    result.update(status="failed", error_code="io_error", error_message=str(exc))
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
            if entry.document_id and result["status"] != "skipped":
                state["last_attempts"][entry.document_id] = result.copy()
            report["results"].append(result)
            finish_report(report)
            store.checkpoint(state, report)
        report.update(complete=True, finished_at=now())
        finish_report(report)
        store.checkpoint(state, report)
    return report
