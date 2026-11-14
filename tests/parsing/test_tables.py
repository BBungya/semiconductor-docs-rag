from hashlib import sha256

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table, TableStyle

from semiconductor_rag.parsing.tables import extract_pdf


def make_spec_pdf(path, *, merged_header=False):
    pdf = Canvas(str(path), pagesize=(460, 300))
    pdf.drawString(24, 270, "Synthetic memory spec")
    pdf.showPage()
    pdf.drawString(24, 270, "Memory capacity and bandwidth")
    table = Table(
        [
            ["Product", "Capacity (GiB)", "Bandwidth (GB/s)"],
            ["SYN-MEM-A", "32", "28"],
            ["SYN-MEM-A2", "32", "30"],
            ["SYN-MEM-B", "64", "40"],
        ],
        colWidths=[110, 120, 150],
    )
    style = [("GRID", (0, 0), (-1, -1), 0.8, colors.black)]
    if merged_header:
        style.append(("SPAN", (0, 0), (1, 0)))
    table.setStyle(TableStyle(style))
    table.wrapOn(pdf, 410, 200)
    table.drawOn(pdf, 24, 144)
    pdf.save()


def test_extracts_product_rows_and_units_from_pdf_grid(tmp_path):
    path = tmp_path / "spec.pdf"
    make_spec_pdf(path)
    digest = sha256(path.read_bytes()).hexdigest()

    result = extract_pdf(
        path, document_id="synthetic-spec", source_sha256=digest, source_version="1.1"
    )

    assert result.page_count == 2
    assert result.issues == []
    assert [block["block_type"] for block in result.blocks] == ["text", "text", "table"]
    assert result.blocks[-1] == {
        "schema_version": 1,
        "document_id": "synthetic-spec",
        "source_version": "1.1",
        "source_sha256": digest,
        "block_index": 3,
        "block_type": "table",
        "location": {"page_number": 2},
        "columns": ["Product", "Capacity (GiB)", "Bandwidth (GB/s)"],
        "rows": [["SYN-MEM-A", "32", "28"], ["SYN-MEM-A2", "32", "30"], ["SYN-MEM-B", "64", "40"]],
    }


def test_records_merged_header_for_review_and_keeps_body(tmp_path):
    path = tmp_path / "merged.pdf"
    make_spec_pdf(path, merged_header=True)

    result = extract_pdf(path, document_id="synthetic-spec", source_sha256="a" * 64)

    assert [block["block_type"] for block in result.blocks] == ["text", "text"]
    assert "Memory capacity and bandwidth" in result.blocks[-1]["text"]
    assert len(result.issues) == 1
    assert result.issues[0]["code"] == "table_structure_uncertain"
    assert result.issues[0]["location"] == {"page_number": 2, "table_number": 1}
