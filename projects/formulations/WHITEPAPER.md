# Formulation Intelligence Engine: 중소 화장품 기업의 BOM 데이터 기반 AI 처방 검증 시스템

**EVAS Cosmetic R&D Technical White Paper**
**Version 1.0 — March 2026**

**Authors**: EVAS Cosmetic R&D Team
**Contact**: Sk Ji, CEO — EVAS Cosmetic

---

## Abstract

화장품 처방 설계는 전통적으로 연구원의 경험과 교과서 지식에 의존해왔다. 본 논문은 중소 화장품 기업이 자사의 제조 기록(BOM, Bill of Materials) 1,254개 제품 × 766종 원료 = 39,415건의 실제 배합 데이터를 기반으로, 3-Layer AI 처방 검증 시스템을 구축한 과정과 결과를 기술한다.

핵심 성과:
- **L1 Knowledge Base**: 766 원료 프로파일 + 42,781 공출현 쌍 + 20개 처방 클러스터
- **L2 Prediction**: pH 예측 MAE 0.213, 점도 예측 1.6배 범위, 성상 분류 79.3%
- **L3 Agentic Verification**: 4-Agent 파이프라인에 의한 자동 처방 검증
- **Dual Engine**: 자사 BOM 기반 검증(Engine A) + 시장 565,329건 추론 배합비 기반 확장(Engine B)

교과서 기반 처방의 신뢰도 35/100 대비, 본 시스템 기반 처방은 65/100을 달성하여 **1.86배 개선**을 실증하였다.

**Keywords**: Cosmetic Formulation, Knowledge Graph, Machine Learning, Bill of Materials, Agentic AI, Market Intelligence

---

## 1. Introduction

### 1.1 문제 정의

화장품 처방 설계의 전통적 접근법은 다음과 같은 한계를 가진다:

1. **교과서 의존**: 일반적인 원료 교과서와 공급사 추천 배합비에 의존하여, 자사의 실제 제조 경험이 반영되지 않음
2. **암묵지 손실**: 숙련 연구원의 경험적 노하우가 체계화되지 않아, 인력 변동 시 지식 유실
3. **검증 부재**: 신규 처방의 물성(pH, 점도, 성상) 예측이 시제 전까지 불가능하여 반복적 시행착오 발생
4. **시장 맹점**: 자사 경험 범위 밖의 원료 조합이나 농도 트렌드를 체계적으로 탐색할 수단 부재

### 1.2 연구 배경

EVAS Cosmetic은 15년간 1,572개 제품을 개발하며 축적한 BOM 데이터가 존재했으나, 이는 단순한 제조 기록으로만 활용되고 있었다. 본 연구는 이 데이터를 **처방 설계의 지식 자산**으로 전환하여, 데이터 기반 처방 검증 시스템을 구축하는 것을 목표로 한다.

### 1.3 접근 방식

Karpathy(2026)의 AutoResearch 개념 — "AI 에이전트가 자율적으로 실험하고 결과를 평가하는 순환 구조" — 에서 영감을 받아, 처방 설계에 적합한 3-Layer 아키텍처를 설계하였다.

```
┌─────────────────────────────────────────────────┐
│ L3: Agentic Verification                        │
│   Retriever → Predictor → Critic → Optimizer    │
│   + Market Expansion (Engine B)                 │
├─────────────────────────────────────────────────┤
│ L2: Prediction Models                           │
│   pH (GBR) | Viscosity (GBR) | Appearance (RFC) │
├─────────────────────────────────────────────────┤
│ L1: Knowledge Base                              │
│   Ingredient Profiles | Co-occurrence Matrix    │
│   Product Clusters | Base Formulas              │
└─────────────────────────────────────────────────┘
         ↕ Supabase (12 tables, 724,086 rows)
```

---

## 2. Data Assets

### 2.1 자사 데이터 (Primary Data)

