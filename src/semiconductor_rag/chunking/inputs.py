"""현재 등록된 문서에서 검증된 파싱 블록을 읽는다."""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.storage import Store
from semiconductor_rag.ingestion.validation import contained_path
from semiconductor_rag.parsing.pipeline import _result_directory


@dataclass(frozen=True)
class ChunkingInput:
    document_id: str
    status: str
    reason: str | None = None
    report: dict | None = None
    blocks: tuple[dict, ...] = ()


def _source_identity(value: dict) -> tuple:
    return tuple(value.get(key) for key in ("document_id", "source_sha256", "source_version"))


def _load_document(root: Path, document_id: str, document: dict) -> ChunkingInput:
    digest = document.get("current_sha256")
    identity = (document_id, digest, document.get("source_version") or None)
    try:
        directory = _result_directory(root, document_id, digest)
        report_path = contained_path(directory, "parsing_report.json")
        blocks_path = contained_path(directory, "blocks.jsonl")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or report.get("schema_version") != 1:
            raise ValueError("지원하지 않는 파싱 보고서 형식")
        if _source_identity(report) != identity:
            raise ValueError("파싱 보고서의 문서 정보가 현재 등록 버전과 다릅니다")

        status = report.get("status")
        if status in ("needs_review", "failed"):
            return ChunkingInput(document_id, "skipped", f"parsing_{status}", report)
        if status != "parsed":
            raise ValueError("알 수 없는 파싱 상태")

        content = blocks_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != report.get("blocks_sha256"):
            raise ValueError("블록 파일의 해시가 보고서와 다릅니다")
        blocks = tuple(json.loads(line) for line in content.decode("utf-8").split("\n") if line)
        if not blocks or len(blocks) != report.get("block_count"):
            raise ValueError("블록 개수가 보고서와 다릅니다")
        for index, block in enumerate(blocks, start=1):
            if (
                not isinstance(block, dict)
                or block.get("schema_version") != 1
                or _source_identity(block) != identity
                or block.get("block_index") != index
            ):
                raise ValueError(f"{index}번 블록의 문서 정보 또는 순서가 잘못됐습니다")
    except FileNotFoundError:
        return ChunkingInput(document_id, "skipped", "missing_parsing_output")
    except (IngestionError, OSError, ValueError) as exc:
        return ChunkingInput(document_id, "invalid", str(exc))
    return ChunkingInput(document_id, "ready", report=report, blocks=blocks)


def iter_chunking_inputs(project_root: Path) -> Iterator[ChunkingInput]:
    """등록 기록에 있는 문서만 읽고 처리 가능 여부와 이유를 돌려준다."""
    root = project_root.resolve()
    documents = Store(root).read()["documents"]
    for document_id, document in sorted(documents.items()):
        yield _load_document(root, document_id, document)
