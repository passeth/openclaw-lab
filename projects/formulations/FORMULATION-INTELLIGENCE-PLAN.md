# EVAS Formulation Intelligence System — 설계안 v2

> **v1의 가정:** "데이터가 없다" → **틀렸다. 데이터가 이미 있다.**  
> **v2의 출발점:** Supabase에 이미 EVAS BOM, 시장 추론 배합비, 성분 기전, 규제 데이터가 있다.  
> 문제는 데이터 수집이 아니라 **연결과 활용**.

---

## 1. 현재 보유 데이터 자산 전수 조사

### 1-1. EVAS 내부 데이터

| 테이블 | 행 수 | 내용 | 가치 |
|--------|------:|------|------|
| `evas_labdoc_products` | **1,572** | 제품 마스터 (성상, pH, 비중, 점도, 화장품 유형) | ★★★★★ |
| `evas_product_compositions` | **39,415** | **실제 BOM — 배합비(%)까지 포함** (70개 제품) | ★★★★★ |
| `evas_research_tech_reports_v2` | **738** | AI 생성 기술 리포트 (마크다운) | ★★★☆☆ |

### 1-2. 시장 데이터

| 테이블 | 행 수 | 내용 | 가치 |
|--------|------:|------|------|
| `incidecoder_composition_inferred` | **565,329** | **시장 제품 추론 배합비** (estimated %) | ★★★★★ |
| `incidecoder_products` | **34,905** | 시장 제품 전성분 | ★★★★☆ |
| `incidecoder_ingredients` | **1,320** | 성분 상세 정보 | ★★★★☆ |

### 1-3. 성분 과학 데이터

| 테이블 | 행 수 | 내용 | 가치 |
|--------|------:|------|------|
| `cosing_function_contexts` | **29,961** | **성분 기전, 적정 농도, 비호환성** | ★★★★★ |
| `cosing_substance_functions` | **29,985** | 성분-기능 매핑 | ★★★★☆ |
| `cosing_substances` | **18,942** | EU CosIng 물질 DB | ★★★★☆ |
| `cosing_regulations` | **2,379** | 규제 제한/금지 | ★★★★★ |
| `incidecoder_research_ingredient_evidence_v2` | **5,993** | PubMed 근거 (논문, 기전, 농도) | ★★★★☆ |
| `incidecoder_research_ingredient_safety_v2` | **1,320** | 안전성 프로파일 (max 농도, 자극성, 광감성) | ★★★★★ |

### 총합: **724,086행**, 12개 테이블

---

## 2. 핵심 발견 — "내가 몰랐던 EVAS의 실제"

### 2-1. 내 처방 vs EVAS 실제 처방 — 충격적 괴리

**AOSP003 (샤샤 어성초 캡슐 스크럽 샴푸)** = 오늘 만든 지성두피 샴푸의 실제 레퍼런스:

| 항목 | 내가 제안한 처방 | EVAS 실제 처방 (AOSP003) | 괴리 |
|------|:---:|:---:|:---:|
| **1차 계면활성제** | SLMI 8% | **Sodium C14-16 Olefin Sulfonate 7%** | ❌ 완전 다름 |
| **2차 계면활성제** | Betaine 7% | **Betaine 2.1%** | ❌ 비율 3배 차이 |
| **보조 계면활성제** | Coco-Glucoside 3% | **Potassium Cocoyl Glycinate 0.72%** | ❌ 원료 자체 다름 |
| **어성초 농도** | 2.0% (고농축!) | **0.01%** | ❌ **200배 차이** |
| **멘톨** | 0.3% | **0.2%** | ≒ 비슷 |
| **점증** | PEG-150 DS 0.8% | **Acrylates Copolymer 5%** | ❌ 완전 다름 |
| **방부** | Phenoxyethanol 0.8% | **Sodium Benzoate 0.4%** | ❌ 다른 시스템 |
| **SLMI 사용 이력** | 핵심 원료로 제안 | **0/19 제품에서 사용한 적 없음** | 🚨 |

**→ 내가 제안한 처방의 핵심 원료(SLMI)를 EVAS는 한 번도 써본 적이 없다.**  
**→ 어성초 "2% 고농축"이라고 했는데, 실제 EVAS는 0.01%만 쓴다.**  
**→ 이것이 바로 "아이디어는 좋지만 실용성이 부족하다"의 정체.**

### 2-2. EVAS 헤어 제품의 실제 계면활성제 패턴

