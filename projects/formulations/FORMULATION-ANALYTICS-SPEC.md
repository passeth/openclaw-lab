# EVAS Formulation Analytics — 공출현 분석 & RPC 설계

> **데이터 규모:** 1,254 제품 / 766 원료 / 39,415 BOM 행 / 시장 56만 행  
> **목표:** 이 데이터에서 "EVAS의 처방 패턴"을 추출하여 새 처방 시 자동 참조

---

## Part 1: 공출현 분석 (Co-occurrence Analysis)

### 이게 뭔가?

**"어떤 원료들이 함께 자주 쓰이는가"**를 수학적으로 계산하는 것.

1,254개 제품에서 766종 원료가 어떤 조합으로 등장하는지 분석하면, 연구원 머릿속에만 있는 **"이건 같이 써야 해"** **"이건 같이 쓰면 안 돼"** 패턴이 데이터로 드러남.

### 예시

```
Glycerin과 함께 가장 자주 쓰이는 원료 Top 5:
  1. Butylene Glycol     (같이 등장 820회 / 유사도 0.91)
  2. Phenoxyethanol      (같이 등장 750회 / 유사도 0.87)
  3. 1,2-Hexanediol      (같이 등장 680회 / 유사도 0.82)
  4. Disodium EDTA       (같이 등장 650회 / 유사도 0.80)
  5. Carbomer            (같이 등장 590회 / 유사도 0.76)

→ Glycerin을 쓸 때 Butylene Glycol이 거의 항상 따라온다
→ 이 조합은 EVAS에서 820번 검증됨. "안전한 조합"
```

반대로:
```
Cocamidopropyl Betaine와 한 번도 같이 안 쓴 원료:
  - White Mineral Oil (0회)
  - Stearyl Alcohol (0회)

→ 계면활성제(세정) + 유성원료(에멀전) = 다른 카테고리
→ 또는 비호환 가능성
→ 만약 새 처방에서 이 조합을 쓰려면 ⚠️ 경고
```

### 분석 방법

**Step 1: 제품 × 원료 매트릭스 생성**

```
              Water  Glycerin  Betaine  SLES  Dimethicone ...
AOSP003         1       1        1       0        0
VMSPM08         1       1        1       0        1
ABFC000         1       1        0       0        0
...
(1,254행 × 766열)
```

1 = 사용, 0 = 미사용. 배합비(%)도 별도 매트릭스로.

**Step 2: 원료 쌍 공출현 빈도 계산**

766 × 766 = 586,756개 원료 쌍 각각에 대해:
- 함께 등장한 제품 수
- Jaccard 유사도 (A∩B / A∪B)
- 코사인 유사도 (배합비 가중)

**Step 3: 클러스터링 (원료 그룹핑)**

자주 함께 쓰이는 원료끼리 자동 그룹핑:
```
Cluster A "수용성 보습 베이스":
  Water, Glycerin, Butylene Glycol, 1,2-Hexanediol, Carbomer

Cluster B "O/W 에멀전 베이스":
  Glyceryl Stearate, Cetyl Alcohol, Stearyl Alcohol, Polysorbate 60

Cluster C "헤어 세정 베이스":
  Cocamidopropyl Betaine, Cocamide MEA, ALS, Sodium Chloride, PQ-10

Cluster D "방부/안정":
  Phenoxyethanol, Ethylhexylglycerin, Disodium EDTA
```

→ 새 처방 시 Cluster 단위로 "이 베이스 시스템을 쓸 건가?" 선택 가능

**Step 4: 제품 클러스터링 (베이스 포뮬러 자동 추출)**

1,254개 제품을 배합 패턴 기반으로 그룹핑:
```
Type 1 "ALS 샴푸" (n=150):
  평균 ALS 8%, Betaine 3%, Cocamide MEA 1.5% ...

Type 2 "지방산 비누 클렌저" (n=80):
  평균 Myristic Acid 12%, KOH 5%, Glycerin 20% ...

Type 3 "O/W 크림/로션" (n=200):
  평균 Glyceryl Stearate 3%, Cetyl Alcohol 2% ...
```

→ "투명 SF 샴푸"를 만들라고 하면, 가장 가까운 Type을 찾아서 그 **평균 배합**을 초안으로 제공

### 실용적 가치

| 활용 | 설명 |
|------|------|
| **① 검증된 조합 추천** | "이 원료를 넣으면, EVAS에서 함께 자주 쓰는 원료는 X, Y, Z" |
| **② 위험 조합 경고** | "이 두 원료는 EVAS 1,254개 제품에서 한 번도 같이 안 씀 ⚠️" |
| **③ 베이스 포뮬러 자동 생성** | "투명 샴푸 만들 때 EVAS 평균 처방은 이거" |
| **④ 원료 대체 후보** | "이 원료 대신 비슷한 공출현 패턴의 다른 원료는?" |
| **⑤ 혁신 기회 발견** | "시장에서는 같이 많이 쓰는데 EVAS는 안 쓰는 조합" |