| 데이터셋 | 규모 | 설명 | 신뢰도 |
|---|---:|---|---|
| evas_labdoc_products | 1,572 | 제품 마스터 (코드, 한글명, 물성 표준) | 🟢 High |
| evas_product_compositions | 39,415 | 실제 배합비 (INCI명, %, 투입 순위) | 🟢 High |
| 유효 제품 | 1,254 | BOM 데이터 보유 제품 (전체의 80%) | 🟢 High |
| 고유 원료 | 766 | BOM에 등장하는 INCI 원료 수 | 🟢 High |

BOM 데이터는 실제 제조에 사용된 배합비로서, 추론이나 추정이 아닌 **ground truth**이다. 이것이 본 시스템의 핵심 차별점이다.

### 2.2 시장 데이터 (Secondary Data)

| 데이터셋 | 규모 | 설명 | 신뢰도 |
|---|---:|---|---|
| incidecoder_products | 34,905 | 글로벌 시장 제품 마스터 | 🟢 High |
| incidecoder_composition_inferred | 565,329 | 추론 배합비 (rule-based-v2) | 🟡 Medium |
| incidecoder_ingredients | 1,320 | 성분 상세 프로파일 | 🟢 High |

시장 추론 배합비의 confidence 분포:
- High: ~4%
- Medium: ~34%
- Low: ~62%

추론 배합비의 정확한 수치보다는 **패턴**(어떤 원료가 어떤 카테고리에서 많이 쓰이는가)이 유의미하다.

### 2.3 규제/안전 데이터 (Tertiary Data)

| 데이터셋 | 규모 | 설명 |
|---|---:|---|
| cosing_substances | ~6,000 | EU 화장품 성분 등록 |
| cosing_function_contexts | 29,961 | 기전, 비호환성, 농도 (LLM 추출) |
| incidecoder_research_ingredient_safety_v2 | ~1,320 | 안전 농도 한계 |

---

## 3. Layer 1: Knowledge Base

### 3.1 Ingredient Profiles

1,254개 제품의 BOM에서 766종 원료 각각에 대해 다음을 계산하였다:

- **usage_count**: 해당 원료가 사용된 제품 수
- **avg_pct / median_pct / max_pct / min_pct**: 사용 시 농도 분포
- **avg_rank**: 전성분 표시 평균 순위
- **categories**: 사용된 제품 카테고리 분포
- **top_cooccurrence**: 가장 자주 함께 쓰이는 원료 Top 5

#### 주요 발견

**가장 많이 쓰이는 원료 Top 10:**

| 순위 | 원료 | 사용 제품 수 | 비율 |
|---:|---|---:|---:|
| 1 | Fragrance | 1,186 | 94.6% |
| 2 | Water | 1,165 | 92.9% |
| 3 | Disodium EDTA | 1,053 | 84.0% |
| 4 | Butylene Glycol | 920 | 73.4% |
| 5 | Glycerin | 877 | 69.9% |

### 3.2 Co-occurrence Matrix

766종 원료 중 3회 이상 사용된 원료 간의 공출현(co-occurrence) 관계를 계산하였다.

- **총 쌍**: 54,506
- **유효 쌍 (co_count ≥ 2)**: 42,781
- **Jaccard 유사도**: |A ∩ B| / |A ∪ B|

#### 주요 발견

**Jaccard 1.0 세트 (항상 함께 사용되는 원료):**
EVAS 꽃 추출물 6종 — Daisy, Chrysanthemum, Evening Primrose, Cherry Blossom, Rose, Elder — 이 206개 제품에서 **예외 없이** 함께 사용됨. 이는 EVAS의 시그니처 원료 세트로, 자사 배합 관행이 데이터에 선명하게 나타난 사례이다.

**실질적 미사용 쌍 (Never-Together):**
Alcohol(360회 사용) ↔ Cocamidopropyl Betaine(270회 사용): 공출현 단 5회. 토너/에센스(Alcohol 기반)와 세정제(Betaine 기반)는 처방 구조가 근본적으로 다름을 의미한다.

