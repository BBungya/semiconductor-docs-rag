"""등록된 원본을 파싱하고 결과와 검토 기록을 저장한다."""

import hashlib
import json
import os
import re
import tempfile
from importlib.metadata import version
from pathlib import Path, PureWindowsPath

from pdfminer.pdfexceptions import PDFException
from pypdf.errors import PyPdfError

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.storage import Store, atomic_json
from semiconductor_rag.ingestion.validation import contained_path, hash_file
from semiconductor_rag.parsing.markdown import extract_markdown
from semiconductor_rag.parsing.tables import extract_pdf

SAFE_ID = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}")


def _result_directory(root: Path, document_id: str, digest: str) -> Path:
    if (
        not SAFE_ID.fullmatch(document_id)
        or document_id.endswith(".")
        or PureWindowsPath(document_id).is_reserved()
    ):
        raise IngestionError("invalid_document_id", f"출력에 사용할 수 없는 문서 ID: {document_id}")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise IngestionError("invalid_source_hash", f"잘못된 등록 해시: {document_id}")
    output = contained_path(root, "data/processed")
    return contained_path(output, Path(document_id) / digest)


def _save_result(directory: Path, blocks: list[dict], report: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(block, ensure_ascii=False) + "\n" for block in blocks).encode("utf-8")
    blocks_path = contained_path(directory, "blocks.jsonl")
    report_path = contained_path(directory, "parsing_report.json")
    report["blocks_sha256"] = hashlib.sha256(data).hexdigest()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, blocks_path)
        # Publish the report last. Its digest lets readers detect an interrupted update.
        atomic_json(report_path, report)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parse_document(root: Path, document_id: str, document: dict, parsers: dict) -> dict:
    digest = document.get("current_sha256")
    directory = _result_directory(root, document_id, digest)
    report = {
        "schema_version": 1,
        "document_id": document_id,
        "title": document.get("title"),
        "source_sha256": digest,
        "source_version": document.get("source_version") or None,
        "source": {},
        "parsers": {},
        "page_count": None,
        "block_count": 0,
        "status": "failed",
        "issues": [],
    }
    blocks = []
    try:
        current = next((item for item in document["versions"] if item["sha256"] == digest), None)
        if current is None:
            raise IngestionError("missing_version", "현재 해시에 해당하는 등록 버전이 없습니다")
        relative_path = current["file_path"]
        report["source"] = {
            key: current.get(key) or None
            for key in ("file_path", "origin_path", "source_url", "final_url")
        }
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            raise IngestionError(
                "unsafe_path", "등록 원본 경로는 프로젝트 기준 상대 경로여야 합니다"
            )
        source = contained_path(root, relative_path)
        if not source.is_relative_to(contained_path(root, "data/raw/blobs")):
            raise IngestionError("unsafe_path", "등록 원본은 data/raw/blobs 아래에 있어야 합니다")
        if not source.is_file():
            raise IngestionError("missing_file", "등록 원본이 없습니다")
        if hash_file(source) != digest:
            raise IngestionError("source_hash_mismatch", "등록 해시와 원본 파일 내용이 다릅니다")

        metadata = {
            "document_id": document_id,
            "source_sha256": digest,
            "source_version": report["source_version"],
        }
        match source.suffix.lower():
            case ".md":
                report["parsers"] = {"markdown-it-py": parsers["markdown-it-py"]}
                blocks = extract_markdown(source, **metadata)
            case ".pdf":
                report["parsers"] = {"pypdf": parsers["pypdf"], "pdfplumber": parsers["pdfplumber"]}
                result = extract_pdf(source, **metadata)
                blocks = result.blocks
                report["page_count"] = result.page_count
                report["issues"] = result.issues
            case _:
                raise IngestionError("unsupported_format", f"지원하지 않는 형식: {source.suffix}")
        if not blocks and not report["issues"]:
            report["issues"].append(
                {"code": "no_blocks", "message": "추출한 본문이나 표가 없습니다"}
            )
        report["block_count"] = len(blocks)
        report["status"] = "needs_review" if report["issues"] else "parsed"
    except IngestionError as exc:
        report["issues"].append({"code": exc.code, "message": str(exc)})
    except (OSError, PyPdfError, PDFException, ValueError, NotImplementedError) as exc:
        report["issues"].append({"code": "parse_failed", "message": str(exc)})

    _save_result(directory, blocks, report)
    return report


def run_parsing(project_root: Path, *, document_id: str | None = None) -> list[dict]:
    """현재 등록된 문서를 읽고 각 문서의 처리 보고서를 반환한다."""
    root = project_root.resolve()
    if not root.is_dir():
        raise IngestionError("invalid_root", "프로젝트 루트 폴더가 없습니다")
    store = Store(root)
    parsers = {name: version(name) for name in ("markdown-it-py", "pypdf", "pdfplumber")}
    with store.lock():
        documents = store.read()["documents"]
        if document_id is not None and document_id not in documents:
            raise IngestionError("unknown_document", f"등록되지 않은 문서 ID: {document_id}")
        if not documents:
            raise IngestionError(
                "no_documents", "등록된 원본이 없습니다. 먼저 문서 수집을 실행하세요"
            )
        folded_ids = {key.casefold() for key in documents}
        if len(folded_ids) != len(documents):
            raise IngestionError("duplicate_output_path", "대소문자만 다른 문서 ID가 있습니다")
        selected = [document_id] if document_id is not None else sorted(documents)
        for key in selected:
            _result_directory(root, key, documents[key].get("current_sha256"))
        return [_parse_document(root, key, documents[key], parsers) for key in selected]