---

## Part 2: RPC 함수 5종

### RPC가 뭔가?

Supabase에 저장해두는 **미리 만든 쿼리 함수**. 이름 하나로 복잡한 조회를 즉시 실행.  
AI가 처방할 때 "이 원료 EVAS에서 몇 번 썼어?" 같은 질문을 **1초 만에** 대답.

---

### RPC 1: `find_similar_recipes` — 유사 제품 검색

**용도:** "이런 조건의 제품, EVAS에서 만든 적 있어?"

**입력:**
```
카테고리: "hair"
주요 원료: ["Cocamidopropyl Betaine", "Menthol", "Houttuynia Cordata Extract"]
```

**출력:**
```
1위: AOSP003 (어성초 캡슐 샴푸)   — 3/3 원료 매칭, pH 5.8, 점도 5500
2위: AOSP002 (진저 쿨링 샴푸)     — 2/3 원료 매칭, pH 5.8, 점도 N/A
3위: AOSP000 (아르간 오일 샴푸)   — 1/3 원료 매칭, pH 5.5, 점도 N/A
```

**활용:**
- 새 처방 시작 전에 "가장 가까운 기존 제품"을 찾아서 베이스로 사용
- 완전히 새로운 조합 vs 기존 변형인지 판단

---

### RPC 2: `get_ingredient_usage` — 원료 사용 이력

**용도:** "이 원료, EVAS에서 몇 번, 어떤 농도로 썼어?"

**입력:**
```
원료: "Cocamidopropyl Betaine"
```

**출력:**
```
총 사용: 142/1254 제품 (11%)
농도 범위: 0.5% ~ 7.0%
평균 농도: 2.8%
주로 사용 카테고리: hair (67%), bodywash (23%), cleanser (10%)

제품별:
  VMSPM08 (밸르모나 요크마요 샴푸)     1.50%  hair
  AOSP003 (어성초 캡슐 스크럽 샴푸)     2.10%  hair
  AOSP000 (아르간 오일 샴푸)           3.00%  hair
  ...
```

**활용:**
- "EVAS에서 Betaine을 7% 쓴 적 있나?" → 있으면 검증됨, 없으면 신규 농도
- "이 원료의 EVAS 표준 농도 범위"를 처방에 반영

---

### RPC 3: `check_incompatibility` — 비호환성 체크

**용도:** "이 원료들 조합, 문제 없어?"

**입력:**
```
원료 리스트: ["Sodium Benzoate", "Niacinamide", "Citric Acid"]
```

**출력:**
```
⚠️ Sodium Benzoate:
   "Effective only below pH 5; above pH 5 activity drops sharply. 
    Avoid cationic surfactants."
   적정 농도: 0.3-0.5%

⚠️ Niacinamide:
   "Hydrolyzes to niacin (nicotinic acid) below pH 3-4, 
    causing flushing risk. Keep pH > 4.5 when combined."

→ Sodium Benzoate(pH<5 필요) + Niacinamide(pH>4.5 필요) = pH 4.5~5.0 좁은 윈도우!
```

**활용:**
- 처방 완성 전 자동 스캔 → 비호환 경고
- cosing_function_contexts의 incompatibility 필드 (29,961행) 활용

---

### RPC 4: `market_benchmark` — 시장 평균 배합비

**용도:** "시장에서 이 카테고리 제품은 보통 뭘 몇 % 넣어?"

**입력:**
```
카테고리: "shampoo" 또는 "moisturizer"
```

**출력:**
```
시장 평균 (샴푸 카테고리, 추론 배합비 기준):

 #  원료                    평균%    중간값%  사용빈도   기능
 1  Water                  65.2    67.0    98%     solvent
 2  Sodium Laureth Sulfate  8.5     9.0    72%     surfactant
 3  Cocamidopropyl Betaine  3.2     3.0    68%     surfactant
 4  Glycerin                2.1     2.0    55%     humectant
 5  Sodium Chloride         1.5     1.2    48%     viscosity
 ...
```

**활용:**
- "우리 처방이 시장 평균 대비 어디가 높고 낮은지" 비교
- "시장에서 많이 쓰지만 EVAS는 안 쓰는 원료" → 혁신 기회

---

### RPC 5: `ingredient_full_profile` — 원료 통합 프로파일

