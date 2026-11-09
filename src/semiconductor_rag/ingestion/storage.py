"""내용 기반 파일 보관, 원자적 상태 저장, 단일 실행 잠금."""

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.validation import contained_path, hash_file


def now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, mode="w", encoding="utf-8", suffix=".tmp", delete=False
        ) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.directory = contained_path(self.root, "data/ingestion")
        self.state_path = contained_path(self.root, "data/ingestion/documents.json")
        self.blobs = contained_path(self.root, "data/raw/blobs")
        self.runs = contained_path(self.root, "data/ingestion/runs")
        self.temp = contained_path(self.root, "data/ingestion/tmp")
        self.lock_path = contained_path(self.root, "data/ingestion/run.lock")

    def read(self) -> dict:
        if not self.state_path.exists():
            return {"schema_version": 1, "documents": {}, "last_attempts": {}}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            if (
                not isinstance(value, dict)
                or value.get("schema_version") != 1
                or not isinstance(value.get("documents"), dict)
                or not isinstance(value.get("last_attempts"), dict)
            ):
                raise ValueError("지원하지 않는 상태 형식")
            for document in value["documents"].values():
                if not isinstance(document, dict) or not isinstance(document.get("versions"), list):
                    raise TypeError("잘못된 문서 버전 목록")
                for version in document["versions"]:
                    if not isinstance(version, dict) or not all(
                        key in version for key in ("sha256", "file_path", "registered_at")
                    ):
                        raise ValueError("잘못된 버전 기록")
                    contained_path(self.root, version["file_path"])
            if any(not isinstance(item, dict) for item in value["last_attempts"].values()):
                raise ValueError("잘못된 최근 시도 기록")
            return value
        except (ValueError, TypeError, OSError) as exc:
            raise IngestionError("invalid_state", f"기존 상태 읽기 실패: {exc}") from exc

    @contextmanager
    def lock(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise IngestionError(
                "run_locked", "다른 실행 중이거나 중단된 실행의 run.lock이 남아 있습니다"
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump({"pid": os.getpid(), "started_at": now()}, file)
            yield
        finally:
            self.lock_path.unlink(missing_ok=True)

    def install_blob(self, source: Path, info) -> str:
        destination = contained_path(self.root, self.blobs / f"{info.sha256}{info.suffix}")
        self.blobs.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if hash_file(destination) != info.sha256:
                raise IngestionError("corrupt_blob", "보관 중인 원본의 해시가 손상되었습니다")
        else:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=self.blobs, suffix=".part", delete=False
                ) as file:
                    temporary = Path(file.name)
                    with source.open("rb") as original:
                        shutil.copyfileobj(original, file)
                    file.flush()
                    os.fsync(file.fileno())
                if hash_file(temporary) != info.sha256:
                    raise IngestionError("source_changed", "검증 후 원본 내용이 바뀌었습니다")
                os.replace(temporary, destination)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return destination.relative_to(self.root).as_posix()

    def register(self, state, entry, source, info, result) -> None:
        file_path = self.install_blob(source, info)
        document = state["documents"].get(entry.document_id)
        if document is None:
            status = "registered"
            document = {"versions": []}
            state["documents"][entry.document_id] = document
        else:
            status = "unchanged" if document.get("current_sha256") == info.sha256 else "changed"
        if not any(version["sha256"] == info.sha256 for version in document["versions"]):
            document["versions"].append(
                {
                    "sha256": info.sha256,
                    "file_path": file_path,
                    "registered_at": result["timestamp"],
                    "size_bytes": info.size_bytes,
                    "pdf_pages": info.pdf_pages,
                    "source_version": entry.data.get("version", ""),
                    "source_url": entry.data.get("source_url", ""),
                    "final_url": result.get("final_url"),
                    "origin_path": entry.data.get("local_path", ""),
                }
            )
        document.update(
            {
                "title": entry.data["title"],
                "current_sha256": info.sha256,
                "current_file_path": file_path,
                "source_version": entry.data.get("version", ""),
                "last_seen_at": result["timestamp"],
            }
        )
        result.update(
            {
                "status": status,
                "sha256": info.sha256,
                "file_path": file_path,
                "size_bytes": info.size_bytes,
                "pdf_pages": info.pdf_pages,
                "manifest_sha256": entry.data.get("sha256", ""),
            }
        )
        declared = entry.data.get("sha256", "")
        result["warnings"] = (
            ["출처 목록의 해시와 실제 내용이 다릅니다. 목록은 자동 변경하지 않았습니다."]
            if declared and declared.lower() != info.sha256
            else []
        )

    def checkpoint(self, state: dict, report: dict) -> None:
        atomic_json(self.state_path, state)
        atomic_json(self.runs / f"{report['run_id']}.json", report)
