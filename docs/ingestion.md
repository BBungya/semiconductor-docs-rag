# 문서 수집 사용 안내

## 구현 기능

- CSV 필수 열·값·문서 ID 검증과 선정 상태 분류
- 프로젝트 예제 파일 검증과 SHA-256 기반 원본 보관
- HTTP 스트리밍 다운로드, 타임아웃과 제한된 재시도
- 빈 파일·HTML 응답·손상/암호화 PDF 구분
- 중복 파일 방지, 내용 버전 보존, 신규·변경 문서 목록 반환
- 특정 문서 처리와 실패 항목 재실행
- 문서 상태·실행 기록 원자적 저장과 단일 실행 잠금

이 기능은 파일 수집 단계다. PDF 본문·표 추출, 청킹·임베딩·LLM 전송은 수행하지 않는다.

## 실행 준비

프로젝트 최상위에서 실행한다. Python 3.12와 uv가 필요하다.

```powershell
uv sync --locked
```

## 실행 명령

```powershell
# 계획만 확인 (네트워크 요청·등록·상태 저장 없음)
uv run python -X utf8 -m semiconductor_rag.ingestion --dry-run

# 선정된 문서 실제 수집
uv run python -X utf8 -m semiconductor_rag.ingestion

# 목록 경로 지정
uv run python -X utf8 -m semiconductor_rag.ingestion --manifest data/manifests/sources.csv

# 문서 하나 처리
uv run python -X utf8 -m semiconductor_rag.ingestion --document-id example-glossary-ko-v1

# 이전 실패 항목만 재처리
uv run python -X utf8 -m semiconductor_rag.ingestion --retry-failed

# 재시도 예정 대상만 확인
uv run python -X utf8 -m semiconductor_rag.ingestion --retry-failed --dry-run

# 도움말
uv run python -X utf8 -m semiconductor_rag.ingestion --help
```

| 옵션 | 기본값·동작 |
| --- | --- |
| --manifest PATH | data/manifests/sources.csv, 현재 작업 폴더 기준 |
| --project-root PATH | 현재 폴더. 로컬 입력 상대 경로와 결과 저장의 기준 |
| --dry-run | 파일·상태 변경과 다운로드 없이 계획만 반환 |
| --document-id ID | 해당 문서만 처리. 없는 ID는 오류 |
| --retry-failed | 마지막 실제 시도가 failed/invalid인 ID만 선택 |
| --max-attempts N | HTTP 요청 총 3회 |
| --timeout SECONDS | HTTP 연결·읽기 등 각 대기 제한 30초. 전체 작업 시간 제한과 다름 |
| --max-bytes N | 파일 크기 한도 67108864바이트 (64 MiB) |

실패 재실행도 현재 CSV의 선정 상태를 다시 확인한다. 보류로 바뀐 자료는 요청하지 않는다.
입력 오류는 먼저 CSV를 수정해야 한다. ID가 비어 있는 행은 ID 기반 재시도로 선택할 수 없다.

## 수집 대상

| selection_status | 처리 |
| --- | --- |
| selected_synthetic_fixture | source_kind가 project_original_synthetic이고 local_path가 있는 로컬 예제 |
| selected_for_download | source_kind가 external_official_candidate이고 download_url이 있는 명시적 다운로드 대상 |
| deferred_* / candidate / excluded / deferred / pending | 건너뜀 |
| 그 외 | 알 수 없는 상태 오류 |

현재 목록의 외부 후보 7개는 보류 상태를 유지한다. 기존 downloaded 기록만으로 자동 수집하지 않는다.
외부 자료의 선정 상태를 바꿀 때는 기존 자료 검토 문서의 방침과 증빙을 함께 확인한다.
이번 구현은 sources.csv, 예제 본문과 이용 조건을 수정하지 않는다.

로컬 입력은 data/examples 아래의 Markdown/PDF를 지원한다.
안내 README, JSONL 질문·정답 파일과 프로젝트 밖 경로는 등록하지 않는다.
CSV에 명시된 예제만 처리하며 폴더 전체를 자동으로 수집하지 않는다.

## 저장 위치

