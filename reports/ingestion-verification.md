# 문서 수집기 검증 기록

검증일: 2026-11-09. Windows, Python 3.12 환경에서 검증했다.

## 현재 출처 목록으로 실행

| 실행 | 결과 |
| --- | --- |
| 첫 실행 | 직접 작성한 예제 신규 등록 5개, 보류 자료 건너뜀 7개 |
| 두 번째 실행 | 동일 내용 5개, 보류 자료 건너뜀 7개 |
| 저장 상태 | 문서 5개, 정상 내용 버전 5개, 보관 원본 파일 5개 |

출처 목록·예제 원문·외부 자료 선정 상태는 변경하지 않았다.
외부 사이트에 실제 다운로드 요청을 보내지 않았다.

## 자동 테스트

96개 테스트를 통과했다. pytest, Ruff 검사와 포맷 검사를 사용했다.

- CSV 입력, 중복 ID, BOM·다중 줄·잘못된 열 수
- dry-run 읽기 전용 동작, 특정 문서와 실패 항목 필터
- 로컬 파일 누락·경로 제한·질문 파일과 README 제외
- 정상·빈·손상·암호화 PDF, HTML 오류 응답과 크기 제한
- 리다이렉트, 타임아웃 후 성공·재시도 소진, 429 Retry-After
- 전송 도중 끊김과 임시 파일 정리, 잘못된 응답 인코딩
- 같은 내용 재처리, 다른 문서의 동일 파일 공유, 새 내용 버전과 이전 버전 복귀
- 새 버전 실패 시 기존 정상 버전 보존, 손상된 보관 원본 탐지
- 문서 하나 실패 후 계속 처리, 중단 후 체크포인트 기반 재실행
- 상태 파일 손상 시 덮어쓰지 않음, 동시 실행 잠금

HTTP 테스트는 httpx.MockTransport와 직접 생성한 PDF를 사용한다.
모의 HTTP 결과는 실제 외부 사이트의 접근 가능성이나 이용 허가를 입증하지 않는다.

## 재현

프로젝트 최상위에서 실행한다.

```powershell
uv run pytest tests/ingestion
uv run ruff check src/semiconductor_rag/ingestion tests/ingestion
uv run ruff format --check src/semiconductor_rag/ingestion tests/ingestion
uv run python -X utf8 -m semiconductor_rag.ingestion --dry-run
uv run python -X utf8 -m semiconductor_rag.ingestion
uv run python -X utf8 -m semiconductor_rag.ingestion
```

이미 등록된 환경에서는 첫 실행부터 unchanged(동일 내용)가 나온다.
외부 문서의 PDF 레이아웃·표·본문 추출 품질과 RAG 답변 성능은 이번 검증 대상이 아니다.
