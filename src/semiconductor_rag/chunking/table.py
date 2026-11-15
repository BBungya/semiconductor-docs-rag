"""표를 행 단위로 묶고 각 셀에 원래 열 제목을 연결한다."""

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class TableChunk:
    document_id: str
    source_version: str | None
    source_sha256: str
    block_index: int
    location: dict
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_start: int | None
    row_end: int | None
    text: str
    size: int
    exceeds_target: bool


def _chunk_table(
    block: dict, max_size: int, max_rows: int | None, measure: Callable[[str], int]
) -> Iterator[TableChunk]:
    columns = tuple(block["columns"])
    rows = tuple(tuple(row) for row in block["rows"])
    if not columns or any(len(row) != len(columns) for row in rows):
        raise ValueError(f"표 블록 {block['block_index']}의 열 개수가 일치하지 않습니다")

    def build_chunk(start: int, end: int, text: str) -> TableChunk:
        size = measure(text)
        return TableChunk(
            document_id=block["document_id"],
            source_version=block["source_version"],
            source_sha256=block["source_sha256"],
            block_index=block["block_index"],
            location=block["location"],
            columns=columns,
            rows=rows[start:end],
            row_start=start + 1 if end > start else None,
            row_end=end if end > start else None,
            text=text,
            size=size,
            exceeds_target=size > max_size,
        )

    if not rows:
        yield build_chunk(0, 0, " | ".join(columns))
        return

    start = 0
    text = ""
    for index, row in enumerate(rows):
        line = " | ".join(f"{column}: {value}" for column, value in zip(columns, row, strict=True))
        candidate = f"{text}\n{line}" if index > start else line
        if index > start and (
            (max_rows is not None and index - start >= max_rows) or measure(candidate) > max_size
        ):
            yield build_chunk(start, index, text)
            start = index
            candidate = line
        text = candidate
    yield build_chunk(start, len(rows), text)


def chunk_tables(
    blocks: Iterable[dict],
    *,
    max_size: int,
    max_rows: int | None = None,
    measure: Callable[[str], int] = len,
) -> Iterator[TableChunk]:
    """표마다 행을 묶는다. 단일 행이 목표를 넘으면 그대로 담고 표시한다."""
    if max_size < 1 or (max_rows is not None and max_rows < 1):
        raise ValueError("목표 크기와 최대 행 수는 1 이상이어야 합니다")
    for block in blocks:
        if block["block_type"] == "table":
            yield from _chunk_table(block, max_size, max_rows, measure)
