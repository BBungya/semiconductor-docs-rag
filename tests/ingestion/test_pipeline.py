import json

import httpx
import pytest

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.pipeline import run_ingestion
from semiconductor_rag.ingestion.storage import Store


def test_local_registration_repeat_and_change(tmp_path, make_row, write_sources, put_local):
    row = make_row()
    path = put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    before = manifest.read_bytes()
    first = run_ingestion(manifest, tmp_path)
    assert first["summary"] == {"registered": 1}
    second = run_ingestion(manifest, tmp_path)
    assert second["summary"] == {"unchanged": 1}
    path.write_text("# second version", encoding="utf-8")
    third = run_ingestion(manifest, tmp_path)
    assert third["changed_documents"] == ["example-1"]
    store = Store(tmp_path)
    state = store.read()
    versions = state["documents"]["example-1"]["versions"]
    assert len(versions) == 2
    assert all((tmp_path / version["file_path"]).is_file() for version in versions)
    assert len(list(store.blobs.iterdir())) == 2
    # Returning to an earlier content version must not append a duplicate version.
    path.write_text("# 가상 문서\n첫 번째 버전", encoding="utf-8")
    assert run_ingestion(manifest, tmp_path)["summary"] == {"changed": 1}
    assert len(store.read()["documents"]["example-1"]["versions"]) == 2
    assert manifest.read_bytes() == before


def test_same_content_keeps_document_links_without_duplicate_blob(
    tmp_path, make_row, write_sources, put_local
):
    rows = [make_row("a"), make_row("b")]
    for row in rows:
        put_local(tmp_path, row)
    run_ingestion(write_sources(tmp_path, rows), tmp_path)
    store = Store(tmp_path)
    assert set(store.read()["documents"]) == {"a", "b"}
    assert len(list(store.blobs.iterdir())) == 1


def test_failed_update_preserves_current_version(tmp_path, make_row, write_sources, put_local):
    row = make_row()
    local = put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    run_ingestion(manifest, tmp_path)
    before = Store(tmp_path).read()["documents"]["example-1"].copy()
    local.write_bytes(b"")
    report = run_ingestion(manifest, tmp_path)
    assert report["exit_code"] == 1
    assert report["results"][0]["error_code"] == "empty_file"
    assert Store(tmp_path).read()["documents"]["example-1"] == before


def test_missing_local_continues_and_retry_only_failed(
    tmp_path, make_row, write_sources, put_local
):
    rows = [make_row("missing"), make_row("good")]
    put_local(tmp_path, rows[1])
    manifest = write_sources(tmp_path, rows)
    first = run_ingestion(manifest, tmp_path)
    assert first["summary"] == {"failed": 1, "registered": 1}
    put_local(tmp_path, rows[0])
    retry = run_ingestion(manifest, tmp_path, retry_failed=True)
    assert retry["new_documents"] == ["missing"]
    assert len(retry["results"]) == 1
    assert not run_ingestion(manifest, tmp_path, retry_failed=True)["results"]


def test_retry_respects_new_hold_status(tmp_path, make_row, write_sources):
    row = make_row()
    manifest = write_sources(tmp_path, [row])
    run_ingestion(manifest, tmp_path)
    row["selection_status"] = "deferred_rights_review"
    write_sources(tmp_path, [row])
    assert run_ingestion(manifest, tmp_path, retry_failed=True)["summary"] == {"skipped": 1}


def test_dry_run_has_no_files_or_requests(tmp_path, make_row, write_sources):
    row = make_row(
        "external",
        source_kind="external_official_candidate",
        selection_status="selected_for_download",
        download_url="https://example.test/doc",
    )
    manifest = write_sources(tmp_path, [row])
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    def unexpected(request):
        pytest.fail("dry-run must not request")

    with httpx.Client(transport=httpx.MockTransport(unexpected)) as client:
        report = run_ingestion(manifest, tmp_path, dry_run=True, client=client)
    assert report["summary"] == {"planned_download": 1}
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_held_external_has_no_request(tmp_path, make_row, write_sources):
    row = make_row(
        source_kind="external_official_candidate",
        download_status="downloaded",
        selection_status="deferred_rights_review",
    )

    def unexpected(request):
        pytest.fail("held source must not request")

    with httpx.Client(transport=httpx.MockTransport(unexpected)) as client:
        report = run_ingestion(write_sources(tmp_path, [row]), tmp_path, client=client)
    assert report["summary"] == {"skipped": 1}
    assert not Store(tmp_path).blobs.exists()


def test_download_same_url_changed_content_and_invalid_update(
    tmp_path, make_row, write_sources, pdf_bytes
):
    row = make_row(
        source_kind="external_official_candidate",
        selection_status="selected_for_download",
        download_url="https://example.test/doc",
    )
    manifest = write_sources(tmp_path, [row])
    content = [pdf_bytes]
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=content[0], headers={"Content-Type": "application/octet-stream"}
            )
        )
    ) as client:
        assert run_ingestion(manifest, tmp_path, client=client)["summary"] == {"registered": 1}
        assert run_ingestion(manifest, tmp_path, client=client)["summary"] == {"unchanged": 1}
        content[0] = pdf_bytes + b"\n% a new file revision\n"
        changed = run_ingestion(manifest, tmp_path, client=client)
        assert changed["summary"] == {"changed": 1}
        before = Store(tmp_path).read()["documents"]["example-1"].copy()
        content[0] = b"<html>Access denied</html>"
        failed = run_ingestion(manifest, tmp_path, client=client)
    assert failed["results"][0]["error_code"] == "unexpected_content"
    assert failed["results"][0]["attempts"] == 1
    assert Store(tmp_path).read()["documents"]["example-1"] == before
    assert not list(Store(tmp_path).temp.glob("*.part"))


