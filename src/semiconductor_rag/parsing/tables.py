"""격자선이 있는 PDF 표를 페이지별로 추출한다."""

from pathlib import Path

import pdfplumber
from pdfminer.pdfdocument import PDFEncryptionError
from pdfminer.pdfexceptions import PDFException

from semiconductor_rag.parsing.pdf import PdfTextResult, extract_pdf_text


def _page_tables(page):
    """페이지 위에서 아래로, 같은 높이에서는 왼쪽에서 오른쪽으로 처리한다."""
    return sorted(page.find_tables(), key=lambda table: (table.bbox[1], table.bbox[0]))


def _rectangular_table(cells: list[list[str | None]]) -> bool:
    if len(cells) < 2 or len(cells[0]) < 2:
        return False
    columns = cells[0]
    return (
        all(column and column.strip() for column in columns)
        and len({column.strip() for column in columns if column is not None}) == len(columns)
        and all(len(row) == len(columns) and None not in row for row in cells[1:])
    )


def extract_pdf(
    path: Path,
    *,
    document_id: str,
    source_sha256: str,
    source_version: str | None = None,
) -> PdfTextResult:
    """본문과 격자 표를 동일한 스키마의 블록으로 반환한다."""
    text_result = extract_pdf_text(
        path, document_id=document_id, source_sha256=source_sha256, source_version=source_version
    )
    blocks = []
    issues = list(text_result.issues)
    text_by_page = {block["location"]["page_number"]: block for block in text_result.blocks}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_number = page.page_number
            text_block = text_by_page.get(page_number)
            if text_block is not None:
                blocks.append({**text_block, "block_index": len(blocks) + 1})
            location = {"page_number": page_number}
            try:
                tables = _page_tables(page)
                extracted = [table.extract() for table in tables]
            except PDFEncryptionError:
                raise
            except (PDFException, ValueError, NotImplementedError) as exc:
                issues.append(
                    {"location": location, "code": "table_extraction_failed", "message": str(exc)}
                )
                continue
            for table_number, cells in enumerate(extracted, start=1):
                if not _rectangular_table(cells):
                    issues.append(
                        {
                            "location": {**location, "table_number": table_number},
                            "code": "table_structure_uncertain",
                            "message": "표의 열 제목 또는 셀 경계를 확인할 수 없습니다",
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
                        "block_type": "table",
                        "location": location,
                        "columns": cells[0],
                        "rows": cells[1:],
                    }
                )
    return PdfTextResult(blocks=blocks, issues=issues, page_count=text_result.page_count)
