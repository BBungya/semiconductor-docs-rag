"""문서 수집 CLI: 로컬 등록, PDF 다운로드와 처리 계획 확인."""

import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.ingestion.manifest import ManifestError
from semiconductor_rag.ingestion.pipeline import run_ingestion


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("양의 정수가 필요합니다")
    return number


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("유한한 양수가 필요합니다")
    return number


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/sources.csv"),
        help="출처 CSV 경로 (현재 작업 폴더 기준)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="입력 상대 경로와 결과 저장의 기준 폴더 (기본값: 현재 폴더)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="처리 계획만 출력. 저장·다운로드 없음"
    )
    parser.add_argument("--document-id", help="지정 문서만 처리")
    parser.add_argument(
        "--retry-failed", action="store_true", help="실패한 문서를 현재 선정 조건으로 재처리"
    )
    parser.add_argument("--max-attempts", type=positive_int, default=3, help="HTTP 총 시도 횟수")
    parser.add_argument("--timeout", type=positive_float, default=30.0, help="HTTP 응답 대기 초")
    parser.add_argument(
        "--max-bytes", type=positive_int, default=64 * 1024 * 1024, help="파일 크기 한도"
    )
    args = parser.parse_args(argv)
    try:
        report = run_ingestion(
            args.manifest,
            args.project_root,
            dry_run=args.dry_run,
            document_id=args.document_id,
            retry_failed=args.retry_failed,
            max_attempts=args.max_attempts,
            timeout=args.timeout,
            max_bytes=args.max_bytes,
        )
    except (ManifestError, IngestionError, OSError) as exc:
        print(f"입력/실행 오류: {exc}", file=sys.stderr)
        return 2

    labels = {
        "planned_local": "로컬 등록 예정",
        "planned_download": "다운로드 예정",
        "registered": "신규 등록",
        "changed": "내용 변경",
        "unchanged": "동일 내용",
        "failed": "실패",
        "invalid": "입력 오류",
        "skipped": "건너뜀",
    }
    if args.dry_run:
        print(f"[DRY RUN] 출처 목록: {args.manifest}")
        print("처리 계획만 표시합니다. 다운로드·파일 등록·상태 저장은 하지 않습니다.")
    else:
        print(f"실행 ID: {report['run_id']}")
    for item in report["results"]:
        reason = item.get("error_message", item["reason"])
        print(
            f"{item['line_number']}행 | {item['document_id'] or '(ID 없음)'} | "
            f"{labels[item['status']]} | {reason}"
        )
        for warning in item.get("warnings", []):
            print(f"  참고: {warning}")
    counts = report["summary"]
    if args.dry_run:
        print(
            f"총 {len(report['results'])}개 | 로컬 등록 예정 {counts.get('planned_local', 0)}개 | "
            f"다운로드 예정 {counts.get('planned_download', 0)}개 | "
            f"건너뜀 {counts.get('skipped', 0)}개 | 오류 {counts.get('invalid', 0)}개"
        )
    else:
        print(
            " | ".join(
                f"{labels[status]} {counts.get(status, 0)}개"
                for status in ("registered", "changed", "unchanged", "skipped", "failed", "invalid")
            )
        )
        print(f"실행 기록: data/ingestion/runs/{report['run_id']}.json")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
