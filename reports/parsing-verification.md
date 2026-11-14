# 문서 파싱 검증 기록

2026-11-14, Windows와 Python 3.12에서 검증했습니다.

| 예제 | 전체 블록 | 표 |
| --- | ---: | ---: |
| 한국어 용어집 | 11 | 0 |
| 가상 메모리 사양 1.0 | 9 | 1 |
| 가상 메모리 사양 1.1 | 12 | 1 |
| 가상 KV 캐시 정책 | 10 | 1 |
| 영어 추론 벤치마크 | 11 | 1 |
| 합계 | 53 | 4 |

제목 24개, 본문 25개, 표 4개를 원문과 대조했습니다. 원문 줄 번호와 제목 경로, 문서 ID·버전·해시, 표의 머리글과 모든 셀이 일치했습니다. 가상 메모리 사양 1.1에서는 원문 20~24줄의 `SYN-MEM-A` 행과 `대역폭 (GB/s)` 열에 있는 `28`이 정확히 연결됐습니다. 재실행 전후로 블록 파일과 보고서 총 10개가 바이트 단위로 같았습니다.

전체 자동 테스트 105개와 파싱 코드의 Ruff 검사·포맷 검사를 통과했습니다. PDF는 직접 생성한 테스트 파일로 페이지 번호 보존, 격자 표의 수치·단위, 병합 머리글 검토 기록, 빈 페이지와 이미지 페이지 구분을 확인했습니다. 외부 PDF의 복잡한 레이아웃이나 OCR 정확도는 검증 범위 밖입니다.

## 재현

```powershell
uv sync --locked
uv run --locked python -X utf8 -m semiconductor_rag.ingestion
uv run --locked python -X utf8 -m semiconductor_rag.parsing
uv run --locked python -X utf8 -m semiconductor_rag.parsing
uv run --locked pytest tests
uv run --locked ruff check src/semiconductor_rag/parsing tests/parsing
uv run --locked ruff format --check src/semiconductor_rag/parsing tests/parsing
```

[문서 파싱 사용 안내](../docs/parsing.md)
