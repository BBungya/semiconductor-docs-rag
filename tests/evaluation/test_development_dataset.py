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


def read_rows(name):
    return [
        json.loads(line)
        for line in (ROOT / "evals" / name).read_text(encoding="utf-8").splitlines()
    ]


def read_sources(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as file:
        return {
            item["document_id"]: item
            for item in csv.DictReader(file)
            if item["selection_status"] == "selected_synthetic_fixture"
        }


def verify_rows(rows, split, sources):
    assert rows
    assert len({row["question_id"] for row in rows}) == len(rows)
    assert len({" ".join(row["question"].casefold().split()) for row in rows}) == len(rows)

    for row in rows:
        question_id = row["question_id"]
        assert row["split"] == split, question_id
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


def test_evaluation_datasets_have_reviewed_sources_and_do_not_overlap():
    dev = read_sources("data/manifests/sources.csv")
    validation = read_sources("evals/validation_sources.csv")
    test = read_sources("evals/test_sources.csv")
    assert validation and test
    for first, second in ((dev, validation), (dev, test), (validation, test)):
        assert first.keys().isdisjoint(second)
        assert {row["sha256"] for row in first.values()}.isdisjoint(
            row["sha256"] for row in second.values()
        )

    splits = [
        ("dev", read_rows("dev.jsonl"), dev),
        ("validation", read_rows("validation.jsonl"), validation),
    ]
    if (ROOT / "evals/private/test.jsonl").exists():
        splits.append(("test", read_rows("private/test.jsonl"), test))

    ids, wording, groups = set(), set(), set()
    for split, rows, sources in splits:
        verify_rows(rows, split, sources)
        split_ids = {row["question_id"] for row in rows}
        split_wording = {" ".join(row["question"].casefold().split()) for row in rows}
        split_groups = {row["group_id"] for row in rows}
        assert ids.isdisjoint(split_ids)
        assert wording.isdisjoint(split_wording)
        assert groups.isdisjoint(split_groups)
        ids.update(split_ids)
        wording.update(split_wording)
        groups.update(split_groups)
