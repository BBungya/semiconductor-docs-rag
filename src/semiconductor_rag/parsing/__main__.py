"""등록된 Markdown과 PDF의 파싱 결과를 저장한다."""

import argparse
import sys
from pathlib import Path

from semiconductor_rag.ingestion.errors import IngestionError
from semiconductor_rag.parsing.pipeline import run_parsing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="프로젝트 루트")
    parser.add_argument("--document-id", help="지정 문서만 처리")
    args = parser.parse_args(argv)

    try:
        reports = run_parsing(args.project_root, document_id=args.document_id)
    except (IngestionError, OSError) as exc:
        print(f"실행 오류: {exc}", file=sys.stderr)
        return 2

    for report in reports:
        print(f"{report['document_id']} | {report['status']} | 블록 {report['block_count']}개")
        for issue in report["issues"]:
            print(f"  {issue['code']}: {issue['message']}")
    return int(any(report["status"] != "parsed" for report in reports))


if __name__ == "__main__":
    raise SystemExit(main())
