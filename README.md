<div align="center">

<h1>🔎 Semiconductor Docs RAG</h1>

<p><strong>반도체 기술 문서에서 근거를 찾고, 출처와 함께 답하는 한국어 RAG</strong></p>
<p>공개 기술 자료의 본문·표·페이지를 연결하고, 검색과 답변의 정확성을 실험으로 검증합니다.</p>

<p>
  <img src="https://img.shields.io/badge/Status-Planning-5319e7" alt="개발 상태: 기획 및 설계">
  <img src="https://img.shields.io/badge/Domain-Semiconductor-1d76db" alt="분야: 반도체">
  <img src="https://img.shields.io/badge/Approach-RAG-0e8a16" alt="목표 접근 방식: RAG">
</p>

<p>
  <a href="#overview">소개</a> ·
  <a href="#features">목표 기능</a> ·
  <a href="#getting-started">시작하기</a> ·
  <a href="#roadmap">로드맵</a> ·
  <a href="https://github.com/BBungya/semiconductor-docs-rag/issues">이슈</a>
</p>

</div>

<a id="overview"></a>

## 💡 프로젝트 소개

반도체 기술 자료는 영어 PDF, 복잡한 표, 유사한 제품명과 여러 문서 버전으로 나뉘어 있습니다. 필요한 내용을 찾더라도 수치의 단위·측정 조건·출처 페이지를 다시 확인해야 합니다.

**Semiconductor Docs RAG**는 공개 기술 자료에서 질문과 관련된 근거를 검색하고, 그 근거에 기반한 한국어 답변을 제공하기 위한 프로젝트입니다. RAG(Retrieval-Augmented Generation)는 외부 문서에서 찾은 내용을 언어 모델의 답변 근거로 사용하는 방식입니다.

기술 자료를 읽는 학습자와 개발자가 **답변을 확인하고 원문으로 돌아갈 수 있는 흐름**을 만들며, 검색 방식과 모델을 바꾸었을 때 정확성·지연·비용이 어떻게 달라지는지 기록합니다.

<a id="features"></a>

## ✨ 목표 기능

