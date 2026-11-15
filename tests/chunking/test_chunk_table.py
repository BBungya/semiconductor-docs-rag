from semiconductor_rag.chunking.table import chunk_tables


def table(**updates):
    return {
        "document_id": "memory-spec",
        "source_sha256": "a" * 64,
        "source_version": "1.1",
        "block_type": "table",
        "block_index": 7,
        "location": {"section_path": ["사양표"], "line_start": 20, "line_end": 24},
        "columns": ["제품 코드", "용량 (GiB)", "대역폭 (GB/s)"],
        "rows": [["SYN-MEM-A", "32", "28"], ["SYN-MEM-A2", "32", "30"], ["SYN-MEM-B", "64", "40"]],
        **updates,
    }


def test_size_and_row_limit_split_on_row_boundaries_and_keep_units():
    block = table()
    [whole] = chunk_tables([block], max_size=500)
    split = list(chunk_tables([block, {"block_type": "text"}], max_size=110))
    one_row = list(chunk_tables([block], max_size=500, max_rows=1))

    assert (whole.row_start, whole.row_end) == (1, 3)
    assert [(chunk.row_start, chunk.row_end) for chunk in split] == [(1, 2), (3, 3)]
    assert [chunk.rows[0][0] for chunk in one_row] == ["SYN-MEM-A", "SYN-MEM-A2", "SYN-MEM-B"]
    assert tuple(row for chunk in split for row in chunk.rows) == whole.rows
    assert all(chunk.columns == whole.columns and "대역폭 (GB/s)" in chunk.text for chunk in split)
    assert "제품 코드: SYN-MEM-A | 용량 (GiB): 32 | 대역폭 (GB/s): 28" in split[0].text
    assert split[1].location == block["location"]
    assert split[1].block_index == 7
    assert split[1].source_version == "1.1"


def test_keeps_oversized_row_whole_and_retains_empty_cells():
    path = {"page_number": 3}
    block = table(location=path, rows=[["SYN-MEM-A", "", "28"]])
    [chunk] = chunk_tables([block], max_size=8)

    assert chunk.exceeds_target
    assert chunk.rows == (("SYN-MEM-A", "", "28"),)
    assert chunk.location == path
    assert chunk.size == len(chunk.text)