**용도:** "이 원료에 대해 아는 거 전부 보여줘"

**입력:**
```
원료: "Centella Asiatica Extract"
```

**출력:**
```
═══ Centella Asiatica Extract — 통합 프로파일 ═══

📦 EVAS 사용 이력:
   사용 횟수: 23/1254 제품
   농도 범위: 0.005% ~ 1.2%
   평균 농도: 0.15%
   주요 카테고리: skincare (65%), hair (22%), bodycare (13%)

🔬 과학 데이터 (CosIng):
   기능: SKIN CONDITIONING, ANTIOXIDANT, WOUND HEALING
   기전: "Triterpenes (asiaticoside, madecassoside) activate 
         TGF-β/Smad pathway, stimulating collagen I/III..."
   적정 농도: 0.1-1%
   비호환: "Extremely low pH (<3) may degrade glycosidic bonds"

📊 시장 벤치마크:
   시장 평균 사용률: 34% 제품에 포함
   시장 평균 농도: 0.3% (추론)

🛡️ 안전성:
   얼굴 최대: 1%
   바디 최대: 2%
   자극 리스크: Low
   감작 리스크: Very Low

📚 근거 논문: 12건
   - Bylka W (2013) "Centella in cosmetology" Level A
   - Lu L (2004) "Asiaticoside collagen synthesis" Level B
   ...
```

**활용:**
- 원료 선택 시 **한 번의 조회로 모든 정보** (EVAS 이력 + 과학 + 시장 + 안전성 + 논문)
- "EVAS에서 0.15% 평균인데 내가 1% 넣으려면?" → 시장에선 보통 0.3%, 안전 한계 1% → OK하지만 EVAS 기준 고농축

---

## Part 3: 전체 흐름 — 처방 요청이 오면

```
1. Brief 수신
   "투명 SF 어성초 샴푸 600mL"

2. RPC 1: find_similar_recipes("hair", ["Houttuynia Cordata", "Menthol"])
   → AOSP003 히트 (유사도 최고)
   → AOSP003의 실제 BOM을 베이스로 로드

3. 공출현 분석에서:
   → AOSP003 계면활성제 시스템의 "자주 함께 쓰이는 원료" 확인
   → SF 전환 시 어떤 대체 원료가 EVAS 패턴에 맞는지 추천

4. RPC 2: 각 원료의 EVAS 사용 이력 조회
   → Potassium Cocoyl Glycinate: EVAS 사용 이력 있음, 0.72%
   → SLMI: EVAS 사용 이력 0회 → 🚨 "미검증 원료"

5. RPC 3: 조합 비호환성 체크
   → 전체 원료 리스트 스캔 → 경고 있으면 표시

6. RPC 4: 시장 SF 샴푸의 평균 배합 참조
   → "시장 SF 샴푸는 보통 아미노산계 5~8%, APG 2~4%"

7. RPC 5: 핵심 원료 프로파일
   → 어성초: EVAS 평균 0.01%, 시장 평균 0.1%, 안전 한계 없음

8. 처방 생성
   → 🟢 안전 처방: AOSP003 변형 (EVAS 검증 원료만)
   → 🟡 변형 처방: 검증 원료 + 신규 1~2종
   → 🔴 혁신 처방: 시장 트렌드 반영 (실험 필요 표시)

9. 각 원료에 태그:
   ✅ EVAS 142회 사용 (검증)
   ⚠️ EVAS 3회 사용 (제한적 검증)
   🚨 EVAS 0회 (미검증, 소싱+안정성 확인 필요)
```

---

## Part 4: 데이터 강화 방향

### 추론 배합비 정확도 향상

EVAS의 **실제 BOM 1,254개**(정확한 %)를 "정답지"로 활용:

```
1. EVAS 1,254개 제품의 전성분 순서만으로 배합비 추론
2. 실제 배합비와 비교 → 추론 모델의 오차 측정
3. 오차 보정 학습 → 시장 34,000개 제품에 적용
4. 시장 전체 추론 배합비 정확도 향상
```

현재 56만 행의 confidence가 low 62% → 이 과정을 거치면 대폭 개선 가능.  
**EVAS만의 독점 자산.**

### 성상/물성 예측

1,254개 제품 중 pH(66%), 비중(86%), 점도(64%), 성상(76%) 데이터 보유:

```
배합비 입력 → pH 예측 (±0.5)
배합비 입력 → 점도 예측 (±20%)
배합비 입력 → "투명 가능 여부" 예측
```

이건 1,000개+ 데이터면 회귀 모델로 충분히 학습 가능.

---

*EVAS Cosmetic — Formulation Analytics Specification v1*  
*2026-03-10*