| 기능 | 구현 목표 | 관련 이슈 |
| --- | --- | --- |
| 📚 문서 수집·추출 | 출처·버전 관리, PDF 본문·표·OCR, 페이지 보존 | [#2](https://github.com/BBungya/semiconductor-docs-rag/issues/2)–[#5](https://github.com/BBungya/semiconductor-docs-rag/issues/5) |
| 🔍 근거 검색 | BM25·다국어 벡터 검색, 하이브리드 검색과 재정렬 | [#7](https://github.com/BBungya/semiconductor-docs-rag/issues/7)–[#9](https://github.com/BBungya/semiconductor-docs-rag/issues/9) |
| 💬 한국어 답변 | 문서·페이지 인용, 제품·단위·조건 구분, 근거 부족 시 답변 보류 | [#10](https://github.com/BBungya/semiconductor-docs-rag/issues/10) |
| 📊 재현 가능한 평가 | 검토된 질문·정답·근거, 실패 분석과 설정별 비교 | [#6](https://github.com/BBungya/semiconductor-docs-rag/issues/6), [#11](https://github.com/BBungya/semiconductor-docs-rag/issues/11)–[#12](https://github.com/BBungya/semiconductor-docs-rag/issues/12) |
| 🖥️ 서비스·운영 | API·화면, 테스트·CI, 배포·복구, 인증·문서 권한, 증분 갱신 | [#13](https://github.com/BBungya/semiconductor-docs-rag/issues/13)–[#17](https://github.com/BBungya/semiconductor-docs-rag/issues/17) |
| 🧪 고급 확장 | 질의 확장, 표·SQL·계산, 멀티모달, Graph RAG·Agent, 모델 학습 | [#18](https://github.com/BBungya/semiconductor-docs-rag/issues/18)–[#23](https://github.com/BBungya/semiconductor-docs-rag/issues/23) |

### 🧭 설계 중인 동작 흐름

```text
공개 문서 → 수집·버전 기록 → 본문·표 추출 → 페이지 정보를 포함한 청크 → 검색 인덱스
                                                                          ↓
한국어 질문 → 키워드·벡터 검색 → 결과 결합·재정렬 → 근거 선택 → LLM 답변 + 출처
                                                                          ↓
                                                        정확성·인용·지연·비용 평가
```

<a id="getting-started"></a>

## 🛠️ 시작하기

### 사전 요구사항

| 구분 | 준비 사항 |
| --- | --- |
| 지금 저장소를 확인하려면 | Git, 터미널, 텍스트 편집기 |
| 개발 환경 구성 시 | Python 버전·의존성은 [#1](https://github.com/BBungya/semiconductor-docs-rag/issues/1)에서 확정 |
| 모델·서비스 구현 시 | 선택한 모델 실행 환경 또는 API 키, DB·Docker 요구사항은 구현 후 안내 |

### 1. 저장소 복제

```bash
git clone https://github.com/BBungya/semiconductor-docs-rag.git
cd semiconductor-docs-rag
```

### 2. 개발 작업 확인

[개발 환경 구성 이슈 #1](https://github.com/BBungya/semiconductor-docs-rag/issues/1)부터 시작합니다. 각 이슈의 **할 일 → 완료 조건 → 산출물 → 선행 작업**을 확인하고, 작업 결과와 관련 PR을 남깁니다.

### 3. 설치·환경 설정·실행

실행 코드와 의존성 파일이 추가되면 검증한 설치 명령, 환경변수, 실행 방법을 이 절에 함께 업데이트합니다. 현재 실행할 서버·CLI나 배포된 서비스는 없습니다. 실제 API 키는 커밋하지 않고, 환경 설정 구현 시 변수명만 담은 예제 파일을 제공합니다.

<details>
<summary>📂 현재 저장소 구성</summary>

```text
semiconductor-docs-rag/
├── .gitignore
└── README.md
```

수집·파싱·검색·생성·평가 코드는 구현에 맞춰 추가합니다. 상세 설계, 설치 가이드, 실험 보고서가 길어지면 목적별 문서로 분리하고 이 README에서 연결합니다.

</details>

## 💬 사용 예시

다음은 **구현 후 검증할 질문 시나리오**입니다. 실제 서비스의 실행 결과나 확인된 답변을 나타내지 않습니다.

| 질문 예시 | 기대하는 동작 |
| --- | --- |
| “LLM 추론에서 메모리 대역폭이 중요한 이유는?” | 관련 기술 문서의 근거를 찾아 한국어로 설명하고 페이지를 제시 |
| “문서에 나온 제품 A와 B의 전송 속도와 조건을 비교해줘.” | 제품·버전을 구분하고 표의 값·단위·조건을 함께 표시 |
| “이전 버전과 비교해 달라진 수치는?” | 버전별 근거를 연결해 변경 사항을 설명 |
| “공개 자료에 없는 내부 공정 정보를 알려줘.” | 확인할 수 있는 근거가 없음을 안내 |

## 📏 평가 기준

검색과 답변의 실패를 구분하고, 같은 평가셋으로 방법별 결과를 비교합니다.

| 평가 대상 | 확인할 항목 |
| --- | --- |
| 검색 | Hit@k, Recall@k, MRR과 유형별 근거 회수 |
| 답변·인용 | 정답·수치·단위·조건 정확성, 인용 페이지와 주장 연결 |
| 답변 가능성 | 근거 없는 답변, 답변 가능한 질문의 과도한 거절 |
| 운영 | 단계별·전체 지연, p50/p95, 토큰·질문당 비용, 자원 사용 |

개발·검증·최종 테스트 질문을 분리하고, 문서·평가셋 버전, 모델·프롬프트·설정, Git 커밋과 실행 환경을 결과에 기록할 계획입니다. **측정 결과는 평가 구현 후 공개합니다.**

<a id="roadmap"></a>

## 🗺️ 개발 로드맵

| 단계 | 작업 | 이슈 |
| --- | --- | --- |
| 1 | 프로젝트 구조·환경·자료 조사 | [#1](https://github.com/BBungya/semiconductor-docs-rag/issues/1), [#2](https://github.com/BBungya/semiconductor-docs-rag/issues/2) |
| 2 | 수집·파싱·청킹·평가 데이터 | [#3](https://github.com/BBungya/semiconductor-docs-rag/issues/3), [#4](https://github.com/BBungya/semiconductor-docs-rag/issues/4), [#5](https://github.com/BBungya/semiconductor-docs-rag/issues/5), [#6](https://github.com/BBungya/semiconductor-docs-rag/issues/6) |
| 3 | 검색·재정렬·근거 기반 답변 | [#7](https://github.com/BBungya/semiconductor-docs-rag/issues/7), [#8](https://github.com/BBungya/semiconductor-docs-rag/issues/8), [#9](https://github.com/BBungya/semiconductor-docs-rag/issues/9), [#10](https://github.com/BBungya/semiconductor-docs-rag/issues/10) |
| 4 | 평가·실패 분석·개선 | [#11](https://github.com/BBungya/semiconductor-docs-rag/issues/11), [#12](https://github.com/BBungya/semiconductor-docs-rag/issues/12) |
| 5 | API·화면·CI·배포·보안·갱신 | [#13](https://github.com/BBungya/semiconductor-docs-rag/issues/13), [#14](https://github.com/BBungya/semiconductor-docs-rag/issues/14), [#15](https://github.com/BBungya/semiconductor-docs-rag/issues/15), [#16](https://github.com/BBungya/semiconductor-docs-rag/issues/16), [#17](https://github.com/BBungya/semiconductor-docs-rag/issues/17) |
| 6 | 고급 확장·모델·성능 실험 | [#18](https://github.com/BBungya/semiconductor-docs-rag/issues/18), [#19](https://github.com/BBungya/semiconductor-docs-rag/issues/19), [#20](https://github.com/BBungya/semiconductor-docs-rag/issues/20), [#21](https://github.com/BBungya/semiconductor-docs-rag/issues/21), [#22](https://github.com/BBungya/semiconductor-docs-rag/issues/22), [#23](https://github.com/BBungya/semiconductor-docs-rag/issues/23) |
| 7 | 문서·데모·포트폴리오 정리 | [#24](https://github.com/BBungya/semiconductor-docs-rag/issues/24) |

구현과 검증이 끝난 작업은 해당 이슈에서 결과를 확인할 수 있습니다. 세부 실행 순서는 이슈 본문의 선행 작업을 따릅니다.

<details>
<summary>🏷️ 이슈 라벨 안내</summary>

| 라벨 | 분류 |
| --- | --- |
| `planning` · `documentation` | 기획·설계와 문서화 |
| `data` | 수집·파싱·청킹·문서 관리 |
| `retrieval` · `llm` | 검색·모델·답변 생성 |
| `evaluation` · `testing` | 품질 평가·실패 분석·자동 테스트 |
| `backend` · `frontend` | 서버·API와 사용자 화면 |
| `devops` · `security` | 배포·운영과 접근 권한·정보 보호 |
| `research` · `multimodal` · `performance` | 확장 실험·이미지 처리·성능 개선 |

한 작업에 여러 라벨이 붙을 수 있습니다. [전체 라벨](https://github.com/BBungya/semiconductor-docs-rag/labels)에서 관심 분야의 이슈를 찾아보세요.

</details>

## 🔧 문제 해결

<details>
<summary>설치 파일이나 실행 명령이 보이지 않아요.</summary>

현재는 기획·설계 단계입니다. 패키지와 서버가 아직 추가되지 않았으므로, 임의의 설치 명령을 실행하기보다 [#1](https://github.com/BBungya/semiconductor-docs-rag/issues/1)과 최근 커밋을 확인하세요.

</details>

<details>
<summary>기술 문서 다운로드 링크가 만료되었거나 접근할 수 없어요.</summary>

발행 기관의 원문 페이지에서 공개 여부와 최신 주소를 확인하세요. 자료명·문제 URL·확인 날짜를 이슈로 남기고, 접근이 제한된 자료는 권한을 확인할 수 있는 공개 자료로 대체합니다.

</details>

<details>
<summary>문서와 실제 코드의 상태가 달라요.</summary>

차이가 나는 README 항목, 사용한 커밋과 재현 절차를 [Issues](https://github.com/BBungya/semiconductor-docs-rag/issues)에 남겨주세요. 기능·설정·실행 방법을 바꾸는 PR에서는 README와 관련 문서도 함께 갱신합니다.

</details>

## 🤝 지원·참여

유지 관리자: [@BBungya](https://github.com/BBungya)

- 오류·문서 수정·기능 제안: [GitHub Issues](https://github.com/BBungya/semiconductor-docs-rag/issues)
- 사용 방법·설계 관련 질문: [GitHub Discussions](https://github.com/BBungya/semiconductor-docs-rag/discussions)
- 작업을 시작할 때 기존 이슈를 확인하고, PR에 관련 이슈·변경 이유·검증 결과를 기록해주세요.
- API 키, 계정 정보, 비공개 문서는 공개 이슈·PR·로그에 첨부하지 않습니다.

## 📚 자료·학습 링크

| 링크 | 참고할 내용 |
| --- | --- |
| [SK hynix Research](https://research.skhynix.com/) | 반도체·메모리·컴퓨팅 공개 연구와 기술 자료 |
| [Samsung Semiconductor Technical Resources](https://semiconductor.samsung.com/support/tools-resources/technical-resources/) | 백서·데이터시트 등 공식 기술 자료 |
| [Docling](https://docling-project.github.io/docling/) | PDF·표·OCR 처리 후보 도구 |
| [Sentence Transformers](https://sbert.net/) | 임베딩·검색·재정렬 모델 |
| [Qdrant Hybrid Queries](https://qdrant.tech/documentation/search/hybrid-queries/) | 검색 결과 결합과 다단계 검색 |
| [Ragas Metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/) | RAG 평가 지표 |

위 도구는 검토 대상이며, 채택한 도구와 버전은 구현 시 확정해 기록합니다. 이 프로젝트는 공개 자료를 활용하는 개인 프로젝트로, 자료 발행 기업의 공식 서비스나 협업 프로젝트가 아닙니다.

## 📝 변경 내역

| 날짜 | 내용 |
| --- | --- |
| 2026-10-23 | 개발 로드맵 24개 이슈 구성, 분야별 라벨 적용, 프로젝트 소개·시작 방법·평가 계획·지원 안내 작성 |

변경 내역이 길어지면 별도 변경 로그로 분리합니다. 세부 수정은 [커밋 이력](https://github.com/BBungya/semiconductor-docs-rag/commits/main/)에서 확인할 수 있습니다.

## 📄 라이선스·자료 이용

코드 라이선스는 **미정**이며, 현재 저장소에 LICENSE 파일이 없습니다. 코드 사용·수정·재배포 조건은 라이선스가 추가될 때 명시합니다.

기술 문서·표·그림·추출 데이터에는 각 원저작자의 이용 조건이 적용됩니다. 원문 링크와 자료별 조건을 기록하고, 공개 가능한 자료와 직접 제작한 예제를 구분해 관리합니다.

---

<p align="center"><strong>답변의 근거를 확인하고, 개선의 근거를 기록합니다.</strong></p>
