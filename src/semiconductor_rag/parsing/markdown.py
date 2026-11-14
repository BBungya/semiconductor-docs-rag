"""Markdown의 본문, 표와 원문 위치를 추출한다."""

import re
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


def _front_matter_length(lines: list[str]) -> int:
    if len(lines) < 3 or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            fields = lines[1:index]
            return index + 1 if any(re.match(r"^[\w-]+:", field) for field in fields) else 0
    return 0


def _table_rows(table: SyntaxTreeNode) -> list[list[str]]:
    return [
        [cell.children[0].content if cell.children else "" for cell in row.children]
        for section in table.children
        for row in section.children
    ]


def _document_nodes(root: SyntaxTreeNode):
    for node in root.children:
        if node.type == "blockquote":
            yield from _document_nodes(node)
        else:
            yield node


def extract_markdown(
    path: Path,
    *,
    document_id: str,
    source_sha256: str,
    source_version: str | None = None,
) -> list[dict]:
    """Markdown을 읽고 원문 순서대로 스키마 1 블록을 반환한다."""
    source = path.read_text(encoding="utf-8-sig")
    lines = source.split("\n")
    offset = _front_matter_length(lines)
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    root = SyntaxTreeNode(parser.parse("\n".join(lines[offset:])))
    headings: list[tuple[int, str]] = []
    blocks = []
    for node in _document_nodes(root):
        if node.map is None:
            continue
        start, end = (line + offset for line in node.map)
        while end > start and not lines[end - 1].strip():
            end -= 1
        if node.type == "heading":
            level = int(node.tag[1:])
            text = node.children[0].content
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, text))
            content = {"block_type": "heading", "text": text, "level": level}
        elif node.type == "table":
            columns, *rows = _table_rows(node)
            content = {"block_type": "table", "columns": columns, "rows": rows}
        elif node.type in {"paragraph", "bullet_list", "ordered_list", "fence", "code_block"}:
            content = {"block_type": "text", "text": "\n".join(lines[start:end])}
        else:
            continue
        blocks.append(
            {
                "schema_version": 1,
                "document_id": document_id,
                "source_version": source_version,
                "source_sha256": source_sha256,
                "block_index": len(blocks) + 1,
                "location": {
                    "section_path": [title for _, title in headings],
                    "line_start": start + 1,
                    "line_end": end,
                },
                **content,
            }
        )
    return blocks
