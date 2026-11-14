import hashlib
import json

from pypdf import PdfWriter

from semiconductor_rag.ingestion.storage import Store, atomic_json
from semiconductor_rag.parsing.__main__ import main


def test_cli_saves_blocks_and_review_then_records_corrupt_source(tmp_path, capsys):
    store = Store(tmp_path)
    store.blobs.mkdir(parents=True)
    markdown = b"# Spec\n\nCapacity: 32 GiB.\n"
    md_hash = hashlib.sha256(markdown).hexdigest()
    md = store.blobs / f"{md_hash}.md"
    md.write_bytes(markdown)
    pdf = store.blobs / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(pdf)
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    documents = {
        key: {
            "title": key,
            "source_version": "1.1",
            "current_sha256": digest,
            "versions": [
                {
                    "sha256": digest,
                    "file_path": source.relative_to(tmp_path).as_posix(),
                    "registered_at": "2026-11-14T00:00:00+00:00",
                }
            ],
        }
        for key, digest, source in (("spec", md_hash, md), ("blank", pdf_hash, pdf))
    }
    atomic_json(
        store.state_path, {"schema_version": 1, "documents": documents, "last_attempts": {}}
    )
    output = tmp_path / "data" / "processed"
    spec = output / "spec" / md_hash
    blank = output / "blank" / pdf_hash

    assert main(["--project-root", str(tmp_path)]) == 1
    data = (spec / "blocks.jsonl").read_bytes()
    blocks = [json.loads(line) for line in data.splitlines()]
    assert blocks[1]["text"] == "Capacity: 32 GiB."
    assert blocks[1]["location"]["line_start"] == 3
    report = json.loads((spec / "parsing_report.json").read_bytes())
    assert report["status"] == "parsed"
    assert report["block_count"] == 2
    assert report["blocks_sha256"] == hashlib.sha256(data).hexdigest()
    review = json.loads((blank / "parsing_report.json").read_bytes())
    assert review["status"] == "needs_review"
    assert review["issues"][0]["location"] == {"page_number": 1}

    md.write_bytes(b"corrupt")
    assert main(["--project-root", str(tmp_path), "--document-id", "spec"]) == 1
    report = json.loads((spec / "parsing_report.json").read_bytes())
    assert report["status"] == "failed"
    assert report["issues"][0]["code"] == "source_hash_mismatch"
    assert (spec / "blocks.jsonl").read_bytes() == b""
    assert "source_hash_mismatch" in capsys.readouterr().out