| 계면활성제 | 사용 빈도 (19개 중) | EVAS 검증 |
|-----------|:---:|:---:|
| Cocamidopropyl Betaine | **9/19** (47%) | ✅ 핵심 |
| Ammonium Laureth Sulfate | **8/19** (42%) | ✅ 주력 1차 |
| Cocamide MEA | **8/19** (42%) | ✅ 거품 안정 |
| Sodium C14-16 Olefin Sulfonate | 확인 필요 | ✅ 사용 이력 |
| Potassium Cocoyl Glycinate | 확인 필요 | ✅ 아미노산계 |
| Coco-Glucoside | **1/19** (5%) | ⚠️ 거의 안 씀 |
| **SLMI** | **0/19** (0%) | ❌ **미사용** |
| **Decyl Glucoside** | **0/19** (0%) | ❌ **미사용** |

**→ Sulfate-Free 전환 시, EVAS가 실제 경험이 있는 원료:**
- Potassium Cocoyl Glycinate (AOSP003에서 사용)
- Cocamidopropyl Betaine (9/19 제품)
- 가능하면 여기서 출발해야 "검증된 안정성"

### 2-3. EVAS 고유 원료 인벤토리 (205종)

```
Top 20 (사용 빈도순):
  59회 | Water
  37회 | Fragrance
  32회 | Glycerin
  23회 | Butylene Glycol
  23회 | White Mineral Oil
  21회 | Glyceryl Stearate
  21회 | Phenoxyethanol
  20회 | Stearyl Alcohol
  20회 | Dimethicone
  19회 | Disodium EDTA
  17회 | Hydrogenated Polydecene
  17회 | Polysorbate 60
  16회 | Glycol Distearate
  16회 | Tocopheryl Acetate
  15회 | Cocamidopropyl Betaine
  14회 | 1,2-Hexanediol
  14회 | Cetyl Alcohol
  12회 | Macadamia Ternifolia Seed Oil
  11회 | Sodium Chloride
  11회 | Methylparaben
```

**→ 이 205종이 "EVAS가 검증한 원료". 여기 없는 건 "신규 소싱 필요"로 플래그.**

---

## 3. 데이터 활용 전략

### 3-1. 즉시 가능한 것 (코드 없이)

**① 처방 생성 전 EVAS BOM 자동 참조**

새 처방 요청이 오면:
1. `evas_product_compositions`에서 유사 제품 검색 (카테고리 + 제형)
2. 유사 제품의 **실제 배합비**를 베이스로 사용
3. 각 원료의 **사용 빈도** 확인 → 검증 수준 표시
4. `cosing_function_contexts`에서 **비호환성** 체크
5. `incidecoder_research_ingredient_safety_v2`에서 **안전 농도** 확인

**② 시장 벤치마킹**

`incidecoder_composition_inferred` (56만 행)에서:
- 같은 카테고리 시장 제품의 **평균 배합 패턴** 추출
- "시장에서 이 원료는 보통 몇 % 쓰는가" 자동 참조
- EVAS vs 시장 평균 비교

**③ 성분 상호작용 사전 체크**

`cosing_function_contexts`의 `incompatibility` 필드:
- 처방 내 모든 원료 쌍의 비호환성 자동 스캔
- "이 조합은 pH X 이하에서 문제" 같은 경고 자동 생성

### 3-2. RPC 함수 설계 (Supabase에 만들어야 할 것)