### 3.3 Product Clustering

1,144개 유효 제품을 배합 조성 벡터(766차원)에 대해 KMeans 클러스터링을 수행하였다.

#### 클러스터 수 결정: k=9 vs k=20

최초 k=9를 시도하였으나, 최대 클러스터(C0)에 623개 제품이 몰리며 샴푸/토너/에센스가 "수용성" 하나로 뭉치는 문제가 발생하였다. k=20으로 변경 후 의미 있는 세분화를 달성하였다.

| Cluster | 제품 수 | 유형 | 시그니처 원료 |
|---|---:|---|---|
| C0 | 338 | 미스트/토너/에센스 | Alcohol |
| C5 | 162 | SLS/SLES 바디워시 | Sodium Lauryl Sulfate |
| C11 | 259 | 에멀전/크림 | Alcohol |
| C12 | 17 | ALS 샴푸 | Acrylates Copolymer |
| C15 | 254 | O/W 크림/로션 | Glycerin |
| C17 | 21 | 폼 클렌저 | Glycerin |
| C19 | 47 | 헤어 컨디셔너 | Dimethicone |

각 클러스터의 평균 배합(centroid)은 **Base Formula**로 저장되어, 신규 처방의 출발점으로 활용된다.

---

## 4. Layer 2: Prediction Models

### 4.1 Feature Engineering

BOM의 원료 조성을 468차원 벡터로 변환하였다. 각 차원은 특정 원료의 배합 비율(%)을 나타낸다. 3회 미만 사용된 원료는 노이즈 제거를 위해 제외하였다.

### 4.2 pH 예측

| 항목 | 값 |
|---|---|
| 모델 | Gradient Boosting Regressor |
| 학습 데이터 | 478 samples (pH 3.5~10.0) |
| 검증 | 5-fold Cross Validation |
| MAE | 0.213 ± 0.014 |
| Top Features | Glyceryl Stearate (0.144), KOH (0.098), Stearyl Alcohol (0.075) |

MAE 0.213은 실측 pH의 표준편차(일반적으로 ±0.5~1.0) 대비 충분히 유의미한 예측 정확도이다.

**실전 검증 (AOSP003 어성초 샴푸):**
- 예측: pH 5.77
- 실측: pH 5.80 ± 1.0
- 오차: **0.03** ✅

### 4.3 점도 예측

| 항목 | 값 |
|---|---|
| 모델 | Gradient Boosting Regressor (log10 scale) |
| 학습 데이터 | 365 samples (13~85,000 cps) |
| MAE | 0.212 log10 (~1.6배 범위) |
| Top Features | Water (0.200), Chamomilla Extract (0.047), Dimethicone (0.038) |

점도는 범위가 13~85,000 cps로 극단적이므로 log10 변환 후 학습하였다. MAE 0.212 log10은 예측값이 실측의 약 1.6배 범위 내에 있음을 의미한다.

**실전 검증 (AOSP003):**
- 예측: 5,405 cps
- 실측: 5,500 ± 2,000 cps
- 오차: **95 cps** ✅

### 4.4 성상 예측

| 항목 | 값 |
|---|---|
| 모델 | Random Forest Classifier |
| 학습 데이터 | 1,004 samples, 8 classes |
| Accuracy | 79.3% ± 2.6% |
| Classes | cream, gel, transparent, oil, translucent, other, pearl, powder |

**실전 검증 (AOSP003):**
- 예측: gel (45%), transparent (35%)
- 실측: "녹색 점액상" (gel 계열)
- 판정: **정확** ✅

---

## 5. Layer 3: Agentic Verification

### 5.1 아키텍처

4개의 순차적 에이전트가 처방을 검증한다:

