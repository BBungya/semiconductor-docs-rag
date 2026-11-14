from hashlib import sha256

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from semiconductor_rag.parsing.pdf import extract_pdf_text
from semiconductor_rag.parsing.tables import extract_pdf


def add_text_page(writer, text):
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 24 156 Td ({text}) Tj ET".encode("ascii"))
    page.replace_contents(stream)


def test_keeps_pdf_page_numbers_when_middle_page_has_no_text(tmp_path):
    writer = PdfWriter()
    add_text_page(writer, "SYN-MEM-A: 32 GiB, 28 GB/s")
    writer.add_blank_page(width=300, height=200)
    add_text_page(writer, "SYN-MEM-A2: 130 ns, 14 W")
    path = tmp_path / "synthetic.pdf"
    writer.write(path)
    digest = sha256(path.read_bytes()).hexdigest()

    result = extract_pdf_text(
        path, document_id="synthetic-spec", source_sha256=digest, source_version="1.1"
    )

    assert result.page_count == 3
    assert [block["location"]["page_number"] for block in result.blocks] == [1, 3]
    assert [block["block_index"] for block in result.blocks] == [1, 2]
    assert result.blocks[0] == {
        "schema_version": 1,
        "document_id": "synthetic-spec",
        "source_version": "1.1",
        "source_sha256": digest,
        "block_index": 1,
        "block_type": "text",
        "location": {"page_number": 1},
        "text": "SYN-MEM-A: 32 GiB, 28 GB/s",
    }
    assert result.blocks[1]["text"] == "SYN-MEM-A2: 130 ns, 14 W"
    assert len(result.issues) == 1
    assert result.issues[0]["location"] == {"page_number": 2}
    assert result.issues[0]["code"] == "no_extractable_text"


def test_flags_image_only_page_and_keeps_text_on_mixed_page(tmp_path):
    path = tmp_path / "ocr-candidates.pdf"
    image = ImageReader(Image.new("RGB", (120, 80), "gray"))
    canvas = Canvas(str(path), pagesize=(300, 200))
    canvas.drawImage(image, 10, 10, width=280, height=180)
    canvas.showPage()
    canvas.drawImage(image, 10, 10, width=280, height=150)
    canvas.drawString(10, 175, "SYN-MEM-A: 28 GB/s")
    canvas.save()

    result = extract_pdf(path, document_id="scan", source_sha256="a" * 64)

    assert result.page_count == 2
    assert len(result.blocks) == 1
    assert result.blocks[0]["location"] == {"page_number": 2}
    assert result.blocks[0]["text"] == "SYN-MEM-A: 28 GB/s"
    assert len(result.issues) == 1
    assert result.issues[0]["location"] == {"page_number": 1}
    assert result.issues[0]["code"] == "ocr_required"


@pytest.mark.parametrize("encrypted", [False, True])
def test_rejects_pdf_without_readable_pages(tmp_path, encrypted):
    writer = PdfWriter()
    if encrypted:
        writer.add_blank_page(width=300, height=200)
        writer.encrypt("test-password")
    path = tmp_path / "invalid.pdf"
    writer.write(path)

    with pytest.raises(PdfReadError):
        extract_pdf_text(path, document_id="invalid", source_sha256="a" * 64)
