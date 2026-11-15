"""등록 문서의 청크와 처리 보고서를 설정별로 저장한다."""

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from semiconductor_rag.chunking.inputs import iter_chunking_inputs
from semiconductor_rag.chunking.records import build_chunk_records
from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.storage import Store, atomic_json
from semiconductor_rag.ingestion.validation import contained_path

DEFAULT_MAX_SIZE = 256


def _save_chunks(path: Path, records: list[dict]) -> str:
    digest = hashlib.sha256()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            for record in records:
                line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
                stream.write(line)
                digest.update(line)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return digest.hexdigest()


def run_chunking(
    project_root: Path, *, max_size: int = DEFAULT_MAX_SIZE, max_table_rows: int | None = None
) -> tuple[Path, dict]:
    """청크와 보고서를 쓰고 저장 폴더 및 보고서를 돌려준다."""
    if max_size < 1 or (max_table_rows is not None and max_table_rows < 1):
        raise ValueError("목표 크기와 최대 행 수는 1 이상이어야 합니다")
    root = project_root.resolve()
    if not root.is_dir():
        raise IngestionError("invalid_root", "프로젝트 루트 폴더가 없습니다")
    rows = "auto" if max_table_rows is None else str(max_table_rows)
    directory = contained_path(root, f"data/processed/_chunks/chars-{max_size}-rows-{rows}")

    records = []
    documents = []
    with Store(root).lock():
        for source in iter_chunking_inputs(root):
            status = source.status
            reason = source.reason
            generated = []
            if status == "ready":
                try:
                    generated = build_chunk_records(
                        source, max_size=max_size, max_table_rows=max_table_rows
                    )
                    status = "chunked" if generated else "skipped"
                    reason = None if generated else "no_chunks"
                except (ValueError, TypeError, KeyError) as exc:
                    status, reason = "invalid", str(exc)
            records.extend(generated)
            documents.append(
                {
                    "document_id": source.document_id,
                    "status": status,
                    "reason": reason,
                    "chunk_count": len(generated),
                }
            )
        if not documents:
            raise IngestionError(
                "no_documents", "등록된 원본이 없습니다. 먼저 문서 수집을 실행하세요"
            )

        directory.mkdir(parents=True, exist_ok=True)
        chunks_path = contained_path(directory, "chunks.jsonl")
        report_path = contained_path(directory, "chunking_report.json")
        report = {
            "schema_version": 1,
            "settings": {
                "size_unit": "characters",
                "max_size": max_size,
                "max_table_rows": max_table_rows,
            },
            "document_counts": dict(Counter(item["status"] for item in documents)),
            "chunk_count": len(records),
            "chunk_type_counts": dict(Counter(record["chunk_type"] for record in records)),
            "over_target_count": sum(record["exceeds_target"] for record in records),
            "documents": documents,
            "chunks_sha256": _save_chunks(chunks_path, records),
        }
        # Readers can compare the digest to detect an interrupted update of the pair.
        atomic_json(report_path, report)
    return directory, report