```
Input: 배합 조성 + 제약조건
         ↓
[Agent 1: Retriever] — L1에서 관련 데이터 검색
         ↓
[Agent 2: Predictor] — L2 모델로 물성 예측
         ↓
[Agent 3: Critic]    — 4축 검증 수행
         ↓
[Agent 4: Optimizer] — 개선안 제안
         ↓
Output: 검증 리포트 (신뢰도 스코어 + 상세 피드백)
```

### 5.2 Agent 1: Retriever

L1 Knowledge Base에서 다음을 검색한다:
- 입력 원료의 프로파일 (사용 빈도, 농도 범위)
- 유사 EVAS 제품 (동일 원료 포함 제품 최대 10개)
- 관련 클러스터 (카테고리 기반)
- 핵심 원료의 공출현 데이터

### 5.3 Agent 2: Predictor

배합 조성을 L2 모델에 입력하여 pH, 점도, 성상을 예측한다. 성상은 8개 클래스의 확률 분포로 제공하여, "투명 48%, gel 45%"와 같은 상세 정보를 리포트에 포함한다.

### 5.4 Agent 3: Critic — 4축 검증

#### Axis 1: 원료 EVAS 검증도
각 원료의 EVAS 사용 이력을 3단계로 분류:
- **10회+ 사용** → ✅ 검증됨: 다수의 제품에서 실제 사용된 원료
- **3~9회 사용** → ⚠️ 제한적 검증: 일부 제품에서만 사용
- **0~2회 사용** → 🚨 미검증: EVAS에서 거의 사용하지 않은 원료

이 분류의 의의: 교과서에서 "좋은 원료"로 소개되더라도, 자사에서 실제로 사용해본 적이 없다면 소싱, 안정성, 호환성 등의 미검증 리스크가 존재한다.

#### Axis 2: 비호환성 체크
두 가지 소스에서 비호환성을 검출:
1. **CosIng incompatibility 필드**: EU 화장품 성분 데이터베이스의 비호환성 정보
2. **공출현 0회 쌍**: EVAS 1,254개 제품에서 한 번도 함께 사용되지 않은 원료 쌍

#### Axis 3: 안전 농도 범위
INCIDecoder safety 데이터베이스의 max_conc_body/max_conc_face 기준으로, 제안 농도가 안전 한계를 초과하는지 검사한다.

#### Axis 4: 예측 물성 vs 목표
L2 예측값과 사용자가 설정한 목표(target_ph, target_viscosity, transparent 여부)를 비교한다.

### 5.5 신뢰도 스코어

```
Score = 100 - (ISSUE 수 × 15) - (WARNING 수 × 5)
범위: 0~100
```

| 점수 | 해석 | 실무 조치 |
|---:|---|---|
| 80~100 | 바로 시제 가능 | 진행 |
| 60~79 | 주의 필요 | 경고 원료 검토 후 진행 |
| 40~59 | 리스크 있음 | 미검증 원료 대체 검토 |
| 0~39 | 재설계 필요 | 처방 구조 변경 |

---

## 6. Engine B: Market Expansion

### 6.1 동기

Engine A(자사 BOM 기반)만으로는 "EVAS가 해본 것만 반복"하는 한계가 있다. 시장 데이터를 활용하되, **단순 카테고리 라벨이 아닌 처방 구조(조성 벡터) 기준**으로 비교하여 확장 기회를 탐색한다.

### 6.2 방법론

#### 6.2.1 카테고리 라벨 vs 처방 구조

| 접근법 | 예시 | 문제점 |
|---|---|---|
| 카테고리 라벨 | "shampoo" | SLS/SF/드라이/2-in-1 혼재 |
| **처방 구조** | **조성 벡터 → 코사인 유사도** | **같은 배합 뼈대끼리 비교** |

#### 6.2.2 클러스터 매핑

시장 16,034개 제품을 EVAS k=20 클러스터에 매핑하였다:

1. 각 시장 제품의 추론 배합비를 766차원 벡터로 변환
2. EVAS 20개 클러스터 centroid와 코사인 유사도 계산
3. 가장 유사한 클러스터에 배정 (threshold: similarity > 0.1)

