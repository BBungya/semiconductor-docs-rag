# 공식 기술 문서 후보

수집일: 2026-11-03 (Asia/Seoul)

후보 7건 중 PDF 5개 저장, 2건은 URL과 실패 사유만 기록했습니다. 저장된 PDF는 총 64페이지입니다.

## 파일 위치

- 원문: `data/raw/official_candidates_2026-11-03/`
- 출처 목록: `data/manifests/official_candidates_2026-11-03.csv` / `official_candidates_2026-11-03.jsonl`

## 저장된 PDF

| 순서 | 문서 | 기관 | 페이지 | 파일 |
| --- | --- | --- | --- | --- |
| 1 | [Enabling inference at massive scale with hybrid storage for KV cache offloading](https://research.skhynix.com/blog/insights/detail/enabling-inference-at-massive-scale-with-hybrid-storage-for-kv-cache-offloading) | SK hynix; Seagate | 15 | `01_skhynix_seagate_kv_cache_offloading.pdf` |
| 2 | [Memory-Centric Computing with SK hynix's Domain-Specific Memory](https://hc2023.hotchips.org/assets/program/conference/day1/PIM/HC35_SKhynix_DSM_YongkeeKwon_rev3.pdf) | SK hynix | 26 | `02_skhynix_hotchips35_llm_memory_rev3.pdf` |
| 3 | [Optimizing KV Cache Offloading to CMM-D in a CXL Switch-based Memory Pool](https://semiconductor.samsung.com/support/tools-resources/technical-resources/) | Samsung Electronics | 15 | `04_samsung_kv_cache_cxl_memory_pool_2026.pdf` |
| 4 | [Compute Express Link 2.0 White Paper](https://computeexpresslink.org/resource-library/) | CXL Consortium | 4 | `06_cxl_consortium_2_0_white_paper.pdf` |
| 5 | [Compute Express Link 3.0](https://computeexpresslink.org/resource-library/) | CXL Consortium | 4 | `07_cxl_consortium_3_0_white_paper.pdf` |

## 권장 확인 순서

1. SK hynix·Seagate 백서: KV 캐시 개념, 저장 계층과 시스템 구성을 살펴보고 근거 페이지를 기록합니다.
2. CXL 2.0 백서: 기본 용어, 메모리 풀링과 스위치 관련 질문을 준비합니다.
3. CXL 3.0 백서: 2.0과 다른 기능을 비교합니다. 두 파일은 서로 다른 세대의 백서이며, 단순 개정판 비교로 취급하지 않습니다.
4. SK hynix Hot Chips 발표자료: 메모리 중심 컴퓨팅과 PIM 설명, 그림과 슬라이드 읽기 순서를 확인합니다.
5. Samsung 백서: 표·조건·수치가 많은 후보입니다. 제한 문구를 확인했으므로 색인/외부 모델 업로드/공개 전 권한 검토 대상으로 둡니다.

## 다운로드하지 못한 추가 후보

- [FMS 2025 CXLT-203-1 presentation (SK hynix)](https://files.futurememorystorage.com/proceedings/2025/20250806_CXLT-203-1_Kim_Updated.pdf): The read operation timed out
- [CXL Memory Expansion: A Closer Look on Actual Platform](https://www.micron.com/content/dam/micron/global/public/products/white-paper/cxl-memory-expansion-a-close-look-on-actual-platform.pdf): Original official URL returned 404; official asset CDN returned Request Rejected HTML instead of PDF. No valid PDF saved.

## 검증 범위

각 파일의 PDF 헤더, 읽을 수 있는 페이지 구조, 파일 크기, SHA-256 해시를 확인했습니다. 상세한 레이아웃·표·OCR 품질 검사는 아직 하지 않았습니다.
Hot Chips 파일은 pypdf에서 교차참조 오프셋 복구 경고가 발생했습니다. 파싱 단계에서 페이지 렌더링과 추출 내용을 대조하세요.
제목·발행일·버전의 확인 근거는 목록에 기록했고, 미확인 날짜는 비워 두거나 불확실성을 표시했습니다.

## 이용 조건과 Git 공개

- 원문은 기존 `.gitignore`의 `data/raw/` 규칙에 따라 Git 추적에서 제외됩니다.
- 공개 다운로드 가능 여부와 재배포·파생 데이터 공개 권한은 별개입니다. 모든 후보는 재배포 허가 미확인 상태로 기록했습니다.
- Samsung 백서는 공식 공개 URL이지만 2페이지에 Confidential과 복제·배포·파생물 제한 문구가 있습니다. 자료 채택 전 별도 검토 대상으로 표시했습니다.
- 원문·추출 본문·표·이미지·임베딩·근거 문장을 공개하기 전에 자료별 조건을 확인하세요.
- 이 작업에서는 수집과 후보 목록 작성만 수행했습니다. 프로젝트 코드·의존성·Git 설정을 바꾸거나 커밋·푸시하지 않았습니다.
