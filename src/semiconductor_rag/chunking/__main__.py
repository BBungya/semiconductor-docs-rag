"""문서 본문과 표를 검색용 청크 파일로 저장한다."""

import argparse
import sys
from pathlib import Path

from semiconductor_rag.chunking.pipeline import DEFAULT_MAX_SIZE, run_chunking
from semiconductor_rag.ingestion.errors import IngestionError


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력하세요")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="프로젝트 루트")
    parser.add_argument(
        "--max-size", type=_positive_int, default=DEFAULT_MAX_SIZE, help="목표 글자 수 (기본 256)"
    )
    parser.add_argument("--max-table-rows", type=_positive_int, help="표 청크 한 개의 최대 행 수")
    args = parser.parse_args(argv)
    try:
        directory, report = run_chunking(
            args.project_root, max_size=args.max_size, max_table_rows=args.max_table_rows
        )
    except (IngestionError, OSError) as exc:
        print(f"실행 오류: {exc}", file=sys.stderr)
        return 2

    for item in report["documents"]:
        reason = f" ({item['reason']})" if item["reason"] else ""
        print(f"{item['document_id']} | {item['status']} | 청크 {item['chunk_count']}개{reason}")
    print(f"청크 {report['chunk_count']}개 저장: {directory}")
    return int(any(item["status"] != "chunked" for item in report["documents"]))


if __name__ == "__main__":
    raise SystemExit(main())
