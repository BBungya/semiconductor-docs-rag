"""본문과 표 청크를 공통 레코드로 만들고 재현 가능한 ID를 붙인다."""

import hashlib
import json
from collections import Counter

from semiconductor_rag.chunking.inputs import ChunkingInput
from semiconductor_rag.chunking.table import chunk_tables
from semiconductor_rag.chunking.text import chunk_text


def build_chunk_records(
    source: ChunkingInput, *, max_size: int, max_table_rows: int | None = None
) -> list[dict]:
    """한 문서의 청크를 원문 순서대로 반환한다. 크기는 글자 수로 잰다."""
    if source.status != "ready":
        raise ValueError("청킹할 수 있는 상태의 문서가 필요합니다")
    settings = {"size_unit": "characters", "max_size": max_size, "max_table_rows": max_table_rows}
    records = []
    for chunk in chunk_text(source.blocks, max_size=max_size):
        records.append(
            {
                "chunk_type": "text",
                "document_id": chunk.document_id,
                "source_version": chunk.source_version,
                "source_sha256": chunk.source_sha256,
                "text": chunk.text,
                "size": chunk.size,
                "exceeds_target": chunk.exceeds_target,
                "source_refs": [
                    {"block_index": index, **location}
                    for index, location in zip(chunk.block_indices, chunk.locations, strict=True)
                ],
            }
        )
    for chunk in chunk_tables(source.blocks, max_size=max_size, max_rows=max_table_rows):
        records.append(
            {
                "chunk_type": "table",
                "document_id": chunk.document_id,
                "source_version": chunk.source_version,
                "source_sha256": chunk.source_sha256,
                "text": chunk.text,
                "size": chunk.size,
                "exceeds_target": chunk.exceeds_target,
                "source_refs": [
                    {
                        "block_index": chunk.block_index,
                        **chunk.location,
                        "row_start": chunk.row_start,
                        "row_end": chunk.row_end,
                    }
                ],
                "columns": list(chunk.columns),
                "rows": [list(row) for row in chunk.rows],
            }
        )

    records.sort(key=lambda record: record["source_refs"][0]["block_index"])
    starts: Counter[int] = Counter()
    for record in records:
        first_block = record["source_refs"][0]["block_index"]
        starts[first_block] += 1
        record.update(schema_version=1, settings=settings.copy())
        identity = {"record": record, "part_at_first_block": starts[first_block]}
        encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record["chunk_id"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return records
