from semiconductor_rag.parsing.markdown import extract_markdown


def test_extracts_table_and_keeps_original_lines_after_front_matter(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text(
        "---\ntitle: 가상 사양\n---\n\n# 가상 사양\n\n## 용량\n\n"
        "| 제품 코드 | 용량 (GiB) | 대역폭 (GB/s) |\n"
        "| --- | ---: | ---: |\n"
        "| SYN-MEM-A | 32 | 28 |\n"
        "| SYN-MEM-A2 | 32 | 30 |\n\n"
        "## 조건\n\n1. 단위를 확인한다.\n   - GiB를 유지한다.\n\n"
        "> 가상 수치입니다.\n",
        encoding="utf-8-sig",
    )

    blocks = extract_markdown(
        path, document_id="spec", source_sha256="a" * 64, source_version="1.1"
    )

    assert [block["block_type"] for block in blocks] == [
        "heading",
        "heading",
        "table",
        "heading",
        "text",
        "text",
    ]
    assert blocks[0]["location"]["line_start"] == 5
    assert blocks[2] == {
        "schema_version": 1,
        "document_id": "spec",
        "source_version": "1.1",
        "source_sha256": "a" * 64,
        "block_index": 3,
        "location": {"section_path": ["가상 사양", "용량"], "line_start": 9, "line_end": 12},
        "block_type": "table",
        "columns": ["제품 코드", "용량 (GiB)", "대역폭 (GB/s)"],
        "rows": [["SYN-MEM-A", "32", "28"], ["SYN-MEM-A2", "32", "30"]],
    }
    assert blocks[4]["location"] == {
        "section_path": ["가상 사양", "조건"],
        "line_start": 16,
        "line_end": 17,
    }
    assert blocks[4]["text"] == "1. 단위를 확인한다.\n   - GiB를 유지한다."
    assert blocks[5]["text"] == "> 가상 수치입니다."


def test_keeps_code_fence_and_escaped_pipe_out_of_markdown_structure(tmp_path):
    path = tmp_path / "example.md"
    path.write_text(
        "# Example\n\n```text\n# not a heading\n```\n\n"
        "| Label | Value |\n| --- | --- |\n| A\\|B | 3 |\n",
        encoding="utf-8",
    )

    blocks = extract_markdown(path, document_id="example", source_sha256="b" * 64)

    assert [block["block_type"] for block in blocks] == ["heading", "text", "table"]
    assert blocks[1]["text"] == "```text\n# not a heading\n```"
    assert blocks[2]["rows"] == [["A|B", "3"]]