def test_duplicate_ids_register_nothing(tmp_path, make_row, write_sources, put_local):
    row = make_row()
    put_local(tmp_path, row)
    report = run_ingestion(write_sources(tmp_path, [row, row]), tmp_path)
    assert report["summary"] == {"invalid": 2}
    assert not Store(tmp_path).read()["documents"]


def test_declared_hash_difference_is_warning_not_manifest_rewrite(
    tmp_path, make_row, write_sources, put_local
):
    row = make_row(sha256="0" * 64)
    put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    original = manifest.read_bytes()
    result = run_ingestion(manifest, tmp_path)["results"][0]
    assert result["status"] == "registered"
    assert result["warnings"]
    assert manifest.read_bytes() == original


def test_corrupt_state_is_not_overwritten(tmp_path, make_row, write_sources):
    store = Store(tmp_path)
    store.directory.mkdir(parents=True)
    store.state_path.write_text("broken state", encoding="utf-8")
    manifest = write_sources(tmp_path, [make_row()])
    with pytest.raises(IngestionError) as exc:
        run_ingestion(manifest, tmp_path)
    assert exc.value.code == "invalid_state"
    assert store.state_path.read_text(encoding="utf-8") == "broken state"
    assert not store.lock_path.exists()


def test_run_lock_prevents_concurrent_writes(tmp_path, make_row, write_sources):
    store = Store(tmp_path)
    manifest = write_sources(tmp_path, [make_row()])
    with store.lock(), pytest.raises(IngestionError) as exc:
        run_ingestion(manifest, tmp_path)
    assert exc.value.code == "run_locked"
    assert not store.state_path.exists()


def test_unknown_document_has_no_output_directory(tmp_path, make_row, write_sources):
    manifest = write_sources(tmp_path, [make_row()])
    with pytest.raises(IngestionError, match="없는 문서"):
        run_ingestion(manifest, tmp_path, document_id="unknown")
    assert not Store(tmp_path).directory.exists()


def test_missing_blob_is_restored_on_repeat(tmp_path, make_row, write_sources, put_local):
    row = make_row()
    put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    first = run_ingestion(manifest, tmp_path)
    blob = tmp_path / first["results"][0]["file_path"]
    blob.unlink()
    assert run_ingestion(manifest, tmp_path)["summary"] == {"unchanged": 1}
    assert blob.is_file()


def test_existing_corrupt_blob_is_not_silently_replaced(
    tmp_path, make_row, write_sources, put_local
):
    row = make_row()
    put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    first = run_ingestion(manifest, tmp_path)
    blob = tmp_path / first["results"][0]["file_path"]
    blob.write_text("corrupted", encoding="utf-8")
    assert run_ingestion(manifest, tmp_path)["results"][0]["error_code"] == "corrupt_blob"


def test_checkpoint_failure_can_be_retried(
    tmp_path, make_row, write_sources, put_local, monkeypatch
):
    row = make_row()
    put_local(tmp_path, row)
    manifest = write_sources(tmp_path, [row])
    original = Store.checkpoint
    calls = []

    def interrupted(self, state, report):
        calls.append(1)
        original(self, state, report)
        if len(calls) == 2:
            raise OSError("simulated interruption after a checkpoint")

    with monkeypatch.context() as context:
        context.setattr(Store, "checkpoint", interrupted)
        with pytest.raises(OSError):
            run_ingestion(manifest, tmp_path)
    assert run_ingestion(manifest, tmp_path)["summary"] == {"unchanged": 1}
    assert len(Store(tmp_path).read()["documents"]["example-1"]["versions"]) == 1


def test_completed_report_and_timezone_are_persisted(tmp_path, make_row, write_sources, put_local):
    row = make_row()
    put_local(tmp_path, row)
    report = run_ingestion(write_sources(tmp_path, [row]), tmp_path)
    saved = json.loads(
        (Store(tmp_path).runs / f"{report['run_id']}.json").read_text(encoding="utf-8")
    )
    assert saved["complete"] is True
    assert saved["started_at"].endswith("+00:00")
    assert saved["results"][0]["sha256"]


@pytest.mark.parametrize(
    "local_path",
    ["../outside.md", "data/examples/README.md", "data/examples/example_questions.jsonl"],
)
def test_disallowed_local_input_is_not_registered(tmp_path, make_row, write_sources, local_path):
    report = run_ingestion(write_sources(tmp_path, [make_row(local_path=local_path)]), tmp_path)
    assert report["summary"] == {"failed": 1}
    assert not Store(tmp_path).read()["documents"]
