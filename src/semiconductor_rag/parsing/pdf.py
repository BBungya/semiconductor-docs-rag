"""PDF에서 페이지별 본문 블록과 추출 문제를 수집한다."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True)
class PdfTextResult:
    blocks: list[dict]
    issues: list[dict]
    page_count: int


def extract_pdf_text(
    path: Path,
    *,
    document_id: str,
    source_sha256: str,
    source_version: str | None = None,
) -> PdfTextResult:
    """텍스트가 있는 페이지마다 스키마 1의 본문 블록 하나를 반환한다."""
    blocks = []
    issues = []
    with path.open("rb") as stream:
        reader = PdfReader(stream, strict=True)
        if reader.is_encrypted:
            raise PdfReadError("암호화된 PDF에서는 본문을 추출할 수 없습니다")
        page_count = len(reader.pages)
        if not page_count:
            raise PdfReadError("PDF에 페이지가 없습니다")

        for page_number, page in enumerate(reader.pages, start=1):
            location = {"page_number": page_number}
            try:
                text = page.extract_text().strip()
                has_image_without_text = not text and bool(page.images.keys())
            except (PdfReadError, ValueError, NotImplementedError) as exc:
                issues.append(
                    {
                        "location": location,
                        "code": "page_extraction_failed",
                        "message": str(exc),
                    }
                )
                continue
            if not text:
                code = "no_extractable_text"
                message = "페이지에서 본문을 추출하지 못했습니다"
                if has_image_without_text:
                    code = "ocr_required"
                    message = "추출 가능한 본문이 없고 이미지가 있어 OCR 검토가 필요합니다"
                issues.append(
                    {
                        "location": location,
                        "code": code,
                        "message": message,
                    }
                )
                continue
            blocks.append(
                {
                    "schema_version": 1,
                    "document_id": document_id,
                    "source_version": source_version,
                    "source_sha256": source_sha256,
                    "block_index": len(blocks) + 1,
                    "block_type": "text",
                    "location": location,
                    "text": text,
                }
            )
    return PdfTextResult(blocks=blocks, issues=issues, page_count=page_count)
