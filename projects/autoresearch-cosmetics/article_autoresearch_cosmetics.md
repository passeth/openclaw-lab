# 🧪 AutoResearch for Cosmetics R&D

**An autonomous AI research pipeline for cosmetics formulation, inspired by Karpathy's autoresearch**

---

## Inspiration: Karpathy's autoresearch

Andrej Karpathy released [autoresearch](https://github.com/karpathy/autoresearch) — a beautifully simple idea:

> Give an AI agent one file (`train.py`), let it autonomously run experiments overnight.
> Hypothesis → modify code → 5-min training → evaluate → keep/discard → repeat.
> Wake up to 100 experiment logs and an improved model.

The key insights:

- **`program.md` is the "code" of a research organization** — humans define direction, AI executes
- **Autonomous iteration is everything** — not one experiment, but cycles
- **Evaluation metrics enable automatic judgment** — clear criteria like val_bpb

But what if you apply this to cosmetics R&D?

---

## The Problem: Cosmetics R&D Has No train.py

The fundamental difference:

| ML Research | Cosmetics R&D |
|-------------|---------------|
| Modify train.py → GPU training | Design formula → physical prototype |
| Auto-evaluate via val_bpb | Stability/efficacy verified in the lab |
| 5 min/experiment | 4+ weeks accelerated stability |
| Just code | Papers + patents + regulations + raw material DBs |

**You can't run train.py, but you CAN automate the literature-based hypothesis validation** that eats most of a formulation chemist's time:

1. Evidence for ingredient combinations (papers, patents)
2. Regulatory compliance checks (NMPA, EU CPR, FDA)
3. Competitive product analysis (INCI lists, claims)
4. Stability risk pre-assessment

All of this is **literature-based hypothesis testing**. That's where autoresearch fits.

---

## Architecture: Cosmetics AutoResearch Pipeline

```
┌──────────────────────────────────────────────┐
│  MAIN AGENT (Claude Opus)                     │
│  Role: Hypothesis generation, cycle mgmt,     │
│        final synthesis                        │
│                                               │
│  • Receive product brief                      │
│  • Generate research hypotheses               │
│  • Delegate to Research Worker                │
│  • Synthesize → formulation amendments        │
└───────────────┬──────────────────────────────┘
                │
    ┌───────────▼───────────┐
    │  RESEARCH WORKER      │
    │  (Sub-Agent)          │
    │                       │
    │  🔍 xAI Grok          │  ← Academic/technical deep search
    │       ↓               │
    │  🧠 Kimi 2.5          │  ← Structure results + evaluate evidence
    │       ↓               │
    │  🕸️ InfraNodus        │  ← Text network + gap analysis
    │       ↓               │
    │  🧠 Kimi 2.5          │  ← Final evaluation + next hypotheses
    │       ↓               │
    │  📋 EXP-{N}.md        │  → Auto-publish to GitHub Gist
    └───────────────────────┘
```

### Why Multi-Model?

A single model could do it all. We intentionally chose different models for different cognitive functions:

- **Grok (xAI):** Real-time web search + academic literature. Covers the latest papers
- **Kimi 2.5 (Moonshot):** 128K context for bulk literature analysis. Crucial for Chinese-language papers and NMPA regulatory docs (our target market is China)
- **InfraNodus:** Not just summarization — **text network analysis**. Discovers hidden connections between topics and research gaps that researchers miss

The key: **each tool handles a different cognitive function.**

Search (explore) → Analyze (understand) → Network (structure) → Evaluate (judge)

---

## Cycle Strategy: 3-Cycle Research

Adapting autoresearch's "100 overnight experiments" for cosmetics R&D:

| Cycle | Purpose | Search Strategy |
|-------|---------|-----------------|
| **1. Exploration** | Basic hypothesis validation, core literature | Broad & shallow |
| **2. Deep Dive** | Dig into gaps/contradictions from Cycle 1 | Narrow & deep |
| **3. Synthesis** | Practical recommendations, alternatives | Actionable focus |

### Auto-Termination

- Confidence score reaches 4/5
- Two consecutive cycles yield no new information
- Hypothesis fully rejected → report direction change

### Continuity

Each EXP document ends with "next hypothesis candidates."
The next cycle evolves hypotheses based on previous findings.
**Runs daily at 4 PM via cron** — fully automated scheduling.

---

## Real-World Application: SF Shampoo for China

The first project through this pipeline:

**Product:** Scalp sebum control & volume sulfate-free shampoo  
**Market:** China domestic (NMPA general cosmetics)  
**Reference:** PHARMA21 蓬松控油轻盈洗发水

### EXP-001: Zinc PCA + Amino Acid Surfactant Stability

**Hypothesis:** Can Zinc PCA (0.3%) be stably formulated in an amino acid cleansing system?

**Findings:**
- Amino acid surfactants are actually **worse for Zinc PCA stability than SLS** (carboxylate-Zn²⁺ chelation)
- Solution: Glycinate↓ + SLMI↑ + Phytic Acid (natural chelator) + tight pH 5.0~5.3
- Clinical evidence secured for Piroctone + Zinc PCA sebum control (J Cosmet Dermatol. 2025)

**Immediate formulation changes:**
- Glycinate 10% → 8%, SLMI 4% → 6%
- EDTA → Phytic Acid swap
- pH ceiling 5.5 → 5.3

What would have taken a human 2-3 days of literature review was done in **30 minutes per cycle**.

### EXP-002: Optimal Sebum Control Active Combination (in progress)

**Hypotheses:**
- H1: Zinc PCA + Piroctone Olamine combo > individual use
- H2: Niacinamide 1% effective in rinse-off (shampoo) environment
- H3: PHA/LHA as viable alternatives to Salicylic Acid for scalp exfoliation

Currently running through the full Grok → Kimi → InfraNodus pipeline.

---

## Daily Routine: 8 AM Product Intelligence

Beyond AutoResearch, another automated pipeline runs every morning:

1. **INCIDecoder** — select 1 trending/new product
2. **Full INCI analysis** — ingredient composition, highlights, differentiation
3. **InfraNodus** — web SEO/reputation network analysis
4. **Grok search** — product reviews, ratings, market reception
5. **Auto-generate R&D planning brief**
6. **Post to research team Slack** as a Gist

The research team arrives in the morning to find a fresh R&D brief waiting in their channel.

---

## Infrastructure: OpenClaw + Multi-Model

Everything runs on [OpenClaw](https://github.com/openclaw/openclaw):

| Component | Role |
|-----------|------|
| OpenClaw Gateway | Agent orchestration, cron, messaging |
| Claude Opus | Main agent (hypothesis, synthesis) |
| Claude Sonnet | Sub-agent (Research Worker) |
| xAI Grok | Real-time academic/technical search |
| Kimi 2.5 | Bulk literature analysis + Chinese NLP |
| InfraNodus | Text network + gap analysis |
| GitHub Gist | Research output publishing |
| Telegram + Slack | Alerts + team sharing |

**Cost:** 3-4 external API calls per cycle. Hundreds of research iterations per month at a fraction of one researcher's salary.

---

## Where AI Fits in Cosmetics R&D

AI doesn't replace the formulator. It amplifies them.

**AI excels at:**
- Literature search & cross-validation (24/7, multilingual)
- Regulatory pre-screening
- Ingredient interaction risk assessment
- Competitive INCI analysis
- Research gap discovery (InfraNodus)

**Humans must do:**
- Final formulation decisions
- Lab verification (accelerated stability, efficacy tests)
- Sensory evaluation (texture, fragrance, feel)
- Market intuition & buyer communication

15 years of experience generates the hypotheses. AI validates them 24/7.
**Experience × AI = a different dimension of R&D velocity.**

---

## Open Resources

- [Formulation Brief v1](https://gist.github.com/epicevas-lgtm/5f307bb4eafe59d0da2b3205ae15b720) — formulation direction + 5 key feature points
- [Buyer Concept Sheet KR/CN](https://gist.github.com/epicevas-lgtm/dd72edfd9066d462ef9786f6cf3238b1)
- [EXP-001: Zinc PCA Stability Research](https://gist.github.com/epicevas-lgtm/860c15bd82ea3d842985af7ff86ff55e)

---

*Build & Find | Cosmetics × AI*
*15-year cosmetics veteran's AI build log*

---
---

# 🧪 화장품 R&D를 위한 AutoResearch

**Karpathy의 autoresearch에서 영감받아, 화장품 R&D에 맞게 재설계한 AI 자율 연구 파이프라인**

---

## 영감: Karpathy의 autoresearch

Andrej Karpathy가 공개한 [autoresearch](https://github.com/karpathy/autoresearch)는 단순하지만 강력한 아이디어입니다.

> AI 에이전트에게 `train.py` 하나를 주고, 밤새 자율적으로 실험을 돌리게 한다.
> 가설 → 코드 수정 → 5분 학습 → 평가 → 유지/폐기 → 반복.
> 아침에 일어나면 100개의 실험 로그와 개선된 모델이 있다.

핵심 인사이트는 이겁니다:

- **`program.md`가 연구 조직의 "코드"다** — 사람이 방향을 정의하고, AI가 실행한다
- **자율 반복이 핵심** — 1회 실험이 아니라 사이클을 돌린다
- **평가 메트릭이 자동 판단을 가능하게 한다** — val_bpb처럼 명확한 기준

그런데 이걸 화장품 R&D에 적용하면?

---

## 변형: 화장품 R&D에는 train.py가 없다

ML 연구와 화장품 R&D의 근본적 차이:

| ML Research | Cosmetics R&D |
|-------------|---------------|
| train.py 수정 → GPU 학습 | 처방 설계 → 시제품 제조 (물리적) |
| val_bpb로 자동 평가 | 안정성/효능은 실험실에서 검증 |
| 5분/실험 | 4주+ 가속안정성 |
| 코드만 있으면 됨 | 논문 + 특허 + 규제 + 원료 DB 필요 |

**train.py를 돌릴 수는 없지만, 가설을 검증하는 문헌 연구는 자동화할 수 있습니다.**

화장품 R&D에서 가장 시간이 많이 드는 단계:

1. 성분 조합의 근거 조사 (논문, 특허)
2. 규제 적합성 확인 (NMPA, EU CPR, FDA)
3. 경쟁 제품 분석 (전성분, 클레임)
4. 안정성 리스크 사전 평가

이 모든 게 **문헌 기반 가설 검증**입니다. 바로 여기에 autoresearch 패턴을 적용했습니다.

---

## 아키텍처: Cosmetics AutoResearch Pipeline

```
┌──────────────────────────────────────────────┐
│  MAIN AGENT (Claude Opus)                     │
│  역할: 가설 설정, 사이클 관리, 최종 종합       │
│                                               │
│  • 제품 기획 브리프 수신                       │
│  • 연구 가설 생성                              │
│  • Research Worker에 위임                     │
│  • 결과 종합 → 처방 수정안 도출               │
└───────────────┬──────────────────────────────┘
                │
    ┌───────────▼───────────┐
    │  RESEARCH WORKER      │
    │  (Sub-Agent)          │
    │                       │
    │  🔍 xAI Grok          │  ← 학술/기술 고급 검색
    │       ↓               │
    │  🧠 Kimi 2.5          │  ← 결과 구조화 + 근거 평가
    │       ↓               │
    │  🕸️ InfraNodus        │  ← 텍스트 네트워크 + 갭 분석
    │       ↓               │
    │  🧠 Kimi 2.5          │  ← 종합 평가 + 다음 가설
    │       ↓               │
    │  📋 EXP-{N}.md        │  → GitHub Gist 자동 발행
    └───────────────────────┘
```

### 왜 멀티 모델인가

단일 모델로도 가능하지만, 의도적으로 다른 모델을 조합했습니다:

- **Grok (xAI):** 실시간 웹 검색 + 학술 문헌 탐색에 강점. 최신 논문까지 커버
- **Kimi 2.5 (Moonshot):** 128K 컨텍스트로 대량 문헌 한번에 분석. 중국어 논문/규제 문서 처리에 강점 (중국 시장 타겟이라 특히 중요)
- **InfraNodus:** 단순 요약이 아닌 **텍스트 네트워크 분석**. 연구자가 놓치는 토픽 간 연결고리와 연구 공백(gap)을 발견

이게 핵심입니다 — **각 도구가 다른 인지 기능을 담당합니다.**

검색(탐색) → 분석(이해) → 네트워크(구조) → 평가(판단)

---

## 사이클 전략: 3-Cycle Research

autoresearch의 "밤새 100회 실험"을 화장품 R&D에 맞게 조정:

| Cycle | 목적 | 검색 전략 |
|-------|------|-----------|
| **1. 탐색** | 가설의 기본 검증, 핵심 문헌 수집 | 넓고 얕게 |
| **2. 심화** | Cycle 1에서 발견된 갭/모순 파고들기 | 좁고 깊게 |
| **3. 종합** | 실무 적용안 도출, 대안 비교 | 실용 중심 |

### 자동 종료 조건

- 신뢰도 4/5 이상 도달
- 2연속 사이클에서 새로운 정보 없음
- 가설 완전 기각 → 방향 전환 보고

### 연속성

각 EXP 문서의 마지막에 "다음 가설 후보"를 기록합니다.
다음 사이클은 이전 결과를 기반으로 가설을 진화시킵니다.
**매일 오후 4시에 자동 실행** — 크론으로 스케줄링.

---

## 실전 적용: 중국 바이어향 SF 샴푸 개발

실제로 이 파이프라인을 돌린 첫 프로젝트:

**제품:** 두피 세범 컨트롤 & 볼륨 설페이트프리 샴푸  
**시장:** 중국 내수 (NMPA 일반화장품)  
**레퍼런스:** PHARMA21 蓬松控油轻盈洗发水

### EXP-001: Zinc PCA + 아미노산 계면활성제 안정성

**가설:** Zinc PCA(0.3%)가 아미노산계 세정 시스템에서 안정적으로 배합 가능한가?

**발견:**
- 아미노산계가 SLS보다 **오히려 Zinc PCA 안정성이 더 나쁘다** (카복실기-Zn²⁺ 킬레이트)
- 해결: Glycinate↓ + SLMI↑ + Phytic Acid(천연 킬레이트) + pH 5.0~5.3 타이트 관리
- Piroctone + Zinc PCA 병용 세범 컨트롤 임상 근거 확보 (J Cosmet Dermatol. 2025)

**처방에 바로 반영된 수정사항:**
- Glycinate 10% → 8%, SLMI 4% → 6%
- EDTA → Phytic Acid 교체
- pH 상한 5.5 → 5.3

이걸 사람이 했으면 2~3일 걸렸을 문헌 조사를 **1사이클 30분**에 끝냈습니다.

### EXP-002: 세범 컨트롤 액티브 최적 조합 (진행 중)

**가설:**
- H1: Zinc PCA + Piroctone Olamine 병용 > 단독
- H2: Niacinamide 1%가 린스오프에서도 유효
- H3: SA 제외 시 PHA/LHA가 각질 관리 대안

현재 서브에이전트가 Grok 검색 + 분석 + InfraNodus 사이클 진행 중.

---

## 일일 루틴: 아침 8시 제품 인텔리전스

AutoResearch 외에 매일 아침 자동으로 돌아가는 또 다른 파이프라인:

1. **INCIDecoder** 신규/트렌딩 제품 1개 선택
2. **전성분 분석** — 성분 구성, 특징, 차별화 포인트
3. **InfraNodus** — 제품 관련 웹 SEO/평판 네트워크 분석
4. **Grok 검색** — 제품 리뷰, 평가, 시장 반응 수집
5. **제형 개발 연구 기획안** 자동 작성
6. 연구팀 **슬랙 채널에 Gist로 공유**

연구팀이 아침에 출근하면 어제 없던 R&D 기획안이 채널에 올라와 있습니다.

---

## 인프라: OpenClaw + 멀티 모델

이 모든 게 [OpenClaw](https://github.com/openclaw/openclaw) 위에서 돌아갑니다.

| 구성 요소 | 역할 |
|-----------|------|
| OpenClaw Gateway | 에이전트 오케스트레이션, 크론, 메시징 |
| Claude Opus | 메인 에이전트 (가설 설정, 종합 판단) |
| Claude Sonnet | 서브에이전트 (Research Worker) |
| xAI Grok | 실시간 학술/기술 검색 |
| Kimi 2.5 | 대량 문헌 분석 + 중국어 처리 |
| InfraNodus | 텍스트 네트워크 + 갭 분석 |
| GitHub Gist | 연구 결과 발행 |
| Telegram + Slack | 알림 + 팀 공유 |

**비용:** 사이클당 외부 API 3~4회 호출. 월 수백 건 연구를 사람 한 명 인건비의 일부로.

---

## 화장품 R&D에서 AI의 위치

AI가 처방을 대신 짜주는 게 아닙니다.

**AI가 잘하는 것:**
- 문헌 검색과 교차 검증 (24시간, 다국어)
- 규제 적합성 사전 체크
- 성분 간 상호작용 리스크 스크리닝
- 경쟁 제품 전성분 분석
- 연구 갭 발견 (InfraNodus)

**사람이 해야 하는 것:**
- 최종 처방 결정
- 실험실 검증 (가속안정성, 효능 시험)
- 관능 평가 (텍스처, 향, 사용감)
- 시장 감각과 바이어 커뮤니케이션

15년의 경험이 가설을 세우고, AI가 24시간 검증합니다.
**경험 × AI = 연구 속도의 차원이 달라집니다.**

---

## 공개 자료

- [기획안 v1](https://gist.github.com/epicevas-lgtm/5f307bb4eafe59d0da2b3205ae15b720) — 제형 처방 방향 + 5대 기능 포인트
- [바이어 컨셉시트 KR/CN](https://gist.github.com/epicevas-lgtm/dd72edfd9066d462ef9786f6cf3238b1)
- [EXP-001: Zinc PCA 안정성 연구](https://gist.github.com/epicevas-lgtm/860c15bd82ea3d842985af7ff86ff55e)

---

*Build & Find | Cosmetics × AI*
*화장품 15년차의 AI 빌드 로그*
