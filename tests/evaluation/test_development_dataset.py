import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADING = re.compile(r"^(#{1,6}) (.+)$")


def section_at(lines: list[str], line_number: int) -> list[str]:
    headings: list[tuple[int, str]] = []
    for line in lines[:line_number]:
        if match := HEADING.fullmatch(line):
            level = len(match[1])
            headings = [(depth, title) for depth, title in headings if depth < level]
            headings.append((level, match[2]))
    return [title for _, title in headings]


def test_development_dataset_references_reviewed_current_sources():
    rows = [
        json.loads(line)
        for line in (ROOT / "evals/dev.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows
    assert len({row["question_id"] for row in rows}) == len(rows)
    assert len({" ".join(row["question"].casefold().split()) for row in rows}) == len(rows)

    with (ROOT / "data/manifests/sources.csv").open(encoding="utf-8-sig", newline="") as file:
        sources = {
            item["document_id"]: item
            for item in csv.DictReader(file)
            if item["selection_status"] == "selected_synthetic_fixture"
        }
    for row in rows:
        question_id = row["question_id"]
        assert row["split"] == "dev", question_id
        assert row["review"]["status"] == "verified", question_id
        assert row["review"]["note"].strip(), question_id
        assert row["expected_answer"].strip(), question_id
        groups = row["evidence_sets"]
        if row["answerable"]:
            assert groups and all(groups), question_id
            assert row["unanswerable_reason"] is None, question_id
        else:
            assert not groups and row["unanswerable_reason"].strip(), question_id
        if "multi_document" in row["types"]:
            assert all(len({ref["document_id"] for ref in group}) > 1 for group in groups)

        for ref in [ref for group in groups for ref in group] + row["reference_evidence"]:
            source = sources[ref["document_id"]]
            assert ref["source_version"] == source["version"], question_id
            raw = (ROOT / source["local_path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == ref["source_sha256"], question_id
            lines = raw.decode("utf-8-sig").splitlines()
            location = ref["location"]
            start, end = location["line_start"], location["line_end"]
            assert 1 <= start <= end <= len(lines), question_id
            assert section_at(lines, start) == location["section_path"], question_id
            assert section_at(lines, end) == location["section_path"], question_id
