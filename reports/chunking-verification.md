# 문서 청킹 검증 기록

2026-11-15에 프로젝트의 Markdown 예제 5개를 사용해 검증했습니다.

| 설정 | 본문 청크 | 표 청크 | 합계 | 목표 초과 |
| --- | ---: | ---: | ---: | ---: |
| 256자, 표 행 자동 묶기 | 25 | 4 | 29 | 0 |
| 256자, 표 한 행씩 | 25 | 12 | 37 | 0 |

두 설정의 모든 청크를 원문과 대조했습니다. 본문은 공백을 정리한 뒤 문서별로 이어 붙였을 때 내용과 순서가 일치했습니다. 각 청크의 제목 경로와 줄 범위가 파싱 블록을 올바르게 가리켰으며, 그 위치에서 읽은 표의 열 제목과 데이터 셀도 모두 일치했습니다. 보고서에 적힌 해시와 실제 청크 파일의 해시가 일치했습니다.

가상 메모리 사양서의 `SYN-MEM-A` 대역폭은 1.0의 `24 GB/s`와 1.1의 `28 GB/s`로 각각 유지됐습니다. 비슷한 이름의 `SYN-MEM-A2`는 두 버전 모두 `30 GB/s`로 구분됐습니다. 이 값은 각 사양서의 ‘사양표’ 20~24줄에서 확인할 수 있습니다.

기본 설정으로 다시 실행했을 때 청크 파일과 처리 보고서의 해시가 동일했습니다. 전체 자동 테스트 118개와 청킹 코드의 Ruff 검사·포맷 검사를 통과했습니다. 자동 테스트에는 PDF 페이지 경계 유지와 누락된 파싱 결과의 보고가 포함됩니다.

이 검증은 분할 결과와 원문 위치가 일치하는지 확인합니다. 최적 청크 크기를 정하려면 검색기를 연결한 뒤 같은 질문과 검색 설정으로 정답 근거를 찾는 비율을 비교해야 합니다.

## 재현

문서 등록과 파싱을 마친 프로젝트 폴더에서 실행합니다. 기본 명령을 두 번 실행해 파일 해시를 비교하고, 행 수 옵션을 적용해 아래 수치를 재현할 수 있습니다.

```powershell
uv run --locked python -X utf8 -m semiconductor_rag.chunking
Get-FileHash data/processed/_chunks/chars-256-rows-auto/chunks.jsonl
Get-FileHash data/processed/_chunks/chars-256-rows-auto/chunking_report.json
uv run --locked python -X utf8 -m semiconductor_rag.chunking --max-table-rows 1
uv run --locked pytest tests
uv run --locked ruff check src/semiconductor_rag/chunking tests/chunking
uv run --locked ruff format --check src/semiconductor_rag/chunking tests/chunking
```
