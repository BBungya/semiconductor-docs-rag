# 문서 청킹

청크는 검색기에 전달하기 좋게 나눈 문서 조각입니다. 각 조각에는 내용 외에 문서 버전과 원문 위치를 함께 기록합니다. 예를 들어 표의 숫자 `28`을 읽을 때 어떤 제품의 값인지, 단위가 무엇인지, 어느 버전에서 나왔는지 확인할 수 있습니다.

## 실행

프로젝트 폴더에서 실행합니다. 새 환경에서는 문서를 등록하고 파싱한 뒤 청킹을 실행합니다.

```powershell
uv sync --locked
uv run --locked python -X utf8 -m semiconductor_rag.ingestion
uv run --locked python -X utf8 -m semiconductor_rag.parsing
uv run --locked python -X utf8 -m semiconductor_rag.chunking
```

본문은 같은 소제목 또는 PDF 페이지 안에서 묶고, 긴 문단은 문장 사이에서 나눕니다. 표는 행 사이에서 나누며, 나뉜 조각마다 열 제목과 단위를 유지합니다. 문장 하나나 표의 한 행이 목표를 넘으면 그대로 보존하고 `exceeds_target`에 표시합니다.

기본 목표는 256자입니다. `--max-size`는 글자 수를 지정하고, `--max-table-rows`는 표 청크 한 개에 담을 최대 행 수를 지정합니다.

```powershell
uv run --locked python -X utf8 -m semiconductor_rag.chunking --max-size 128
uv run --locked python -X utf8 -m semiconductor_rag.chunking --max-table-rows 1
```

## 결과 확인

기본 결과는 `data/processed/_chunks/chars-256-rows-auto/`에 생성됩니다. 크기나 행 수 설정이 달라지면 별도 폴더에 저장합니다.

| 파일 | 확인할 내용 |
| --- | --- |
| `chunks.jsonl` | 한 줄에 청크 하나. 고유 ID, 본문 또는 표, 문서 ID·버전·해시, 원문 위치를 담습니다. PDF는 페이지 번호, Markdown은 제목 경로와 줄 범위를 기록합니다. 표는 데이터 행 범위도 기록합니다. |
| `chunking_report.json` | 실행 설정, 문서별 처리 상태, 건너뛴 이유, 청크 종류별 수, 목표를 넘은 개수와 청크 파일 해시를 기록합니다. |

파싱이 정상 완료된 현재 버전을 사용합니다. 파일 누락이나 검토가 필요한 문서는 건너뛰고, 파싱 보고서와 블록 파일의 해시가 다르면 입력 오류로 기록합니다. 모든 문서가 처리되면 종료 코드 0, 건너뛰거나 오류가 난 문서가 있으면 1, 전체 실행에 실패하면 2를 반환합니다.

256자는 예제에서 출처와 문맥 보존을 확인하기 위한 기본값입니다. 검색기를 연결한 뒤 같은 질문과 검색 설정으로 근거를 얼마나 잘 찾는지 비교할 수 있습니다. [청킹 검증 기록](../reports/chunking-verification.md)
