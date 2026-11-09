"""외부 요청 없이 출처 목록의 검증과 분류를 테스트한다."""

import csv
import io
import sys
from pathlib import Path

import pytest

from semiconductor_rag.ingestion.manifest import ManifestError, load_manifest, main

COLUMNS = [
    "document_id",
    "title",
    "source_kind",
    "selection_status",
    "local_path",
    "download_status",
    "selection_reason",
]


def source(**changes):
    row = {
        "document_id": "example-1",
        "title": "가상 예제",
        "source_kind": "project_original_synthetic",
        "selection_status": "selected_synthetic_fixture",
        "local_path": "data/examples/example.md",
        "download_status": "created_locally",
        "selection_reason": "테스트용 예제",
    }
    row.update(changes)
    return row


def write_manifest(tmp_path, rows, columns=None, encoding="utf-8"):
    path = tmp_path / "sources.csv"
    with path.open("w", encoding=encoding, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS if columns is None else columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_local_fixture_with_utf8_and_bom(tmp_path, encoding):
    path = write_manifest(tmp_path, [source()], encoding=encoding)
    entry = load_manifest(path)[0]
    assert entry.action == "local"
    assert entry.data["title"] == "가상 예제"
    assert entry.line_number == 2


def test_missing_required_column(tmp_path):
    columns = [column for column in COLUMNS if column != "document_id"]
    row = {key: value for key, value in source().items() if key != "document_id"}
    with pytest.raises(ManifestError, match="document_id"):
        load_manifest(write_manifest(tmp_path, [row], columns))


def test_duplicate_id_invalidates_all_occurrences(tmp_path):
    entries = load_manifest(write_manifest(tmp_path, [source(), source()]))
    assert len(entries) == 2
    assert all(entry.action == "error" for entry in entries)
    assert all("document_id 중복" in entry.reason for entry in entries)


@pytest.mark.parametrize(
    "status", ["deferred_rights_review", "deferred_download_failed", "excluded"]
)
def test_deferred_external_source_is_skipped_even_if_downloaded(tmp_path, status):
    row = source(
        source_kind="external_official_candidate",
        selection_status=status,
        download_status="downloaded",
    )
    entry = load_manifest(write_manifest(tmp_path, [row]))[0]
    assert entry.action == "skip"
    assert status in entry.reason
    assert "테스트용 예제" in entry.reason


@pytest.mark.parametrize("field", ["document_id", "title", "source_kind", "selection_status"])
def test_missing_required_value_is_row_error(tmp_path, field):
    entry = load_manifest(write_manifest(tmp_path, [source(**{field: "  "})]))[0]
    assert entry.action == "error"
    assert field in entry.reason


def test_local_fixture_requires_path(tmp_path):
    entry = load_manifest(write_manifest(tmp_path, [source(local_path="")]))[0]
    assert entry.action == "error"
    assert "local_path" in entry.reason


def test_fixture_kind_must_match_selection_status(tmp_path):
    row = source(source_kind="external_official_candidate")
    entry = load_manifest(write_manifest(tmp_path, [row]))[0]
    assert entry.action == "error"
    assert "source_kind" in entry.reason


@pytest.mark.parametrize("column_count", [6, 8])
def test_wrong_column_count_is_row_error(tmp_path, column_count):
    path = tmp_path / "sources.csv"
    values = [
        "id",
        "title",
        "project_original_synthetic",
        "selected_synthetic_fixture",
        "path.md",
        "created_locally",
        "reason",
        "extra",
    ]
    path.write_text(
        ",".join(COLUMNS) + "\n" + ",".join(values[:column_count]) + "\n",
        encoding="utf-8",
    )
    entry = load_manifest(path)[0]
    assert entry.action == "error"
    assert "열 수" in entry.reason


def test_bad_row_does_not_hide_valid_row(tmp_path):
    entries = load_manifest(write_manifest(tmp_path, [source(document_id=""), source()]))
    assert [entry.action for entry in entries] == ["error", "local"]


def test_unknown_status_is_not_silently_selected(tmp_path):
    entry = load_manifest(write_manifest(tmp_path, [source(selection_status="typo")]))[0]
    assert entry.action == "error"
    assert "typo" in entry.reason


def test_explicit_download_selection_requires_url(tmp_path):
    row = source(
        source_kind="external_official_candidate", selection_status="selected_for_download"
    )
    entry = load_manifest(write_manifest(tmp_path, [row]))[0]
    assert entry.action == "error"
    assert "download_url" in entry.reason


def test_explicit_download_selection(tmp_path):
    row = source(
        source_kind="external_official_candidate", selection_status="selected_for_download"
    )
    row["download_url"] = "https://example.test/document.pdf"
    entry = load_manifest(write_manifest(tmp_path, [row], COLUMNS + ["download_url"]))[0]
    assert entry.action == "download"


@pytest.mark.parametrize("content", ["", "document_id,document_id\n", '"unterminated'])
def test_invalid_file_structure(tmp_path, content):
    path = tmp_path / "sources.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_multiline_and_comma_values_are_preserved(tmp_path):
    row = source(title="용어, 설명", selection_reason="첫째 줄\n둘째 줄")
    entry = load_manifest(write_manifest(tmp_path, [row]))[0]
    assert entry.action == "local"
    assert entry.data["title"] == "용어, 설명"
    assert entry.data["selection_reason"] == "첫째 줄\n둘째 줄"


def test_current_project_manifest():
    root = Path(__file__).resolve().parents[2]
    entries = load_manifest(root / "data/manifests/sources.csv")
    assert entries
    assert not [entry for entry in entries if entry.action == "error"]
    for entry in entries:
        if entry.data["selection_status"] == "selected_synthetic_fixture":
            assert entry.action == "local"
        elif entry.data["selection_status"].startswith("deferred_"):
            assert entry.action == "skip"


def test_cli_handles_windows_output_encoding(tmp_path, monkeypatch):
    row = source(
        source_kind="external_official_candidate",
        selection_status="deferred_rights_review",
        selection_reason="보류 이유: 🙂",
    )
    path = write_manifest(tmp_path, [row])
    original_bytes = path.read_bytes()
    buffer = io.BytesIO()
    output = io.TextIOWrapper(buffer, encoding="cp949")
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "argv", ["manifest", "--manifest", str(path)])
    assert main() == 0
    output.flush()
    text = buffer.getvalue().decode("cp949")
    assert "건너뜀 1개" in text
    assert "\\U0001f642" in text
    assert path.read_bytes() == original_bytes