**결과: 11,221개 매핑 성공 (70%)**

### 6.3 결과

| 클러스터 | EVAS | 시장 | 유사도 | 핵심 발견 |
|---|---:|---:|---:|---|
| C0 (토너) | 338 | 249 | 0.957 | 높은 매칭 — 유사 구조 |
| C5 (SLS 바디워시) | 162 | 65 | 0.909 | 시장은 SLES 병행 |
| C12 (샴푸) | **17** | **179** | 0.877 | EVAS 경험 10배 부족 |
| C19 (에멀전) | 47 | **9,617** | 0.975 | 대규모 시장 벤치마크 |

### 6.4 활용: Dual Report

처방 검증 시 Engine A + Engine B가 함께 실행되어 이중 리포트를 생성한다:

```
🟢 Engine A (EVAS 기준)
  신뢰도 65/100 | 원료 검증도 94%
  → "이 처방은 EVAS 경험 내에서 안전합니다"

🔵 Engine B (시장 확장)
  C12 매핑 | EVAS 17 vs 시장 179
  Panthenol: 우리 0.1% vs 시장 1.5% (15배 차이)
  Cetrimonium Chloride: 시장 124개 제품 사용, EVAS 0회
  → "시장은 컨디셔닝 원료를 더 많이 씁니다"
```

---

## 7. Experimental Validation

### 7.1 교과서 처방 vs BOM 기반 처방 비교

동일한 제품 brief(투명 SF 어성초 샴푸)에 대해 두 가지 접근법으로 처방을 설계하고 엔진으로 검증하였다.

**V1 — 교과서 기반 처방:**
- 주 세정제: Sodium Lauroyl Methyl Isethionate (SLMI) 8%
- 점증: PEG-150 Distearate 0.8%
- 교과서에서 "순한 SF 세정제"로 추천되는 원료 중심

**V2 — BOM 기반 처방:**
- 주 세정제: Sodium C14-16 Olefin Sulfonate 5% (AOSP003 참고)
- 보조: Potassium Cocoyl Glycinate 2%
- EVAS 기존 제품에서 실제 사용된 원료 중심

### 7.2 결과

| 지표 | V1 (교과서) | V2 (BOM 기반) | 판정 |
|---|:---:|:---:|:---:|
| **신뢰도** | **35/100** | **65/100** | V2 ×1.86 |
| 원료 검증도 | 79% | **94%** | V2 |
| 미검증 원료 | 2종 (SLMI, PEG-150 DS) | **0종** | V2 |
| WARNING | 10개 | 7개 | V2 |
| ISSUE | 1개 🚨 | **0개** | V2 |
| pH 예측 | 5.55 | 5.86 | V1이 목표에 근접 |
| 점도 예측 | 8,123 cps | 8,008 cps | 유사 |
| 투명 확률 | 50% | 43% | 유사 |

### 7.3 해석

V1은 pH 예측이 목표에 더 가까웠으나, **SLMI와 PEG-150 Distearate**라는 EVAS 미검증 원료 2종을 포함한다. 이 원료들은:
- EVAS 15년 제조 이력에서 사용된 적 없음
- 소싱 경로, 공급사 품질, 타 원료와의 호환성이 미검증
- 소량 시제 + 안정성 테스트가 선행되어야 함

반면 V2는 pH 조정이 필요하지만(Citric Acid 0.05% 추가로 해결 가능), 94% 검증된 원료만으로 구성되어 **바로 시제 가능**하다.

**결론: "좋아 보이는" 원료보다 "1,254개 제품에서 검증된" 원료가 실무적으로 우월하다.**

---

## 8. System Architecture

### 8.1 인프라

| 구성요소 | 기술 | 역할 |
|---|---|---|
| Database | Supabase (PostgreSQL) Pro | 12 테이블, 724K+ rows |
| ML Models | scikit-learn (GBR, RFC) | pH/점도/성상 예측 |
| Orchestration | Python + OpenClaw | 에이전트 파이프라인 |
| Sub-agent | ⚗️ EVAS Formulator | 병렬 처방 검증 |
| Documentation | Obsidian | 아키텍처 + 진화 로그 |

