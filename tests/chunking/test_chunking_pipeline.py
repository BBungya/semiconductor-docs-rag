import hashlib
import json

from semiconductor_rag.chunking.__main__ import main
from semiconductor_rag.ingestion.storage import Store, atomic_json


def test_cli_saves_repeatable_results_and_keeps_configurations_apart(tmp_path):
    store = Store(tmp_path)
    digest = "b" * 64
    identity = {"document_id": "spec", "source_sha256": digest, "source_version": "1.1"}
    document = {
        "current_sha256": digest,
        "source_version": "1.1",
        "versions": [
            {"sha256": digest, "file_path": "data/raw/blobs/spec.md", "registered_at": "test"}
        ],
    }
    atomic_json(
        store.state_path,
        {
            "schema_version": 1,
            "documents": {"spec": document, "missing": document},
            "last_attempts": {},
        },
    )
    processed = tmp_path / "data" / "processed"
    source = processed / "spec" / digest
    source.mkdir(parents=True)
    block = {
        **identity,
        "schema_version": 1,
        "block_index": 1,
        "block_type": "table",
        "location": {"page_number": 2},
        "columns": ["Product", "GB/s"],
        "rows": [["A", "28"], ["B", "40"]],
    }
    contents = (json.dumps(block) + "\n").encode("utf-8")
    (source / "blocks.jsonl").write_bytes(contents)
    atomic_json(
        source / "parsing_report.json",
        {
            **identity,
            "schema_version": 1,
            "status": "parsed",
            "block_count": 1,
            "blocks_sha256": hashlib.sha256(contents).hexdigest(),
        },
    )

    args = ["--project-root", str(tmp_path)]
    assert main(args) == 1
    default = processed / "_chunks" / "chars-256-rows-auto"
    chunks_path = default / "chunks.jsonl"
    report_path = default / "chunking_report.json"
    first = chunks_path.read_bytes(), report_path.read_bytes()
    report = json.loads(first[1])
    assert report["chunk_count"] == 1
    assert report["chunks_sha256"] == hashlib.sha256(first[0]).hexdigest()
    assert report["document_counts"] == {"chunked": 1, "skipped": 1}
    assert report["documents"][0]["reason"] == "missing_parsing_output"

    assert main([*args, "--max-size", "256", "--max-table-rows", "1"]) == 1
    single_rows = processed / "_chunks" / "chars-256-rows-1"
    assert len((single_rows / "chunks.jsonl").read_bytes().splitlines()) == 2
    assert main(args) == 1
    assert first == (chunks_path.read_bytes(), report_path.read_bytes())