```text
data/
├── raw/blobs/<sha256>.md 또는 .pdf  # 검증 후 보관한 내용 기반 원본
└── ingestion/
    ├── documents.json             # 문서별 정상 버전·현재 해시·최근 시도
    ├── runs/<run_id>.json          # 실행별 결과·요약·신규/변경 목록
    ├── tmp/*.part                 # 다운로드 중인 파일
    └── run.lock                   # 동시에 상태를 쓰지 않도록 하는 잠금
```

문서와 파일은 분리한다. 서로 다른 문서 ID가 같은 내용을 가리키면 원본 파일은 공유하고 출처 연결은 유지한다.
같은 ID의 내용이 바뀌면 새 해시 버전을 추가한다. 이전 내용으로 되돌아가도 같은 해시 버전을 중복 추가하지 않는다.
공식 version과 파일 내용 해시는 별도로 기록한다. 파일 해시 변경이 의미상의 내용 변경을 보장하지는 않는다.

목록에 기록된 sha256과 실제 파일이 다르면 경고를 남기고 실제 해시로 등록한다.
출처 목록의 해시는 자동으로 덮어쓰지 않는다. 보관 원본 자체가 손상됐다면 오류로 처리한다.

## 상태와 결과

| 상태 | 의미 |
| --- | --- |
| registered | 문서 ID의 첫 정상 버전 등록 |
| changed | 현재 정상 버전과 다른 내용으로 전환 |
| unchanged | 현재 정상 버전과 동일한 내용 |
| skipped | 선정 상태에 따라 건너뜀 |
| failed | 파일·다운로드·검증 처리 실패 |
| invalid | CSV 행 오류 |
| planned_local / planned_download | dry-run의 처리 예정 상태 |

실행 기록에는 시각(UTC), 문서 ID, 행 번호, 시도 횟수, HTTP 상태·최종 URL,
파일 경로·크기·해시·PDF 페이지 수, 오류 코드와 경고가 포함된다.
summary와 new_documents, changed_documents 등 상태별 목록도 반환한다.
원본 파일·실제 실행 기록은 Git에서 제외하고, 재현 가능한 검증 결과만 보고서로 공개한다.

## 실패와 복구

- 408·429·500·502·503·504와 일시적 네트워크 오류를 제한적으로 재시도한다.
- 401·403·404 등은 그대로 실패를 기록한다.
- Retry-After를 해석한다. 60초를 넘는 대기가 요구되면 한도를 무시해 재요청하지 않고 실패를 기록한다.
- 검증 실패한 다운로드의 임시 파일은 정리하고 기존 정상 버전은 보존한다.
- 문서 하나의 처리 실패 후 다음 문서를 처리한다.
- 상태·실행 기록은 임시 파일 후 교체하며, 각 결과마다 체크포인트를 저장한다.
- 중단 후 재실행하면 내용 기반 원본과 버전 해시로 중복을 방지한다.
- 상태 JSON이 손상됐으면 초기화하지 않고 오류를 낸다. 백업을 확인해 복구한다.
- 강제 종료로 run.lock이 남았다면 기록된 PID의 프로세스가 끝났는지 확인한 뒤 잠금 파일만 정리한다.
  실행 중인 프로세스의 잠금을 제거하지 않는다.
- 파일 시스템·상태 저장 같은 전체 실행 오류는 종료 코드 2로 보고한다.
- PDF 기본 검증은 파일 전체의 레이아웃·표·텍스트 추출 품질을 보장하지 않는다. 상세 파싱은 #4에서 다룬다.

## 종료 코드

| 코드 | 의미 |
| --- | --- |
| 0 | 선택한 대상 처리 성공 또는 모두 건너뜀 |
| 1 | 문서별 failed/invalid 포함 |
| 2 | 옵션·입력 파일·상태·전체 실행 오류 |

## 검증

```powershell
uv run pytest tests/ingestion
uv run ruff check src/semiconductor_rag/ingestion tests/ingestion
uv run ruff format --check src/semiconductor_rag/ingestion tests/ingestion
```

다운로드 자동 테스트는 실제 외부 사이트 대신 httpx.MockTransport와 직접 만든 PDF를 사용한다.
[검증 기록](../reports/ingestion-verification.md)을 참고한다.

