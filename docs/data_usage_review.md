# 📋 자료 이용 조건 검토

확인일: **2026-11-03**. 문서 내부 표시와 공식 사이트 약관을 확인하고 프로젝트에서 취할 처리 방침을 기록했다. 약관을 읽었다는 사실과 재사용 허가를 확보했다는 사실은 구분한다. 아래의 `hold_pending_permission`은 확인이 끝날 때까지 활용을 보류한다는 프로젝트 운영 상태이며 모든 사용이 불법이라는 판단이 아니다.

## 자료별 확인 결과

| 문서 ID | 확인한 근거 | 확인 결과와 처리 |
| --- | --- | --- |
| skhynix-seagate-kv-offloading-2026 | PDF 15쪽 저작권 표시; Seagate 사이트 약관의 CODE OF CONDUCT, COPYRIGHT AND TRADEMARK, DOWNLOADING | 다운로드 대상으로 제공되는 자료의 다운로드와 추가 이용을 구분한다. 약관에는 비상업적 개인 이용, 검색·색인·데이터 수집 수단, 복제·배포에 관한 제한이 있다. RAG 색인·외부 API 전송·원문 공개를 포괄적으로 허용한다는 근거는 확보하지 못했다. 추가 이용 보류. |
| skhynix-hotchips35-llm-memory-2023 | PDF 3·4쪽 SK hynix 소유 자료 표시; 공식 Hot Chips 2023 프로그램 | 공개 발표 슬라이드지만 소유권 관련 표시가 있다. 해당 배포본에 적용되는 자유 재이용 허가는 찾지 못했다. 공개 호스팅만으로 권한이 확보되었다고 처리하지 않는다. 추가 이용 보류. |
| samsung-cmmd-kv-cache-pool-2026 | PDF 2쪽의 Confidential 표시와 복제·배포·수정 등에 관한 사전 서면 허가 문구 | 공개 다운로드 주소와 문서 내부 제한이 함께 존재한다. 외부 공개 주소라는 이유로 내부 제한을 무시하지 않는다. 적용 범위 또는 별도 허가 확인 전 추가 이용 보류. |
| cxl-consortium-2-white-paper | CXL Website Terms of Use 3.2·3.3; 해당 PDF | 사이트 약관은 권리 보유와 특정 허용 범위 밖의 복제·배포·가공 등에 관한 서면 허가를 규정한다. 본 백서에 대한 별도의 RAG 재이용 허가는 확보하지 못했다. 추가 이용 보류. |
| cxl-consortium-3-white-paper | CXL Website Terms of Use 3.2·3.3; 해당 PDF | 위와 동일. PDF 텍스트에서 라이선스 문구를 찾지 못했다는 사실은 이용 허가를 뜻하지 않는다. 추가 이용 보류. |
| skhynix-fms2025-cxlt2031 | 다운로드 시간 초과; 원문 미확보 | 파일 본문과 문서별 이용 조건을 검토하지 못했다. `not_reviewable_download_failed`. |
| micron-cxl-memory-expansion-platform | 기존 주소 404; 공식 자산 CDN은 PDF 대신 거부 HTML 반환 | 정상 PDF를 확보하지 못했다. 문서별 조건 미확인. `not_reviewable_download_failed`. |

PDF 쪽수는 인쇄된 슬라이드 번호가 아닌 **파일의 첫 페이지를 1로 센 위치**다. 이미지 속 표시·도표와 모든 페이지의 품질 검토가 완료되었다는 뜻은 아니다. 상세 파싱·렌더링 QA는 별도 과제다.

## 공식 근거 링크

- [Seagate 사이트 이용 약관](https://www.seagate.com/legal/website-use-terms-and-conditions/) — 2024-07-24 갱신 표시. 본 프로젝트의 검토일과 약관 갱신일은 다르다.
- [SK hynix Research 약관](https://research.skhynix.com/terms) — SK Research 서비스의 자동 접근 및 콘텐츠 권리에 관한 참고 자료. 다른 배포처의 모든 문서에 이 약관이 자동 적용된다고 가정하지 않는다.
- [Hot Chips 2023 공식 프로그램](https://hc2023.hotchips.org/) 및 [SK hynix 발표 PDF](https://hc2023.hotchips.org/assets/program/conference/day1/PIM/HC35_SKhynix_DSM_YongkeeKwon_rev3.pdf).
- [삼성 백서 원문](https://download.semiconductor.samsung.com/resources/white-paper/Optimizing_KV_Cache_Offloading_to_CMM-D_in_a_CXL_Switch-based_Memory_Pool.pdf) — 2쪽 확인.
- [CXL 사이트 이용 약관](https://computeexpresslink.org/cxl-website-terms-of-use/) 및 [공식 자료실](https://computeexpresslink.org/resource-library/). Compliance Software EULA를 백서의 이용 허가로 대신 사용하지 않는다.
- 각 문서의 상세 원문 URL·해시·파일 경로는 [sources.csv](../data/manifests/sources.csv)에 기록한다.

## 프로젝트 처리 방침

1. **외부 원문 5건:** 확보한 로컬 후보 파일은 `data/raw/`에 보관한다. 이용 조건 확인을 위해 일부 텍스트를 확인했으나, RAG 입력용 파싱·청킹·임베딩이나 공개 데모 연결은 수행하지 않았다. 상태는 `hold_pending_permission`이다.
2. **외부 전송:** 임베딩 API, LLM API, 온라인 OCR, 원격 벡터 저장소로 원문·청크·이미지를 전송하지 않는다. 약관 또는 개별 허가가 예정된 처리와 전송을 포함하는지 먼저 확인한다.
3. **공개 저장소:** 외부 원문, 추출 텍스트, 원문 이미지, 원문 기반 벡터 인덱스는 허가 확인 전 공개하지 않는다. 출처 메타데이터와 검토 기록을 관리한다. 기존 `.gitignore`의 원문·가공물·인덱스 제외 규칙을 유지한다.
4. **직접 작성 예제 5건:** [예제 폴더](../data/examples/README.md)의 명시된 문서만 로컬 개발용 입력으로 사용한다. 제3자 원문을 옮기지 않았다. 프로젝트 라이선스 선택은 이번 작업에 포함하지 않는다.
5. **별도 허가가 필요하면:** 권리자, 적용 문서/버전, 로컬 색인, 외부 서비스 전송, 공개 답변의 인용 범위, 재배포 가능 범위를 확인하고 증빙 위치를 남긴다. 이번 작업에서는 권리자에게 연락하거나 허가를 받은 사실이 없다.

## 상태를 변경할 때

- 해당 문서와 예정된 사용에 적용되는 명시적 라이선스 또는 개별 허가를 확인한다.
- 허가 범위·조건·확인 날짜·증빙 경로를 `sources.csv`와 이 문서에 함께 기록한다.
- 권리 확인과 별도로 표·단위·페이지 매핑 등 파싱 품질을 검증한다.
- 파일이 바뀌면 SHA-256과 버전을 갱신하고 기존 색인과 평가 결과의 재사용 여부를 검토한다.