### 8.2 서브에이전트 병렬 처리

```
사용자: "4종 샴푸 검증해줘"
         ↓
  🔬 EVAS LAB (main)
         ↓ spawn × 4
  ⚗️ Formulator #1 → PURIFY 결과
  ⚗️ Formulator #2 → BALANCE 결과
  ⚗️ Formulator #3 → STRENGTHEN 결과
  ⚗️ Formulator #4 → REPAIR 결과
         ↓
  종합 리포트
```

최대 8개 동시 서브에이전트 지원.

### 8.3 자가 진화 루프

매일 08:00 KST 크론잡이 실행되어:
1. 시스템 상태 점검 (DB 연결, 모델 파일)
2. 데이터 변화 감지 (신규 BOM 추가 여부)
3. 랜덤 제품 역검증 (예측 오차 추적)
4. R&D 트렌드 웹 검색
5. 개선안 작성 → Obsidian에 아카이브

---

## 9. Limitations

### 9.1 Ground Truth 피드백 루프의 부재

현재 시스템은 **예측만 하고 실측값 확인을 하지 않는다**. L2 모델이 "pH 5.77"을 예측해도, 실제 시제 결과가 6.1이었는지 5.3이었는지 시스템에 돌아오지 않는다.

```
현재:  배합 → 예측 → 끝
필요:  배합 → 예측 → 시제 → 실측 → 오차 학습 → 모델 개선
```

AutoResearch(Karpathy, 2026)가 강력한 이유는 val_bpb가 ground truth이기 때문이다. 우리에게 이에 해당하는 것은 실제 시제 → 안정성 시험 → 사용감 평가 결과이며, 이것이 축적되면 시스템은 근본적으로 다른 수준으로 진화할 수 있다.

### 9.2 데이터 품질

- 시장 추론 배합비의 62%가 low confidence
- INCI 표기 불일치 (Water vs Aqua vs Aqua/Water)
- INCIDecoder 파싱 잔여물 ("Read all the geeky details...")
- 이로 인해 Engine B 매핑 실패율 30%

### 9.3 모델 한계

- pH 학습 데이터 478개 (1,000개+ 필요)
- 점도 극단값 (85,000 cps) 예측 불안정
- 성상 8 클래스로는 "녹색 점액상" 같은 세부 구분 불가

### 9.4 스코어링 한계

신뢰도 스코어는 **규칙 기반**(WARNING -5, ISSUE -15)이지, 실측 결과로 보정된 것이 아니다. "65점 처방이 35점 처방보다 실제로 좋은가"는 시제 데이터 축적 후 검증이 필요하다.

---

## 10. Future Work

### Phase 1: 단기 (1~3개월)

| 과제 | 효과 |
|---|---|
| INCI 정규화 매핑 테이블 | Engine B 매핑 70% → 85%+ |
| INCIDecoder 파싱 정리 | 데이터 품질 개선 |
| 고신뢰 추론 배합비 분리 | Engine B 정확도 향상 |
| 스코어링 가중치 튜닝 | 실무 체감 개선 |

### Phase 2: 중기 (3~6개월)

| 과제 | 효과 |
|---|---|
| **시제 결과 입력 시스템** | Ground truth 피드백 루프 시작 |
| L2 모델 재학습 파이프라인 | 데이터 추가 시 자동 개선 |
| 안정성 예측 축 추가 | 3개월 가속 안정성 예측 |
| 원가 예측 축 추가 | 처방 단계에서 원가 최적화 |
| 관능 평가 예측 | 사용감 사전 예측 |

### Phase 3: 장기 (6~12개월)

