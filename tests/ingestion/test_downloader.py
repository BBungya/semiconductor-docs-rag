import httpx
import pytest

from semiconductor_rag.ingestion.downloader import download_pdf, retry_delay
from semiconductor_rag.ingestion.errors import IngestionError


def test_stream_download(tmp_path, pdf_bytes):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=pdf_bytes, headers={"Content-Type": "application/pdf"}
            )
        )
    ) as client:
        result = download_pdf("https://example.test/file.pdf", tmp_path, client=client)
    assert result.path.read_bytes() == pdf_bytes
    assert result.path.suffix == ".part"
    assert result.attempts == 1


def test_redirect_records_final_url(tmp_path, pdf_bytes):
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "/new"})
        return httpx.Response(200, content=pdf_bytes)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_pdf("https://example.test/old", tmp_path, client=client)
    assert result.final_url == "https://example.test/new"


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_temporary_status_retries(tmp_path, pdf_bytes, status):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "0"})
        return httpx.Response(200, content=pdf_bytes)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_pdf(
            "https://example.test/doc", tmp_path, client=client, sleep=waits.append
        )
    assert result.attempts == 2
    assert len(calls) == 2
    assert waits == [0]


@pytest.mark.parametrize("status", [401, 403, 404, 501])
def test_permanent_status_does_not_retry(tmp_path, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf("https://example.test/doc", tmp_path, client=client)
    assert exc.value.http_status == status
    assert exc.value.attempts == 1
    assert len(calls) == 1
    assert not list(tmp_path.glob("*.part"))


def test_timeout_exhaustion(tmp_path):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf("https://example.test/doc", tmp_path, client=client, sleep=waits.append)
    assert exc.value.code == "timeout"
    assert exc.value.attempts == 3
    assert len(calls) == 3
    assert waits == [1, 2]


def test_broken_stream_cleans_partial_file(tmp_path):
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b"partial"
            raise httpx.ReadError("broken")

    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Broken()))
        ) as client,
        pytest.raises(IngestionError),
    ):
        download_pdf(
            "https://example.test/doc",
            tmp_path,
            client=client,
            max_attempts=2,
            sleep=lambda delay: None,
        )
    assert not list(tmp_path.glob("*.part"))


def test_oversized_download_cleanup(tmp_path):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"123456"))
        ) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf("https://example.test/doc", tmp_path, client=client, max_bytes=4)
    assert exc.value.code == "file_too_large"
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize("url", ["file:///x", "not a url", "https://user:pass@example.test/doc"])
def test_invalid_url_has_no_request(tmp_path, url):
    with pytest.raises(IngestionError) as exc:
        download_pdf(url, tmp_path)
    assert exc.value.code == "invalid_url"


def test_long_retry_after_is_not_ignored(tmp_path):
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, headers={"Retry-After": "3600"})
            )
        ) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf("https://example.test/doc", tmp_path, client=client)
    assert exc.value.code == "retry_after_limit"


def test_retry_after_fallback():
    assert retry_delay("invalid", 2) == 2
    assert retry_delay("NaN", 1) == 1


def test_timeout_then_success(tmp_path, pdf_bytes):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("temporary timeout", request=request)
        return httpx.Response(200, content=pdf_bytes)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_pdf(
            "https://example.test/doc", tmp_path, client=client, sleep=waits.append
        )
    assert result.attempts == 2
    assert waits == [1]


def test_invalid_encoded_response_is_reported(tmp_path):
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=b"not gzip", headers={"Content-Encoding": "gzip"}
                )
            )
        ) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf("https://example.test/doc", tmp_path, client=client)
    assert exc.value.code == "response_error"
    assert not list(tmp_path.glob("*.part"))


def test_retries_stop_after_configured_attempts(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(IngestionError) as exc,
    ):
        download_pdf(
            "https://example.test/doc",
            tmp_path,
            client=client,
            max_attempts=2,
            sleep=lambda delay: None,
        )
    assert len(calls) == exc.value.attempts == 2
    assert exc.value.http_status == 503
