import hashlib
import json

import pytest

from semiconductor_rag.chunking.inputs import iter_chunking_inputs
from semiconductor_rag.ingestion.storage import Store, atomic_json


@pytest.mark.parametrize(
    ("parse_status", "change", "expected"),
    [
        ("parsed", None, "ready"),
        ("needs_review", None, "skipped"),
        ("failed", None, "skipped"),
        ("parsed", "changed_bytes", "invalid"),
        ("parsed", "wrong_version", "invalid"),
        ("parsed", "missing_report", "skipped"),
    ],
)
def test_chunking_checks_current_parse_results(tmp_path, parse_status, change, expected):
    digest = "a" * 64
    store = Store(tmp_path)
    document = {
        "current_sha256": digest,
        "source_version": "1.1",
        "versions": [
            {"sha256": digest, "file_path": "data/raw/blobs/spec.md", "registered_at": "test"}
        ],
    }
    atomic_json(
        store.state_path,
        {"schema_version": 1, "documents": {"spec": document}, "last_attempts": {}},
    )
    directory = tmp_path / "data" / "processed" / "spec" / digest
    directory.mkdir(parents=True)
    identity = {
        "schema_version": 1,
        "document_id": "spec",
        "source_sha256": digest,
        "source_version": "1.0" if change == "wrong_version" else "1.1",
    }
    block = {**identity, "block_index": 1, "block_type": "text", "text": "Capacity 32 GiB"}
    data = (json.dumps(block) + "\n").encode()
    if change != "missing_report":
        atomic_json(
            directory / "parsing_report.json",
            {
                **identity,
                "status": parse_status,
                "block_count": 1,
                "blocks_sha256": hashlib.sha256(data).hexdigest(),
            },
        )
    (directory / "blocks.jsonl").write_bytes(data + b" " if change == "changed_bytes" else data)

    (result,) = iter_chunking_inputs(tmp_path)

    assert result.status == expected
    if expected == "ready":
        assert result.blocks == (block,)
    else:
        assert result.reason
        assert result.blocks == ()