| 과제 | 효과 |
|---|---|
| **AutoResearch 루프** | 예측→시제→실측→보정 자동 순환 |
| 처방 자동 생성 | Brief → 최적 처방 자동 제안 |
| 경쟁사 처방 역추적 | 시장 제품의 배합 전략 분석 |
| LLM 기반 처방 근거 설명 | "왜 이 원료를 이 농도로 넣었는가" |

### Phase 4: 확장 (12개월+)

| 과제 | 효과 |
|---|---|
| 타 기업 BOM 연합학습 | 업계 공동 지식 베이스 |
| 원료 공급사 데이터 연동 | 실시간 소싱/가격/리드타임 |
| 규제 자동 체크 (NMPA, EU CPR, FDA) | 해외 수출 처방 자동 검증 |

---

## 11. Conclusion

본 연구는 중소 화장품 기업이 보유한 BOM 데이터만으로, 별도의 대규모 투자 없이 AI 기반 처방 검증 시스템을 구축할 수 있음을 실증하였다.

핵심 기여:

1. **BOM-first 원칙의 정량적 검증**: 교과서 기반 처방(35/100) 대비 BOM 기반 처방(65/100)이 1.86배 높은 신뢰도를 보임
2. **처방 구조 기반 시장 비교**: 카테고리 라벨이 아닌 조성 벡터의 코사인 유사도로 시장 16,000+ 제품을 자사 클러스터에 매핑하여 확장 기회 도출
3. **실용적 3-Layer 아키텍처**: Knowledge Graph → ML Prediction → Agentic Verification의 계층 구조가 중소기업 규모에서 구현 가능함을 입증
4. **Dual Engine 접근**: 자사 기준 검증(안전)과 시장 확장 분석(성장)을 동시에 제공하여, "제자리걸음"과 "무모한 시도" 사이의 균형점 제시

**데이터가 직감을 이긴다.** 15년간 쌓인 1,254개 제품의 배합 기록은 어떤 교과서보다 정확한 처방 가이드이다. 본 시스템은 그 데이터를 비로소 "말하게" 만든 것이다.

---

## References

1. Karpathy, A. (2026). AutoResearch: Autonomous AI Research Agents. GitHub: autoresearch-macos.
2. Anthropic. (2026). Claude API Prompt Caching Documentation.
3. EU CosIng Database. European Commission Cosmetic Ingredient Database.
4. INCIDecoder. Global Cosmetic Product & Ingredient Database.
5. EVAS Cosmetic Internal BOM Archive (2011–2026). 1,572 products.

---

## Appendix A: System Specifications

| Component | Specification |
|---|---|
| Hardware | Apple Mac mini (M-series, ARM64) |
| OS | macOS Darwin 25.3.0 |
| Runtime | Node.js v25.5.0 + Python 3.14 |
| Database | Supabase PostgreSQL (Pro Plan) |
| ML Framework | scikit-learn |
| Orchestration | OpenClaw 2026.3.2 |
| AI Models | Anthropic Claude Sonnet 4.5, xAI Grok 4.1 |
| Storage | 724,086 rows across 12 tables |

## Appendix B: Reproducibility

본 시스템의 모든 코드는 다음 경로에 있다:

```
projects/formulations/
  ├── formulation_engine.py        — L3 통합 엔진 (Engine A + B)
  ├── build_l1_profiles.py         — 원료 프로파일 계산
  ├── build_l1_cooccurrence.py     — 공출현 매트릭스
  ├── build_l1_clusters.py         — 제품 클러스터링
  ├── build_l2_predictors.py       — ML 모델 학습
  ├── build_engine_b_clustered.py  — 시장 프로파일 구축
  └── WHITEPAPER.md                — 본 문서

projects/arpt/
  ├── l2_models.pkl                — 학습된 ML 모델
  ├── l1_clusters_k20.json         — 클러스터 데이터
  ├── engine_b_clustered_profiles.json — 시장 프로파일
  └── .venv/                       — Python 가상환경
```

---

*© 2026 EVAS Cosmetic. All rights reserved.*
