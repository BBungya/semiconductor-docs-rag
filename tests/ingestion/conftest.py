"""네트워크에 의존하지 않는 수집 테스트 자료."""

import csv
from io import BytesIO

import pytest
from pypdf import PdfWriter


@pytest.fixture
def pdf_bytes():
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def make_row():
    def build(document_id="example-1", **changes):
        row = {
            "document_id": document_id,
            "title": "가상 예제",
            "source_kind": "project_original_synthetic",
            "selection_status": "selected_synthetic_fixture",
            "local_path": f"data/examples/{document_id}.md",
            "download_url": "",
            "source_url": "",
            "version": "1.0",
            "sha256": "",
        }
        row.update(changes)
        return row

    return build


@pytest.fixture
def write_sources():
    def write(root, rows):
        path = root / "data/manifests/sources.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = list(dict.fromkeys(key for row in rows for key in row))
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return path

    return write


@pytest.fixture
def put_local():
    def put(root, row, text="# 가상 문서\n첫 번째 버전"):
        path = root / row["local_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    return put
