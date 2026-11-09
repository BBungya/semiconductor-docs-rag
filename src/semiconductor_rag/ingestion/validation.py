"""로컬 파일과 PDF의 기본 유효성을 확인한다."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from semiconductor_rag.ingestion.errors import IngestionError


@dataclass(frozen=True)
class FileInfo:
    sha256: str
    size_bytes: int
    suffix: str
    pdf_pages: int | None = None


def contained_path(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise IngestionError("unsafe_path", "프로젝트 밖의 경로입니다")
    return path


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, suffix: str, *, max_bytes: int) -> FileInfo:
    if not path.is_file():
        raise IngestionError("missing_file", f"파일이 없습니다: {path.name}")
    size = path.stat().st_size
    if size == 0:
        raise IngestionError("empty_file", "빈 파일입니다")
    if size > max_bytes:
        raise IngestionError("file_too_large", "파일 크기 한도 초과")
    pages = None
    if suffix == ".pdf":
        with path.open("rb") as file:
            header = file.read(1024)
        if b"%PDF-" not in header:
            raise IngestionError("unexpected_content", "PDF 대신 다른 내용이 반환되었습니다")
        try:
            with path.open("rb") as file:
                reader = PdfReader(file, strict=True)
                if reader.is_encrypted:
                    raise IngestionError("encrypted_pdf", "암호화 PDF는 지원하지 않습니다")
                pages = len(reader.pages)
                if not pages:
                    raise IngestionError("invalid_pdf", "페이지가 없는 PDF입니다")
                for page in reader.pages:
                    _ = page.mediabox
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError("invalid_pdf", f"PDF 기본 검증 실패: {exc}") from exc
    elif suffix == ".md":
        try:
            path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise IngestionError("invalid_encoding", "예제는 UTF-8이어야 합니다") from exc
    else:
        raise IngestionError("unsupported_format", f"지원하지 않는 형식: {suffix}")
    return FileInfo(hash_file(path), size, suffix, pages)


def validate_local(root: Path, relative: str, *, max_bytes: int):
    if Path(relative).is_absolute():
        raise IngestionError("unsafe_path", "local_path는 프로젝트 기준 상대 경로여야 합니다")
    path = contained_path(root, relative)
    if not path.is_relative_to(contained_path(root, "data/examples")):
        raise IngestionError("unsafe_path", "로컬 예제는 data/examples 안에 있어야 합니다")
    if path.name.lower() == "readme.md":
        raise IngestionError("excluded_file", "안내 README는 수집 대상이 아닙니다")
    return path, validate_file(path, path.suffix.lower(), max_bytes=max_bytes)
