import json

from semiconductor_rag.chunking.inputs import ChunkingInput
from semiconductor_rag.chunking.records import build_chunk_records


def test_records_keep_source_order_and_give_repeated_text_distinct_stable_ids():
    identity = {"document_id": "spec", "source_version": "1.1", "source_sha256": "a" * 64}
    source = ChunkingInput(
        "spec",
        "ready",
        blocks=(
            {
                **identity,
                "block_index": 1,
                "block_type": "text",
                "text": "Repeat. Repeat.",
                "location": {"page_number": 2},
            },
            {
                **identity,
                "block_index": 2,
                "block_type": "table",
                "columns": ["Product", "GB/s"],
                "rows": [["A", "28"], ["B", "40"]],
                "location": {"page_number": 2},
            },
            {
                **identity,
                "block_index": 3,
                "block_type": "text",
                "text": "End.",
                "location": {"page_number": 3},
            },
        ),
    )

    records = build_chunk_records(source, max_size=14)

    assert records == build_chunk_records(source, max_size=14)
    assert json.loads(json.dumps(records)) == records
    assert [record["chunk_type"] for record in records] == [
        "text",
        "text",
        "table",
        "table",
        "text",
    ]
    assert len({record["chunk_id"] for record in records}) == len(records)
    assert records[0]["text"] == records[1]["text"] == "Repeat."
    assert (
        records[0]["source_refs"]
        == records[1]["source_refs"]
        == [{"block_index": 1, "page_number": 2}]
    )
    assert records[3]["source_refs"] == [
        {"block_index": 2, "page_number": 2, "row_start": 2, "row_end": 2}
    ]
    assert records[3]["rows"] == [["B", "40"]]
    assert records[-1]["chunk_id"] != build_chunk_records(source, max_size=30)[-1]["chunk_id"]