```sql
-- RPC 1: 유사 제품 검색 (카테고리 + 주요 원료 매칭)
CREATE OR REPLACE FUNCTION find_similar_evas_recipes(
  p_category TEXT,        -- 'hair', 'bodycare', 'skincare'
  p_key_ingredients TEXT[] -- ['Cocamidopropyl Betaine', 'Menthol']
)
RETURNS TABLE (
  product_code TEXT,
  korean_name TEXT,
  match_score INT,
  ingredient_count INT,
  ph TEXT,
  appearance TEXT
) AS $$
  SELECT 
    p.product_code,
    l.korean_name,
    COUNT(DISTINCT c2.inci_name_en) AS match_score,
    COUNT(DISTINCT c.inci_name_en) AS ingredient_count,
    l.ph_standard AS ph,
    l.appearance
  FROM evas_product_compositions p
  JOIN evas_product_compositions c ON c.product_code = p.product_code
  LEFT JOIN evas_product_compositions c2 
    ON c2.product_code = p.product_code 
    AND c2.inci_name_en = ANY(p_key_ingredients)
  LEFT JOIN evas_labdoc_products l ON l.product_code = p.product_code
  WHERE p.product_category = p_category
  GROUP BY p.product_code, l.korean_name, l.ph_standard, l.appearance
  ORDER BY match_score DESC, ingredient_count DESC
  LIMIT 10;
$$ LANGUAGE sql;

-- RPC 2: 원료 사용 이력 조회
CREATE OR REPLACE FUNCTION get_ingredient_usage(
  p_inci_name TEXT
)
RETURNS TABLE (
  product_code TEXT,
  korean_name TEXT,
  percentage NUMERIC,
  product_category TEXT,
  ph TEXT
) AS $$
  SELECT 
    c.product_code,
    l.korean_name,
    c.percentage,
    c.product_category,
    l.ph_standard AS ph
  FROM evas_product_compositions c
  LEFT JOIN evas_labdoc_products l ON l.product_code = c.product_code
  WHERE c.inci_name_en ILIKE p_inci_name
  ORDER BY c.percentage DESC;
$$ LANGUAGE sql;

-- RPC 3: 비호환성 체크 (원료 리스트 → 경고 반환)
CREATE OR REPLACE FUNCTION check_incompatibility(
  p_ingredients TEXT[]
)
RETURNS TABLE (
  inci_name TEXT,
  func TEXT,
  incompatibility TEXT,
  typical_conc TEXT
) AS $$
  SELECT 
    s.inci_name,
    fc.function,
    fc.incompatibility,
    fc.typical_conc
  FROM cosing_function_contexts fc
  JOIN cosing_substances s ON s.substance_id = fc.substance_id
  WHERE s.inci_name = ANY(p_ingredients)
    AND fc.incompatibility IS NOT NULL
    AND fc.incompatibility != '';
$$ LANGUAGE sql;

-- RPC 4: 시장 평균 배합비 (카테고리별)
CREATE OR REPLACE FUNCTION market_avg_composition(
  p_category TEXT,  -- product_category from inferred
  p_limit INT DEFAULT 20
)
RETURNS TABLE (
  inci_name TEXT,
  avg_pct NUMERIC,
  median_pct NUMERIC,
  usage_count INT,
  function_category TEXT
) AS $$
  SELECT 
    inci_name_en AS inci_name,
    ROUND(AVG(estimated_pct_mid)::numeric, 2) AS avg_pct,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY estimated_pct_mid)::numeric, 2) AS median_pct,
    COUNT(*) AS usage_count,
    MODE() WITHIN GROUP (ORDER BY function_category) AS function_category
  FROM incidecoder_composition_inferred
  WHERE product_category ILIKE '%' || p_category || '%'
    AND estimated_pct_mid > 0
  GROUP BY inci_name_en
  ORDER BY usage_count DESC
  LIMIT p_limit;
$$ LANGUAGE sql;

-- RPC 5: EVAS 원료 인벤토리 (사용 빈도 + 안전성 통합)
CREATE OR REPLACE FUNCTION evas_ingredient_profile(
  p_inci_name TEXT
)
RETURNS TABLE (
  inci_name TEXT,
  usage_count INT,
  avg_percentage NUMERIC,
  max_percentage NUMERIC,
  products_used TEXT[],
  safety_max_face TEXT,
  safety_max_body TEXT,
  irritation_risk TEXT,
  typical_conc TEXT,
  incompatibility TEXT
) AS $$
  WITH usage AS (
    SELECT 
      inci_name_en,
      COUNT(*) AS usage_count,
      ROUND(AVG(percentage)::numeric, 3) AS avg_percentage,
      MAX(percentage) AS max_percentage,
      ARRAY_AGG(DISTINCT product_code) AS products_used
    FROM evas_product_compositions
    WHERE inci_name_en ILIKE p_inci_name
    GROUP BY inci_name_en
  ),
  safety AS (
    SELECT 
      inci_name,
      max_conc_face,
      max_conc_body,
      irritation_risk,
      typical_concentration AS typical_conc
    FROM incidecoder_research_ingredient_safety_v2
    WHERE inci_name ILIKE p_inci_name
    LIMIT 1
  ),
  compat AS (
    SELECT 
      STRING_AGG(DISTINCT fc.incompatibility, '; ') AS incompatibility
    FROM cosing_function_contexts fc
    JOIN cosing_substances s ON s.substance_id = fc.substance_id
    WHERE s.inci_name ILIKE p_inci_name
      AND fc.incompatibility IS NOT NULL
      AND fc.incompatibility != ''
  )
  SELECT 
    u.inci_name_en,
    u.usage_count,
    u.avg_percentage,
    u.max_percentage,
    u.products_used,
    s.max_conc_face,
    s.max_conc_body,
    s.irritation_risk,
    s.typical_conc,
    c.incompatibility
  FROM usage u
  LEFT JOIN safety s ON TRUE
  LEFT JOIN compat c ON TRUE;
$$ LANGUAGE sql;
```

