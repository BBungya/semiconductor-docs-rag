"""CLI 옵션, 반환 코드와 dry-run의 읽기 전용 동작을 확인한다."""

import csv

import pytest

from semiconductor_rag.ingestion import __main__ as cli


def write_source(path, duplicate=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["document_id", "title", "source_kind", "selection_status", "local_path"])
        row = [
            "example-1",
            "가상 예제",
            "project_original_synthetic",
            "selected_synthetic_fixture",
            "data/examples/example.md",
        ]
        writer.writerow(row)
        if duplicate:
            writer.writerow(row)


def snapshot_files(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_custom_manifest_dry_run_does_not_write_files(tmp_path, monkeypatch, capsys):
    path = tmp_path / "custom.csv"
    write_source(path)
    monkeypatch.chdir(tmp_path)
    before = snapshot_files(tmp_path)
    assert cli.main(["--manifest", str(path), "--dry-run"]) == 0
    output = capsys.readouterr()
    assert "[DRY RUN]" in output.out
    assert "로컬 등록 예정 1개" in output.out
    assert not output.err
    assert snapshot_files(tmp_path) == before
    assert not (tmp_path / "data/examples/example.md").exists()


def test_default_manifest_is_relative_to_working_directory(tmp_path, monkeypatch, capsys):
    write_source(tmp_path / "data/manifests/sources.csv")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["--dry-run"]) == 0
    assert "로컬 등록 예정 1개" in capsys.readouterr().out


def test_missing_file_returns_input_error(tmp_path, capsys):
    assert cli.main(["--manifest", str(tmp_path / "missing.csv"), "--dry-run"]) == 2
    assert "입력/실행 오류" in capsys.readouterr().err


def test_invalid_header_returns_input_error(tmp_path, capsys):
    path = tmp_path / "invalid.csv"
    path.write_text("title\n예제\n", encoding="utf-8")
    assert cli.main(["--manifest", str(path), "--dry-run"]) == 2
    assert "필수 열 누락" in capsys.readouterr().err


def test_duplicate_rows_are_reported_and_return_failure(tmp_path, capsys):
    path = tmp_path / "duplicate.csv"
    write_source(path, duplicate=True)
    assert cli.main(["--manifest", str(path), "--dry-run"]) == 1
    output = capsys.readouterr().out
    assert "document_id 중복" in output
    assert "오류 2개" in output


def test_without_dry_run_registers_local_file(
    tmp_path, monkeypatch, capsys, make_row, write_sources, put_local
):
    row = make_row()
    write_sources(tmp_path, [row])
    put_local(tmp_path, row)
    monkeypatch.chdir(tmp_path)
    assert cli.main([]) == 0
    assert "신규 등록 1개" in capsys.readouterr().out
    assert (tmp_path / "data/ingestion/documents.json").is_file()


def test_help_lists_supported_options(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "--manifest" in output
    assert "--dry-run" in output


def test_unknown_option_is_rejected(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--not-an-option"])
    assert exc.value.code == 2
    assert "--not-an-option" in capsys.readouterr().err


@pytest.mark.parametrize(
    "option,value",
    [
        ("--max-attempts", "0"),
        ("--max-bytes", "-1"),
        ("--timeout", "nan"),
        ("--timeout", "inf"),
        ("--timeout", "0"),
    ],
)
def test_invalid_limits_are_rejected(option, value):
    with pytest.raises(SystemExit) as exc:
        cli.main([option, value, "--dry-run"])
    assert exc.value.code == 2


def test_document_filter_and_retry_option(tmp_path, monkeypatch, capsys, make_row, write_sources):
    write_sources(tmp_path, [make_row("one"), make_row("two")])
    monkeypatch.chdir(tmp_path)
    assert cli.main(["--document-id", "one"]) == 1
    output = capsys.readouterr().out
    assert "one" in output
    assert "| two |" not in output
    assert cli.main(["--retry-failed", "--dry-run"]) == 0
    assert "로컬 등록 예정 1개" in capsys.readouterr().out
