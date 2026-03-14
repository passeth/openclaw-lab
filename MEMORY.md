# MEMORY.md — Long-term Memory

## 🔴 업무 원칙 (모든 세션/채널 공통)

### 처방 설계 원칙
**모든 처방 작업은 반드시 Formulation Intelligence Engine을 거쳐야 한다.**

1. **EVAS BOM 먼저** — 교과서/일반 지식으로 처방하지 않는다. 반드시 EVAS 1,254개 제품의 실제 배합 데이터를 먼저 조회한다.
2. **엔진 검증 필수** — `formulation_engine.py`의 4-Agent 파이프라인(Retriever→Predictor→Critic→Optimizer)을 반드시 실행한다.
3. **신뢰도 스코어 공개** — 처방 제안 시 엔진의 검증 결과(신뢰도 점수, PASS/WARNING/ISSUE)를 함께 제시한다.
4. **미검증 원료 플래그** — EVAS 사용 이력 0~2회인 원료는 🚨 명시. 소량 시제 선행 권장.
5. **데이터가 직감을 이긴다** — "좋아 보이는" 원료보다 "1,254개 제품에서 검증된" 원료를 우선한다.
6. **EVAS 보유 원료만 사용** — 처방 예시 작성 시 EVAS 원료 DB(`evas_ingredient_profiles`)에 없는 성분은 제외하고, 보유 중인 유사 기능 원료로 대체한다. (2026-03-11 연구팀 요청)

> 근거: 교과서 처방(SLMI 기반) 신뢰도 35/100 vs EVAS 기반 처방 신뢰도 65/100 (2026-03-10 실증)

### 엔진 위치
- 코드: `projects/formulations/formulation_engine.py`
- L2 모델: `projects/arpt/l2_models.pkl`
- Supabase 테이블: `evas_ingredient_profiles`, `evas_cooccurrence`, `evas_base_formulas`, `evas_product_clusters`

---

## 프로젝트: ARPT (Auto Research Product Tournament)

### 핵심 사실
- **EVAS Cosmetic** CEO Sk Ji (passeth)의 화장품 R&D 자동화 프로젝트
- Karpathy autoresearch 원리 → 화장품 제품 토너먼트로 적용
- 주제 입력 → 50개 제품 수집 → 다중 지표 스코어링 → 토너먼트 → 2종 리포트

### 파이프라인 완성 (2026-03-10)
- **7개 Python 모듈** (`projects/arpt/pipeline/`)
- 전성분 수집: Supabase DB(34K) 우선 → 화해 → INCIDecoder 크롤링
- Grok 비동기: asyncio+aiohttp, 배치 5개씩
- InfraNodus API: 텍스트 네트워크 Gap 분석
- 2종 리포트: 처방 제안서(연구원) + 상품 기획 제안서(기획자)

### 인프라
- **Supabase**: Pro Plan, ref `ejbbdtjoqapheqieoohs`, org `evas`
- **InfraNodus**: API key in `.env`
- **xAI Grok**: `grok-4-1-fast-reasoning`, Responses API
- **Gist 계정**: `epicevas-lgtm`
- **Slack**: `#C0AHPSNJJH5`

### 데이터 자산
- `incidecoder_products`: 34,774건 (전성분 DB)
- `incidecoder_ingredients`: 1,320건 (성분 상세)
- `arpt_*` 5 테이블: 세션, 제품, 스코어, 라운드, Gap
- 기존 테이블: `evas_*` 7개, `cosing_*` 4개

### 유저 선호
- 데이터는 절대 버리지 않음 (Supabase JSONB 보존)
- 최신성/트렌드 중시 (올드패션 감점 포함)
- 웹사이트로 시각화 원함 (다른 에이전트 담당)

---

## 프로젝트: Formulation Intelligence System

### 데이터 자산 (Supabase)
- **EVAS BOM**: 1,254개 제품, 766종 원료, 39,415행 (실제 배합비 %)
- **시장 추론 배합비**: 565,329행 (34,000+ 시장 제품)
- **성분 과학**: cosing_function_contexts 29,961행 (기전/비호환성/농도)
- **안전성**: 1,320 성분 프로파일
- **총 12 테이블, 724,086행**

### 3-Layer 아키텍처 (승인됨)
- L1: Knowledge Base (원료 프로파일 + 공출현 + Embedding RAG)
- L2: Prediction (pH/점도/성상 예측 — XGBoost)
- L3: Agentic Verification (Retriever→Formulator→Critic→Optimizer)

### 핵심 교훈
- **EVAS BOM 먼저 조회** 후 처방 (교과서 처방 금지)
- SLMI는 EVAS 미사용 원료 → 제안 시 🚨 플래그 필수
- Supabase 쿼리 시 페이지네이션 필수 (기본 1000행 limit)

---

## 헤어라인 처방 (바이어 프로젝트)
- 5종: 지성두피/비듬/모근/손상샴푸/손상트리트먼트
- 바이어 요구: 투명 + Sulfate-Free
- CE 목표: g당 2원
- Gist: https://gist.github.com/epicevas-lgtm/bc3bbb11af285a9881cf7a751a7bc565

---

---

## 프로젝트: Formulation Intelligence Internal SaaS ⭐

### 핵심
- 2026-03-11 Sk Ji 승인 — "중요 프로젝트"
- 처방 제안→실험→결과 기록→모델 재학습 피드백 루프를 내부 SaaS로 구축
- PRD Brief: `Formulation_Intelligence/PRD_Internal_SaaS.md` (Obsidian)

### 핵심 테이블 (신규)
- `experiments` — 처방 제안 + 실험 상태 추적
- `experiment_formulas` — 실제 투입 배합
- `experiment_results` — 측정값 (즉시/안정성/관능)
- `model_training_log` — 재학습 이력

### 성공 지표
- 엔진 처방→시제 전환율 20%→50%
- pH 예측 MAE 0.5→0.3 (실험 50건 후)
- 처방 설계 시간 40% 단축

### 다음 단계
- 연구원 인터뷰 → 와이어프레임 → DB 스키마 확정 → M1 시작

---

*Last updated: 2026-03-11 08:15*