### 3-3. 머신러닝 / 통계적 접근

#### 접근 1: 성분 공출현 행렬 (Co-occurrence Matrix)

EVAS 70개 레시피에서:
- 어떤 원료 쌍이 자주 함께 사용되는가?
- 어떤 원료 쌍이 한 번도 함께 사용된 적 없는가? (비호환 가능성)
- 클러스터링 → "베이스 포뮬러 타입" 자동 분류

```python
# 의사 코드
import pandas as pd
from sklearn.cluster import KMeans
import numpy as np

# 1. 제품 × 원료 매트릭스 생성
products = get_all_products()  # 70개
ingredients = get_all_ingredients()  # 205종
matrix = np.zeros((len(products), len(ingredients)))

for i, product in enumerate(products):
    for j, ingredient in enumerate(ingredients):
        matrix[i][j] = get_percentage(product, ingredient)  # 0 if not used

# 2. 원료 공출현 (코사인 유사도)
from sklearn.metrics.pairwise import cosine_similarity
ingredient_similarity = cosine_similarity(matrix.T)
# → "이 원료와 함께 자주 사용되는 원료" 추출

# 3. 제품 클러스터링
kmeans = KMeans(n_clusters=5)  # hair/body/skin/cleanser 등
clusters = kmeans.fit_predict(matrix)
# → 각 클러스터의 "평균 포뮬러" = 베이스 레시피 자동 추출
```

#### 접근 2: 시장 데이터 + EVAS 데이터 통합 분석

`incidecoder_composition_inferred` (56만 행)에서:
- 시장 평균 배합 패턴 추출
- EVAS 배합과 시장 평균의 **차이** 분석 → EVAS의 특이점/강점 발견
- 시장에서 많이 쓰지만 EVAS가 안 쓰는 원료 → **혁신 기회**

#### 접근 3: 추론 배합비 품질 향상

현재 `incidecoder_composition_inferred`의 confidence:
- high: 4%, medium: 34%, low: 62%

EVAS의 **실제 BOM 데이터(정확한 %)**를 학습 데이터로 활용하면:
- 전성분 순서 → 배합비 추론 모델의 **calibration** 개선
- "EVAS 실제 배합비 vs 추론 배합비" 비교 → 추론 정확도 검증
- 검증된 모델로 나머지 34,000개 시장 제품의 배합비 재추론

#### 접근 4: 제형 성상 예측 모델

EVAS 데이터에 성상(appearance), pH, 점도, 비중이 있으므로:
- 배합 → 성상 예측: "이 조합으로 투명이 되는가?"
- 배합 → pH 예측
- 배합 → 점도 예측

이건 EVAS 70개 + 시장 데이터로 충분히 학습 가능.

---

## 4. 즉시 실행 — "오늘 만든 처방을 EVAS 데이터로 재검증"

### 4-1. 지성두피 샴푸 PURIFY — 실제 데이터 기반 재처방

AOSP003 (샤샤 어성초 캡슐 스크럽 샴푸)를 **실제 베이스**로:

**AOSP003 핵심 구조 (실측):**
```
Water                              78.52%
Sodium C14-16 Olefin Sulfonate      7.00%  ← 1차 (Sulfonate, not Sulfate)
Acrylates Copolymer                 5.00%  ← 점증/스크럽
Cocamidopropyl Betaine              2.10%  ← 2차
Sucrose Stearate                    1.00%  ← 유화/안정
Polysorbate 20                      0.80%
Potassium Cocoyl Glycinate          0.72%  ← 아미노산계
Lauryl Hydroxysultaine              0.52%  ← 보조 계면활성제
Menthol                             0.20%
Houttuynia Cordata Extract          0.01%  ← 어성초 (미량)
```

**SF 전환 시 실제 가능한 접근:**
- Sodium C14-16 Olefin Sulfonate → **Potassium Cocoyl Glycinate 증량** (이미 사용 이력)
- 또는 **Sodium Cocoyl Isethionate** (EVAS 미사용이지만 시장 SF 표준)
- Cocamidopropyl Betaine 비율 ↑ (9/19 제품에서 사용, 안정성 검증)
- **SLMI는 EVAS 검증 이력 0 → 리스크 플래그**

### 4-2. 새로운 처방 레포트 포맷

