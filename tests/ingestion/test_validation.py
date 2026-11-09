import pytest

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.validation import validate_file, validate_local


def test_markdown_and_hash(tmp_path):
    path = tmp_path / "data/examples/example.md"
    path.parent.mkdir(parents=True)
    path.write_text("가상 문서", encoding="utf-8")
    actual, info = validate_local(tmp_path, "data/examples/example.md", max_bytes=1024)
    assert actual == path
    assert len(info.sha256) == 64
    assert info.pdf_pages is None


@pytest.mark.parametrize(
    "name,content,code",
    [
        ("empty.md", b"", "empty_file"),
        ("bad.md", b"\xff\xff", "invalid_encoding"),
        ("questions.jsonl", b"{}", "unsupported_format"),
        ("README.md", b"guide", "excluded_file"),
    ],
)
def test_invalid_local_content(tmp_path, name, content, code):
    path = tmp_path / "data/examples" / name
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    with pytest.raises(IngestionError) as exc:
        validate_local(tmp_path, f"data/examples/{name}", max_bytes=1024)
    assert exc.value.code == code


@pytest.mark.parametrize("relative", ["../outside.md", "data/ingestion/documents.json"])
def test_path_outside_examples(tmp_path, relative):
    with pytest.raises(IngestionError, match="프로젝트|data/examples"):
        validate_local(tmp_path, relative, max_bytes=1024)


def test_absolute_path_rejected(tmp_path):
    with pytest.raises(IngestionError) as exc:
        validate_local(tmp_path, str(tmp_path / "absolute.md"), max_bytes=1024)
    assert exc.value.code == "unsafe_path"


def test_missing_file(tmp_path):
    with pytest.raises(IngestionError) as exc:
        validate_local(tmp_path, "data/examples/missing.md", max_bytes=1024)
    assert exc.value.code == "missing_file"


def test_valid_pdf(tmp_path, pdf_bytes):
    path = tmp_path / "document.pdf"
    path.write_bytes(pdf_bytes)
    info = validate_file(path, ".pdf", max_bytes=1024 * 1024)
    assert info.pdf_pages == 1


@pytest.mark.parametrize(
    "content,code",
    [
        (b"<html>Access denied</html>", "unexpected_content"),
        (b"%PDF-1.7\ntruncated", "invalid_pdf"),
    ],
)
def test_invalid_pdf(tmp_path, content, code):
    path = tmp_path / "invalid.pdf"
    path.write_bytes(content)
    with pytest.raises(IngestionError) as exc:
        validate_file(path, ".pdf", max_bytes=1024)
    assert exc.value.code == code


def test_file_size_limit(tmp_path):
    path = tmp_path / "large.md"
    path.write_bytes(b"12345")
    with pytest.raises(IngestionError) as exc:
        validate_file(path, ".md", max_bytes=4)
    assert exc.value.code == "file_too_large"


def test_encrypted_pdf(tmp_path):
    from pypdf import PdfWriter

    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    with path.open("wb") as file:
        writer.write(file)
    with pytest.raises(IngestionError) as exc:
        validate_file(path, ".pdf", max_bytes=1024 * 1024)
    assert exc.value.code == "encrypted_pdf"
