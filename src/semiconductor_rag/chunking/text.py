"""같은 소제목이나 PDF 페이지 안에서 본문 청크를 만든다."""

import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

SENTENCE_BREAK = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass(frozen=True)
class TextChunk:
    document_id: str
    source_version: str | None
    source_sha256: str
    text: str
    block_indices: tuple[int, ...]
    locations: tuple[dict, ...]
    size: int
    exceeds_target: bool


def _chunk_section(
    blocks: list[dict], max_size: int, measure: Callable[[str], int]
) -> Iterator[TextChunk]:
    text = ""
    references: list[dict] = []

    def build_chunk() -> TextChunk:
        first = references[0]
        size = measure(text)
        return TextChunk(
            document_id=first["document_id"],
            source_version=first["source_version"],
            source_sha256=first["source_sha256"],
            text=text,
            block_indices=tuple(block["block_index"] for block in references),
            locations=tuple(block["location"] for block in references),
            size=size,
            exceeds_target=size > max_size,
        )

    for block in blocks:
        paragraph = block["text"].strip()
        if not paragraph:
            continue
        parts = [paragraph] if measure(paragraph) <= max_size else SENTENCE_BREAK.split(paragraph)
        for part in parts:
            same_block = bool(references) and references[-1] is block
            separator = " " if same_block else "\n\n"
            candidate = text + separator + part if text else part
            if text and measure(candidate) > max_size:
                yield build_chunk()
                references = []
                candidate = part
            if not references or references[-1] is not block:
                references.append(block)
            text = candidate
    if references:
        yield build_chunk()


def chunk_text(
    blocks: Iterable[dict], *, max_size: int, measure: Callable[[str], int] = len
) -> Iterator[TextChunk]:
    """문단을 우선 보존한다. 한 문장만으로 목표를 넘으면 초과 상태를 기록한다."""
    if max_size < 1:
        raise ValueError("청크 목표 크기는 1 이상이어야 합니다")
    section: list[dict] = []
    current_key = None
    for block in blocks:
        if block["block_type"] != "text":
            yield from _chunk_section(section, max_size, measure)
            section = []
            current_key = None
            continue
        location = block["location"]
        key = (
            block["document_id"],
            block["source_version"],
            block["source_sha256"],
            location.get("page_number"),
            tuple(location.get("section_path", ())),
        )
        if key != current_key:
            yield from _chunk_section(section, max_size, measure)
            section = []
            current_key = key
        section.append(block)
    yield from _chunk_section(section, max_size, measure)
