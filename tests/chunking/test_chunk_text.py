from semiconductor_rag.chunking.text import chunk_text


def block(index, text, *, section="사양", page=None, kind="text"):
    return {
        "block_type": kind,
        "block_index": index,
        "text": text,
        "document_id": "spec",
        "source_sha256": "a" * 64,
        "source_version": "1.1",
        "location": (
            {"page_number": page}
            if page is not None
            else {"section_path": [section], "line_start": index, "line_end": index}
        ),
    }


def test_size_changes_grouping_but_keeps_product_and_unit_together():
    blocks = [
        block(1, "제품 A는 28 GB/s다. 지연 시간은 1.5 ns다."),
        block(2, "테스트 조건은 가상이다."),
    ]

    large = list(chunk_text(blocks, max_size=100))
    small = list(chunk_text(blocks, max_size=18))

    assert len(large) == 1
    assert large[0].block_indices == (1, 2)
    assert [chunk.text for chunk in small] == [
        "제품 A는 28 GB/s다.",
        "지연 시간은 1.5 ns다.",
        "테스트 조건은 가상이다.",
    ]
    assert small[1].locations == (blocks[0]["location"],)
    assert all(chunk.source_version == "1.1" and not chunk.exceeds_target for chunk in small)


def test_does_not_merge_across_table_section_or_pdf_page():
    blocks = [
        block(1, "before"),
        block(2, "", kind="table"),
        block(3, "after"),
        block(4, "different section", section="조건"),
        block(5, "page one", page=1),
        block(6, "page two", page=2),
    ]

    assert [chunk.block_indices for chunk in chunk_text(blocks, max_size=200)] == [
        (1,),
        (3,),
        (4,),
        (5,),
        (6,),
    ]


def test_oversized_sentence_is_marked_when_using_custom_size_measure():
    [chunk] = chunk_text(
        [block(1, "SYN-MEM-A 28 GB/s")], max_size=2, measure=lambda s: len(s.split())
    )

    assert chunk.text == "SYN-MEM-A 28 GB/s"
    assert chunk.size == 3
    assert chunk.exceeds_target