```
═══════════════════════════════════════════════════
📋 지성두피 샴푸 PURIFY — EVAS 데이터 기반 처방
═══════════════════════════════════════════════════

🔗 베이스: AOSP003 (샤샤 어성초 캡슐 스크럽 샴푸)
   pH 5.80±1.0 | 점도 5,500±2,000 | 성상: 알갱이가 있는 녹색 점액상
   양산 이력: ✅ | 설계자: 이인아 | 작성일: 2024-07-10

┌─────────────────────────────────────────────────────────────┐
│ # │ 원료               │  제안%  │ AOSP003 │ EVAS사용 │ 비고 │
├───┼────────────────────┼────────┼─────────┼─────────┼──────┤
│ 1 │ Water              │  75.0  │  78.52  │ 59/70  │      │
│ 2 │ K. Cocoyl Glycinate│   6.0  │   0.72  │  확인  │ SF①  │
│ 3 │ Betaine            │   5.0  │   2.10  │  9/19  │ ↑증량│
│ 4 │ Acrylates Copolymer│   5.0  │   5.00  │  확인  │ 유지 │
│ 5 │ Lauryl Hydroxysult.│   2.0  │   0.52  │  확인  │ ↑보조│
│ 6 │ 어성초 추출물        │   0.5  │   0.01  │  확인  │ ②   │
│ 7 │ Menthol            │   0.2  │   0.20  │  확인  │ 유지 │
│ ...│                   │        │         │        │      │
└─────────────────────────────────────────────────────────────┘

⚠️ 주의사항 (EVAS 실제 데이터 기반):
① SF 전환: K. Cocoyl Glycinate를 6%로 증량하면 거품량 부족 가능
   → AOSP003에서 0.72%만 사용. 6%는 EVAS 미검증 농도
   → 시장 참고: 추론 배합비 기준 아미노산계 SF 제품의 평균 3~8%
   → 소량 시제(1L)로 거품·점도·안정성 확인 필요

② 어성초: AOSP003에서 0.01%만 사용
   → 0.5%도 EVAS 기준으로는 "고농축"
   → 투명도 영향 가능성 → 시제 확인

🏭 설비: AOSP003 양산 이력 있으므로 동일 설비 사용 가능
         단, SF 전환 시 점도 변화 → 교반 조건 재설정 필요
```

---

## 5. 확장 로드맵

### Phase 1: 즉시 (이번 주)
- [x] Supabase 테이블 전수 조사 완료
- [ ] 처방 요청 시 자동으로 EVAS BOM 참조하는 워크플로우 정립
- [ ] EVAS 원료 205종 → 재고/검증 레벨 매핑

### Phase 2: RPC 구축 (1주)
- [ ] 5개 핵심 RPC 함수 Supabase에 생성
- [ ] 처방 레포트에 "EVAS 사용 이력 n회" 자동 표기
- [ ] 비호환성 자동 체크 통합

### Phase 3: 분석 (2~4주)
- [ ] 성분 공출현 행렬 분석 (70개 제품 × 205원료)
- [ ] 제품 클러스터링 → 베이스 포뮬러 자동 추출
- [ ] 시장 데이터 vs EVAS 데이터 비교 분석
- [ ] 추론 배합비 모델 calibration (EVAS 실제 BOM으로 검증)

### Phase 4: 예측 모델 (1~2개월)
- [ ] 배합 → 성상/pH/점도 예측
- [ ] "이 조합으로 투명이 되는가?" 예측기
- [ ] SF 전환 시 예상 거품량/세정력 추정

### Phase 5: 창의적 혁신 (지속)
- [ ] 시장에 있지만 EVAS에 없는 원료 조합 탐색
- [ ] EVAS 강점 원료 + 시장 트렌드 원료 매칭
- [ ] "검증된 경계 바로 바깥"에서 제안

---

## 6. 데이터 강화 기회

### 현재 약한 부분

| 데이터 | 현재 상태 | 강화 방법 |
|--------|----------|----------|
| 안정성 시험 결과 | 없음 | 연구원 엑셀/노트에서 입력 |
| 소비자 피드백 | 없음 | 리뷰/클레임 데이터 연동 |
| 설비 프로파일 | 없음 | 1회성 입력 |
| 원가 데이터 | 없음 | ERP 연동 또는 수동 입력 |
| 추론 배합비 신뢰도 | low 62% | EVAS BOM으로 calibration |

### 추론 배합비 모델 개선

EVAS 70개 제품의 **정확한 배합비**를 가지고 있으므로:

1. 같은 70개 제품의 전성분 순서만으로 배합비를 추론
2. 실제 배합비와 비교 → 모델 오차 측정
3. 오차 패턴 학습 → 나머지 34,000개 제품에 적용
4. **시장 전체의 배합비 추론 정확도 향상**

이건 EVAS만의 독점 자산이 됨.

---

*EVAS Cosmetic — Formulation Intelligence System v2*  
*2026-03-10*
