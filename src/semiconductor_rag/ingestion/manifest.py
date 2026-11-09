"""출처 CSV를 읽고 로컬 등록·건너뜀·입력 오류로 분류한다.

파일 다운로드, 실제 파일 검증, 수집 상태 저장은 이 모듈에서 하지 않는다.
"""

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REQUIRED_COLUMNS = {
    "document_id",
    "title",
    "source_kind",
    "selection_status",
    "local_path",
}

SKIPPED_STATUSES = {"candidate", "excluded", "deferred", "pending"}


class ManifestError(ValueError):
    """헤더나 CSV 문법 등의 문제로 목록을 해석할 수 없는 경우."""


@dataclass(frozen=True)
class ManifestEntry:
    """원본 행과 분류 결과. line_number는 CSV 행이 끝나는 실제 줄 번호다."""

    line_number: int
    document_id: str
    action: Literal["local", "download", "skip", "error"]
    reason: str
    data: dict[str, str]


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    """CSV 전체를 검증하고 각 행의 처리 계획을 반환한다.

    파일 전체 문제는 ManifestError, 행별 문제는 action='error'로 구분한다.
    중복 ID는 첫 번째 행을 포함한 모든 해당 행을 오류로 처리한다.
    """
    rows: list[tuple[int, dict[str, str], bool]] = []

    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, strict=True)
            if reader.fieldnames is None:
                raise ManifestError("CSV가 비어 있습니다. 헤더가 필요합니다.")

            columns = [name.strip() for name in reader.fieldnames]
            if len(columns) != len(set(columns)):
                raise ManifestError("CSV 헤더에 중복된 열 이름이 있습니다.")
            if any(not name for name in columns):
                raise ManifestError("CSV 헤더에 이름이 비어 있는 열이 있습니다.")

            missing = REQUIRED_COLUMNS - set(columns)
            if missing:
                raise ManifestError(f"필수 열 누락: {', '.join(sorted(missing))}")

            reader.fieldnames = columns
            for raw_row in reader:
                # 열이 많으면 None 키가, 열이 적으면 None 값이 생긴다.
                invalid_columns = None in raw_row or any(
                    value is None for value in raw_row.values()
                )
                data = {
                    key: value.strip() if value is not None else ""
                    for key, value in raw_row.items()
                    if key is not None
                }
                rows.append((reader.line_num, data, invalid_columns))
    except (csv.Error, UnicodeDecodeError) as exc:
        raise ManifestError(f"CSV를 읽을 수 없습니다: {exc}") from exc

    counts = Counter(data["document_id"] for _, data, _ in rows if data["document_id"])
    entries = []

    for line_number, data, invalid_columns in rows:
        document_id = data["document_id"]
        problems = []
        if invalid_columns:
            problems.append("헤더와 행의 열 수가 다릅니다")
        for field in ("document_id", "title", "source_kind", "selection_status"):
            if not data[field]:
                problems.append(f"필수 값 누락: {field}")
        if document_id and counts[document_id] > 1:
            problems.append(f"document_id 중복: {document_id}")

        if problems:
            action, reason = "error", "; ".join(problems)
        else:
            action, reason = classify_source(data)

        entries.append(ManifestEntry(line_number, document_id, action, reason, data))

    return entries


def classify_source(
    data: dict[str, str],
) -> tuple[Literal["local", "download", "skip", "error"], str]:
    """현재 출처 목록의 선정 상태에 따라 분류한다. 과거 다운로드 상태는 무시한다."""
    status = data["selection_status"]

    if status == "selected_synthetic_fixture":
        if data["source_kind"] != "project_original_synthetic":
            return "error", "예제 선정 상태와 source_kind가 일치하지 않습니다"
        if not data["local_path"]:
            return "error", "로컬 예제의 local_path가 비어 있습니다"
        return "local", "직접 작성한 예제: local_path의 파일 등록 예정"

    if status == "selected_for_download":
        if data["source_kind"] != "external_official_candidate":
            return "error", "다운로드 선정 상태와 source_kind가 일치하지 않습니다"
        if not data.get("download_url"):
            return "error", "다운로드 선정 문서의 download_url이 비어 있습니다"
        return "download", "명시적으로 선정한 외부 PDF 다운로드 예정"

    if status.startswith("deferred_") or status in SKIPPED_STATUSES:
        reason = f"선정 상태에 따라 건너뜀: {status}"
        if data.get("selection_reason"):
            reason += f" — {data['selection_reason']}"
        return "skip", reason

    # 새 상태값이 생기면 의미를 확인한 뒤 명시적으로 분류 규칙을 추가한다.
    return "error", f"지원하지 않는 selection_status: {status}"


def main() -> int:
    """현재 분류 결과를 터미널에서 확인하기 위한 실행 함수."""
    # Windows 콘솔이 지원하지 않는 문자가 있어도 결과 출력은 계속한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/sources.csv"))
    args = parser.parse_args()

    try:
        entries = load_manifest(args.manifest)
    except (ManifestError, OSError) as exc:
        print(f"입력 오류: {exc}")
        return 2

    for entry in entries:
        print(
            f"{entry.line_number}행 | {entry.document_id or '(ID 없음)'} | "
            f"{entry.action} | {entry.reason}"
        )

    counts = Counter(entry.action for entry in entries)
    print(
        f"총 {len(entries)}개 | 로컬 등록 {counts['local']}개 | "
        f"다운로드 예정 {counts['download']}개 | 건너뜀 {counts['skip']}개 | 오류 {counts['error']}개"
    )
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
