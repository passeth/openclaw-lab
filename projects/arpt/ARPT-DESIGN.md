# 🔬 ARPT — Auto Research Product Tournament

## 설계 문서 v1.3 | EVAS LAB

> **영감:** Karpathy의 autoresearch — "평가 지표 + 자동 반복 = 최적값 발견"  
> **적용:** 화장품 R&D 제품 조사 자동화 파이프라인

---

## 1. 개요

### 목적
특정 성분/주제 기준으로 관련 제품 50개를 자동 수집 → 다중 지표 스코어링 → 토너먼트 → 상위 챔피언 기반 신제품 기획서 생성

### 운영 방식
| 항목 | 설명 |
|------|------|
| **트리거** | 사용자가 주제 지정 (예: "PDRN 앰플", "비건 선크림") |
| **Daily PI와 관계** | 독립 운영. Daily PI = 매일 영감, ARPT = 온디맨드 기획 |
| **소요 시간** | 에이전트 병렬 가동 시 약 30분~1시간 (목표) |
| **출력** | GitHub Gist (공개) + Slack #C0AHPSNJJH5 채널 전송 |

---

## 2. 도구 인벤토리

### 검증 완료 ✅

| 도구 | 역할 | 검증 결과 |
|------|------|----------|
| **Scrapling** (v0.4.2) | 웹 스크래핑 프레임워크 | ✅ 설치 완료 (`projects/arpt/.venv`) |
| **Scrapling `fetch`** | 브라우저 기반 동적 페이지 수집 | ✅ 올리브영 랭킹/상세, 화해 검색 성공 |
| **Scrapling `get`** | HTTP 기반 정적 페이지 수집 | ✅ INCIDecoder 전성분, 아마존 검색, YesStyle 검색 |
| **Scrapling `stealthy-fetch`** | 안티봇 우회 | ⚠️ 화해 상세 차단 (불필요 — JSON 대안 발견) |
| **ClawHub scrapling-official** | Scrapling 공식 스킬 | ✅ 설치 완료 |
| **xAI Grok** | 웹 검색 + 종합 분석 | ✅ Daily PI에서 검증 완료 (Responses API) |
| **Kimi 2.5** | 심층 분석 + 평가 | ✅ AutoResearch에서 검증 완료 |
| **InfraNodus** | 텍스트 네트워크 + 구조적 갭 | ✅ Daily PI에서 검증 완료 |
| **GitHub Gist** | 산출물 발행 | ✅ `gh` CLI 검증 완료 |
| **Slack** | 팀 전달 | ✅ message 도구 검증 완료 |

### 구축 완료 ✅ (v1.3)

| 도구 | 역할 | 상태 |
|------|------|------|
| **Supabase** (Pro Plan) | 전체 데이터 영구 저장 | ✅ 5 ARPT 테이블 + `incidecoder_products` 34,774건 활용 |
| **InfraNodus API** | 텍스트 네트워크 Gap 분석 | ✅ API 키 연동, 150 nodes / 6 communities 확인 |
| **xAI Grok 비동기** | 제품 분석 + Gap 보강 | ✅ asyncio+aiohttp, 10/10 성공, 배치 5개씩 |
| **INCIDecoder 전성분** | DB 우선 → 크롤링 fallback | ✅ Supabase 34K DB → INCIDecoder scrape 2단계 |
| **서브에이전트 병렬** | 속도 확보 | ✅ 5개×배치 동시 처리 |
| **2종 리포트 생성** | 처방 제안서 + 상품 기획 제안서 | ✅ Grok 자동 생성 → Gist 발행 |

### 향후 연동 예정 🔧

| 도구 | 역할 | 상태 |
|------|------|------|
| **CosDNA 스킬** | 성분 안전성 스코어 | 🔧 스킬 있음, 스코어링 연동 예정 |
| **CosIng 스킬** | EU 규제 상태 | 🔧 스킬 있음, 규제 체크 연동 예정 |
| **CIR 스킬** | 임상 안전성 | 🔧 스킬 있음, 효능 근거 연동 예정 |
| **PubMed** | 논문 검색 | 🔧 미검증 |

---

## 3. 데이터 소스 검증 결과

### 3.1 사이트별 Fetcher 매핑

| 사이트 | Fetcher | 검증 상태 | 수집 데이터 |
|--------|---------|----------|------------|
| **화해 검색** | `fetch` | ✅ 검증 완료 | 제품명, 브랜드, 평점, 리뷰수, 가격, 용량 |
| **화해 상세** | — | ⛔ 403 차단 | `__NEXT_DATA__` JSON으로 대체 |
| **INCIDecoder** | `get` | ✅ 검증 완료 | 전성분, 효능 분류, 안전성 |
| **올리브영 랭킹** | `fetch` | ✅ 검증 완료 | 제품명, 브랜드, 가격, 이미지, URL |
| **올리브영 상세** | `fetch` | ✅ 검증 완료 | 가격, 평점, 리뷰수, 배송 정보 |
| **아마존 검색** | `get` | ✅ 검증 완료 (2026-03-10) | 제품명, 평점, 리뷰수, 가격(KRW), 브랜드 |
| **YesStyle 검색** | `get` | ✅ 검증 완료 (2026-03-10) | 제품명, 브랜드, 랭킹, 이미지 |
| **Sephora** | get/fetch/stealthy 전부 | ⛔ Akamai 완전 차단 | xAI Grok 간접 수집으로 대체 |
| **PubMed** | `get` | 🔧 미검증 | 핵심 성분 관련 논문 |

### 3.2 화해 `__NEXT_DATA__` JSON (핵심 발견 ✅)

화해 검색 페이지(`/search?query=KEYWORD`)를 Scrapling `fetch`로 수집하면,  
HTML 내 `<script id="__NEXT_DATA__">` 태그에 **구조화된 JSON**이 포함됨.

**별도 상세 페이지 크롤링 불필요** — 검색 결과에 이미 제품 상세 정보 포함.

```json
{
  "goods_seq": 69360,
  "name": "[only화해] 피디알엔 캡슐 100 세럼 50ml 대용량 기획",
  "discount_rate": 59,
  "price": 24500,
  "ranking": 5,
  "ranking_change": 8,
  "product": {
    "id": 2113285,
    "name": "PDRN 히알루론산 캡슐 100 세럼",
    "review_count": 10656,
    "review_rating": 4.61,
    "price": 39000,
    "package_info": "30 mL / 1.01 fl.oz."
  },
  "brand": {
    "id": 7890,
    "alias": "Anua",
    "full_name": "아누아 (Anua)"
  }
}
```

### 3.3 아마존 검색 (2026-03-10 검증 ✅)

`scrapling extract get` (HTTP, `--impersonate chrome`)로 검색 결과 직접 수집.

- URL: `https://www.amazon.com/s?k=PDRN+serum`
- 응답: **614개 결과**, HTML 마크다운으로 파싱 완료
- 수집 가능 필드:
  - 제품명 (전체 타이틀)
  - 평점 (예: 4.6/5.0)
  - 리뷰 수 (예: 27.1K)
  - 가격 (KRW 자동 변환됨 — 한국 IP 기준)
  - 브랜드명
  - 제품 이미지 URL
  - ASIN (URL에서 추출 가능)
  - Sponsored vs Organic 구분 가능

검증 시 발견된 제품 예시:
| 제품 | 평점 | 리뷰수 | 가격 |
|------|------|--------|------|
| VT COSMETICS PDRN Cica Exosome Ampoule | 4.6 | 256 | ₩32,710 |
| Anua PDRN Hyaluronic Acid Capsule 100 Serum | 4.6 | 838 | ₩40,694 |
| Dr. Reju-All PDRN Rejuvenating Cream | 4.5 | 704 | ₩74,341 |
| Lollsea PDRN Serum 99% Purity | 5.0 | 15 | ₩39,995 |
| VT COSMETICS PDRN 100 Essence | 4.6 | 1,700 | ₩41,631 |
| SeoulCeuticals PDRN Serum + Vitamin C | 4.3 | 27,100 | — |

### 3.4 YesStyle 검색 (2026-03-10 검증 ✅)

`scrapling extract get` (HTTP, `--impersonate chrome`)로 검색 결과 수집.

- URL: `https://www.yesstyle.com/en/beauty-face-serums/list.html/bcc.15556_bpt.46?q=PDRN`
- 수집 가능: 제품명, 브랜드, 랭킹 순서, 이미지
- K-뷰티 글로벌 판매 데이터 확보 (Sephora 대체)

랭킹 결과:
1. medicube - PDRN Pink Peptide Serum
2. Anua - PDRN Hyaluronic Acid Capsule 100 Serum
3. VT - PDRN Essence 100
4. medicube - PDRN Pink Peptide Serum Bundle Set

### 3.5 Sephora (차단됨 ⛔)

- `get` / `fetch` / `stealthy-fetch` 모두 **Akamai WAF 완전 차단**
- 응답: Akamai 보호 페이지만 반환 (4줄)
- **대안:** xAI Grok 웹 검색으로 Sephora 제품 데이터 간접 수집

---

## 4. 데이터 수집 전략 (v1.1 확정)

### 기존 (문제)
```
올리브영에서 제품 찾고 → 성분 매칭 시도 (역방향, 매칭률 낮음)
```

### 수정 (확정)
```
1차: 화해 검색 (Scrapling fetch)   → 성분 기준 K-뷰티 제품 목록 + 상세 JSON
2차: 아마존 검색 (Scrapling get)   → 글로벌 제품 목록 + 평점/리뷰/가격
3차: YesStyle 검색 (Scrapling get) → K-뷰티 글로벌 판매 랭킹 교차 검증
4차: INCIDecoder (Scrapling get)   → 전성분 보완 (글로벌 제품)
5차: xAI Grok (Responses API)      → Sephora 간접 + 트렌드/리뷰/논문 검색
6차: 올리브영 (Scrapling fetch)    → 한국 내 가격/랭킹 교차 검증 (보조)
```

### 소스별 역할 매트릭스

| 소스 | K-뷰티 | 글로벌 | 가격 | 평점/리뷰 | 성분 | 트렌드 |
|------|--------|--------|------|----------|------|--------|
| **화해** | ★★★ | — | ★★ | ★★★ | ★ | ★ |
| **아마존** | ★★ | ★★★ | ★★★ | ★★★ | — | ★★ |
| **YesStyle** | ★★★ | ★ | ★★ | ★ | — | ★★ |
| **INCIDecoder** | ★ | ★★★ | — | — | ★★★ | — |
| **xAI Grok** | ★★ | ★★ | ★ | ★ | ★★ | ★★★ |
| **올리브영** | ★★★ | — | ★★★ | ★★ | — | ★★ |

---

## 5. 세션 기반 데이터 추적 (Traceability)

### 세션 ID 구조

각 ARPT 실행은 하나의 **세션(session)**으로 관리됨.  
모든 중간 데이터는 `session_id`로 연결되어, 최종 Gist 리포트의 모든 수치를 원본 데이터까지 역추적 가능.

```
arpt_sessions (마스터 테이블)
│
├── session_id: UUID ← 모든 하위 테이블의 FK
├── topic: "PDRN 앰플"
├── keywords: ["PDRN", "폴리디옥시리보뉴클레오타이드", "연어DNA", ...]
├── preset: "trend" / "stable" / "innovation"
├── product_count: 50
├── started_at / completed_at
├── gist_url: 발행된 Gist URL
├── status: running / scoring / tournament / completed / failed
│
├── arpt_products      ← session_id FK (50개 제품 원본)
├── arpt_scores        ← product_id FK (각 제품별 점수 + 근거)
├── arpt_rounds        ← session_id FK (토너먼트 진행 기록)
└── arpt_gaps          ← session_id FK (구조적 공백 발견)
```

### 추적 시나리오

**"저번에 PDRN으로 돌린 결과 다시 봐줘"**
```sql
SELECT * FROM arpt_sessions WHERE topic ILIKE '%PDRN%' ORDER BY started_at DESC;
```

**"챔피언 1위 제품의 성분 효능 점수 근거가 뭐였지?"**
```sql
SELECT s.efficacy_score, s.efficacy_evidence
FROM arpt_scores s
JOIN arpt_products p ON s.product_id = p.id
JOIN arpt_rounds r ON r.product_id = p.id
WHERE r.session_id = '{session_id}' AND r.round_number = 3 AND r.advanced = true
ORDER BY r.round_score DESC LIMIT 1;
```

**"Gist에 나온 가격 데이터 원본 확인"**
```sql
SELECT product_name, price, raw_data->'original_price', source_platform, scraped_at
FROM arpt_products WHERE session_id = '{session_id}';
```

---

## 6. Supabase 스키마 (v1.1)

```sql
-- 세션 마스터 테이블
CREATE TABLE arpt_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  keywords TEXT[],
  preset TEXT DEFAULT 'default',    -- default / trend / stable / innovation
  product_count INTEGER DEFAULT 50,
  status TEXT DEFAULT 'scouting',   -- scouting / scoring / tournament / reporting / completed / failed
  config JSONB,                      -- 실행 시 설정 (가중치, 소스 목록 등)
  gist_url TEXT,
  gist_id TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  error_log JSONB
);

-- 제품 원본 데이터
CREATE TABLE arpt_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  product_name TEXT NOT NULL,
  brand TEXT,
  brand_tier TEXT,           -- k-beauty / global / indie / luxury-derma
  price NUMERIC,
  discount_price NUMERIC,
  discount_rate NUMERIC,
  currency TEXT DEFAULT 'KRW',
  volume TEXT,
  review_count INTEGER,
  review_rating NUMERIC,
  full_ingredients TEXT,
  source_url TEXT,
  source_platform TEXT,      -- hwahae / amazon / yesstyle / incidecoder / oliveyoung / grok
  image_url TEXT,
  external_id TEXT,          -- 화해 product_id / ASIN / YesStyle pid 등
  raw_data JSONB,            -- 원본 데이터 전부 보존
  scraped_at TIMESTAMPTZ DEFAULT now()
);

-- 스코어링 결과
CREATE TABLE arpt_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES arpt_products(id) ON DELETE CASCADE,
  
  -- 기본 지표 (각 0-100)
  efficacy_score NUMERIC,
  efficacy_evidence JSONB,
  formulation_score NUMERIC,
  formulation_notes JSONB,
  consumer_score NUMERIC,
  consumer_raw JSONB,
  value_score NUMERIC,
  value_calc JSONB,
  differentiation_score NUMERIC,
  diff_evidence JSONB,
  
  -- 최신성 가점 (각 항목별)
  search_momentum NUMERIC,     -- 검색 모멘텀 (+15 max)
  paper_trend NUMERIC,         -- 논문 트렌드 (+10 max)
  sns_buzz NUMERIC,            -- SNS 버즈 가속도 (+10 max)
  launch_freshness NUMERIC,    -- 출시 신선도 (+10 max)
  ingredient_trend NUMERIC,    -- 트렌드 성분 (+5 max)
  freshness_total NUMERIC,     -- 최신성 합계 (+50 max)
  
  -- 올드패션 감점
  review_staleness NUMERIC,    -- 리뷰 노후화 (-10 max)
  ingredient_staleness NUMERIC,-- 성분 진부도 (-10 max)
  no_renewal NUMERIC,          -- 리뉴얼 부재 (-5 max)
  staleness_total NUMERIC,     -- 감점 합계 (-25 max)
  
  -- 최종
  base_weighted NUMERIC,       -- 기본 지표 가중 합계
  final_score NUMERIC,         -- base + freshness - staleness
  preset_used TEXT,
  scored_at TIMESTAMPTZ DEFAULT now()
);

-- 토너먼트 라운드 기록
CREATE TABLE arpt_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  round_number INT NOT NULL,   -- 1: 50→20, 2: 20→10, 3: 10→5
  product_id UUID NOT NULL REFERENCES arpt_products(id) ON DELETE CASCADE,
  round_score NUMERIC,
  rank_in_round INT,
  analysis JSONB,              -- Kimi/InfraNodus 분석 결과
  advanced BOOLEAN DEFAULT false,
  eliminated_reason TEXT,
  evaluated_at TIMESTAMPTZ DEFAULT now()
);

-- 구조적 공백 (기회 영역)
CREATE TABLE arpt_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  gap_type TEXT,               -- ingredient_combo / claim / price_tier / formulation / target_skin
  gap_description TEXT NOT NULL,
  opportunity_score NUMERIC,   -- 0-100
  evidence JSONB,
  infranodus_data JSONB,
  related_products UUID[],     -- 관련 제품들
  discovered_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_products_session ON arpt_products(session_id);
CREATE INDEX idx_scores_product ON arpt_scores(product_id);
CREATE INDEX idx_rounds_session ON arpt_rounds(session_id);
CREATE INDEX idx_rounds_product ON arpt_rounds(product_id);
CREATE INDEX idx_gaps_session ON arpt_gaps(session_id);
CREATE INDEX idx_sessions_topic ON arpt_sessions(topic);
CREATE INDEX idx_sessions_status ON arpt_sessions(status);
```

---

## 7. Phase별 아키텍처

### Phase 1 — 제품 수집 (Product Scouting)

```
사용자: "PDRN 앰플"
        ↓
[1] arpt_sessions 생성 (session_id 발급, status='scouting')
        ↓
[2] xAI Grok → 키워드 확장
    "PDRN" → ["PDRN", "폴리디옥시리보뉴클레오타이드", "연어DNA", "Salmon DNA", ...]
        ↓
[3] 병렬 수집 (서브에이전트)
    ┌─ 화해 검색 (Scrapling fetch) → K-뷰티 25개
    ├─ 아마존 검색 (Scrapling get) → 글로벌 15개
    ├─ YesStyle 검색 (Scrapling get) → 인디/교차 검증
    └─ xAI Grok → Sephora 간접 + 추가 발굴
        ↓
[4] 중복 제거 + 카테고리 분배
    K-뷰티 25 / 글로벌 15 / 인디 7 / 럭셔리·더마 3
        ↓
[5] arpt_products 저장 (50개, raw_data JSONB 포함)
        ↓
[6] 성분 보완 수집
    ┌─ INCIDecoder (글로벌 제품)
    └─ 화해 __NEXT_DATA__ (K-뷰티)
        ↓
[7] status → 'scoring'
```

### Phase 2 — 스코어링 매트릭스

**스코어링 파이프라인 (파일럿 개선 반영):**

```
[1] 전성분 수집 (DB 우선 전략)
    ├─ 1순위: Supabase incidecoder_products (34,774건!) → 크롤링 없이 즉시
    ├─ 2순위: 화해 __NEXT_DATA__ (K-뷰티)
    ├─ 3순위: INCIDecoder 크롤링 fallback (Scrapling get)
    └─ arpt_products.full_ingredients 업데이트
         ↓
[2] xAI Grok 비동기 분석 (개선 #1)
    ├─ 제품당 1회 호출 (배치, 타임아웃 120초)
    ├─ 검색 모멘텀 / SNS 버즈 / 출시일 / 트렌드 데이터 수집
    └─ 실패 시 룰 기반 fallback (파일럿 방식)
         ↓
[3] 전성분 기반 정밀 스코어링 (개선 #2)
    ├─ CIR 스킬: 핵심 성분 안전성 → efficacy_evidence
    ├─ CosDNA 스킬: 자극도/여드름 유발성 → formulation_notes
    ├─ CosIng 스킬: EU 규제 상태 → regulatory check
    └─ Supabase incidecoder_ingredients JOIN → 성분 프로파일 교차
         ↓
[4] 서브에이전트 병렬 처리 (개선 #4)
    ├─ 5개 제품씩 배치 → 서브에이전트 10개 병렬
    └─ 각 서브에이전트: Grok 호출 + 스코어링 + Supabase 저장
```

**기본 지표 (Base Metrics) — 각 0~100점:**

| 지표 | 가중치 (default) | 담당 도구 | 아웃풋 |
|------|--------|----------|--------|
| **성분 효능 지수** | 0.30 | xAI Grok + CIR + 전성분 분석 | 효능 점수 + 근거 요약 |
| **처방 완성도** | 0.20 | CosDNA + CosIng + 전성분 분석 | 처방 점수 + 위험 요소 |
| **소비자 만족도** | 0.20 | 화해 + 아마존 데이터 | 평점 × log(리뷰수) + 감성 |
| **가성비** | 0.15 | 계산 | 활성 성분 추정 함량 ÷ mL당 가격 |
| **차별화도** | 0.15 | xAI Grok + Kimi 2.5 | 독자 원료/특허/고유 제형 |

**🔥 최신성 가점 (Freshness Bonus) — 최대 +50:**

| 가점 항목 | 측정 방법 | 가점 |
|-----------|----------|------|
| 검색 모멘텀 | 최근 3개월 검색량 ÷ 12개월 평균 → 상승률 | +15 |
| 논문 발행 트렌드 | 핵심 성분 최근 1년 논문 수 ÷ 3년 평균 | +10 |
| SNS 버즈 가속도 | 최근 30일 언급량 ÷ 90일 평균 | +10 |
| 출시 신선도 | 출시 2년 이내 +5, 1년 이내 +10 | +10 |
| 트렌드 성분 일치 | 올해 떠오르는 성분 포함 여부 | +5 |

**올드패션 감점 (Staleness Penalty) — 최대 -25:**

| 감점 항목 | 조건 | 감점 |
|-----------|------|------|
| 리뷰 노후화 | 최근 6개월 신규 리뷰 비율 < 10% | -10 |
| 성분 진부도 | 모든 활성 성분이 10년+ 범용 원료만 | -10 |
| 리뉴얼 부재 | 3년 이상 처방 변경 없음 (추정) | -5 |

**최종 점수 산출:**
```
최종 점수 = Σ(기본 지표 × 가중치) + 최신성 가점 - 올드패션 감점
```

**주제별 프리셋:**

| 프리셋 | 설명 | 조정 |
|--------|------|------|
| 🔍 **trend** | 트렌드 탐색 | 최신성 ×1.5, 소비자 만족도 ↓ |
| 🛡️ **stable** | 안정적 기획 | 소비자 만족도 ×1.3, 최신성 ×0.7 |
| 🔬 **innovation** | 기술 혁신 | 차별화도 ×1.5, 가성비 ↓ |
| ⚖️ **default** | 기본 균형 | 원래 가중치 그대로 |

### Phase 3 — 토너먼트 실행

```
50개 스코어링 완료 → status='tournament'
        ↓
Round 1 (50→20): final_score 순위 컷 (Supabase 쿼리)
        ↓
Round 2 (20→10): Kimi 2.5 심층 분석
  - 성분 시너지/충돌 정밀 분석
  - 실제 리뷰 텍스트 감성 분석
  - 특허/논문 교차 검증
        ↓
Round 3 (10→5): InfraNodus 자동 네트워크 분석 (개선 #3)
  - 상위 10개의 전성분 + 리뷰 키워드 + 마케팅 클레임 → 텍스트 수집
  - InfraNodus API 자동 호출:
    ├─ POST /api/v1/entries: 텍스트 추가
    ├─ GET /api/v1/analytics: 토픽 클러스터 + 연결 구조
    └─ GET /api/v1/gaps: 구조적 공백 자동 추출
  - "이 10개가 공통으로 안 하는 것" = 구조적 공백 = R&D 기회
  - infranodus_data → arpt_gaps.infranodus_data (JSONB 영구 보존)
        ↓
🏆 챔피언 5개 + 📊 arpt_gaps 저장
        ↓
status → 'reporting'
```

### Phase 4 — 리포트 자동 생성 (2종)

ARPT는 **2종의 독립 리포트**를 자동 생성하여 각각 Gist 발행:

#### 📋 Report A: 처방 제안서 (R&D 연구원용)

> **대상:** 제형 연구원, 처방 개발자  
> **목적:** 챔피언 제품의 처방 분석 → 신제품 처방 설계 근거 제공

```
1. 핵심 성분 분석
   - 챔피언 5개 전성분 비교표
   - INCI 기준 성분 빈도 히트맵 (공통 성분 vs 차별 성분)
   - 활성 성분별 추정 함량 범위 (INCIDecoder + composition_inferred 데이터)
   - CIR/CosDNA 안전성 프로파일

2. 처방 패턴 분석
   - 공통 베이스 구조 (유화제, 증점제, 보존제 패턴)
   - 성분 시너지 맵 (상호 강화 조합)
   - 성분 충돌 경고 (pH 불일치, 안정성 리스크)
   - 처방 완성도 상위 3개 심층 해부

3. 구조적 공백 → 처방 기회
   - Gap별 추천 성분 조합 (구체적 INCI명)
   - 예상 안정성 이슈 및 해결 방향
   - 참고 논문/특허 (PubMed + Grok 검색)

4. 신처방 제안 (3안)
   - Safe bet: 검증된 성분 조합 + 개선점
   - Trend rider: 트렌드 성분 투입
   - Blue ocean: 미탐색 조합
   - 각 안별: 추천 전성분 초안, 예상 pH, 제형 타입, 안정성 유의사항

5. 원료 소싱 참고
   - 핵심 원료 공급사 정보 (가능 시)
   - 원가 추정 범위
```

#### 📊 Report B: 상품 기획 제안서 (상품기획자용)

> **대상:** 상품 기획자, 마케팅, 영업  
> **목적:** 시장 기회 분석 → 신제품 포지셔닝 + 상품 기획 의사결정 근거

```
1. 시장 경쟁 구도
   - 50개 전체 순위표 (점수 + 주요 지표)
   - 브랜드 티어별 분포 (K-뷰티/글로벌/인디/럭셔리)
   - 가격대별 분포 (저가/중가/고가/프리미엄)
   - 포지셔닝 맵 (가격 × 소비자만족도 2D)

2. 챔피언 5개 프로필
   - 제품 사진 + 기본 정보
   - 강점/약점 요약 (스코어링 근거 기반)
   - 소비자 리뷰 핵심 키워드 (긍정/부정)
   - 글로벌 vs 국내 가격 비교

3. 트렌드 & 소비자 인사이트
   - 검색 모멘텀 / SNS 버즈 데이터
   - 최신성 가점 상위 제품의 공통점
   - 소비자가 가장 많이 언급하는 효능 키워드
   - InfraNodus 네트워크 시각화 (있으면)

4. 기회 영역 (Gap → 상품 컨셉)
   - Gap별 타깃 고객 프로파일
   - 예상 가격대 + 채널 전략
   - 경쟁 강도 평가 (이 Gap을 공략할 경쟁자 유무)

5. 신상품 기획안 (3안)
   - Safe bet / Trend rider / Blue ocean
   - 각 안별: 상품명 제안, 가격대, 타깃, 채널, 패키지 컨셉, USP
   - 예상 포지셔닝 (기존 챔피언 대비 위치)
   - Go/No-Go 판단 체크리스트

6. 실행 로드맵
   - 처방 개발 → 시제품 → 인허가 → 양산 타임라인 (대략)
   - 필요 투자/리소스 개요
```

**발행 & 기록:**
```
Kimi 2.5 (Report A: 처방 제안서 작성)
  → Gist A 발행
Kimi 2.5 (Report B: 상품 기획 제안서 작성)
  → Gist B 발행
  → arpt_sessions.gist_url 업데이트 (JSON: {report_a, report_b})
  → Slack #C0AHPSNJJH5 (요약 + 양쪽 링크)
  → Telegram passeth (핵심 인사이트 + 링크)
  → status='completed', completed_at=now()
```

---

## 8. 데이터 보존 정책

```
수집 원본 (raw_data)     → Supabase arpt_products.raw_data (JSONB, 영구 보존)
스코어링 근거 (evidence) → Supabase arpt_scores.*_evidence (JSONB, 영구 보존)
InfraNodus 결과          → Supabase arpt_gaps.infranodus_data (JSONB, 영구 보존)
토너먼트 분석            → Supabase arpt_rounds.analysis (JSONB, 영구 보존)
최종 기획서              → Gist + Supabase gist_url + 로컬 파일
```

**원칙: 어떤 단계에서도 데이터를 버리지 않는다.**  
최종 산출물만 보는 건 Gist, 근거 추적은 Supabase.

---

## 9. 실행 아키텍처

```
사용자: "PDRN 앰플로 ARPT 실행해줘"
              ↓
    ┌──────────────────────────┐
    │  메인 에이전트            │  ← 오케스트레이션 + 상태 관리
    │  (arpt_sessions 생성)    │
    └─────────┬────────────────┘
              │
    ┌─────────┼──────────────────────────────┐
    ↓         ↓              ↓               ↓
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│Scout-1 │ │Scout-2 │ │Scout-3   │ │Scout-4   │
│화해    │ │아마존  │ │YesStyle  │ │xAI Grok  │
└────┬───┘ └────┬───┘ └────┬─────┘ └────┬─────┘
     └──────────┴──────────┴─────────────┘
                    ↓
          arpt_products 저장 (50개)
                    ↓
         ┌────────────────┐
         │  Scorer Agent  │  ← Kimi 2.5 + CIR + CosDNA
         │  (병렬 5개씩)  │
         └────────┬───────┘
                  ↓
          arpt_scores 저장
                  ↓
         ┌────────────────┐
         │  Tournament    │  ← 3라운드 실행
         │  Agent         │
         └────────┬───────┘
                  ↓
         ┌──────────────────────────────────┐
         │  Writer Agent                    │
         │  ├─ Report A: 처방 제안서 (R&D)  │
         │  └─ Report B: 상품 기획 제안서    │
         │  → Gist 2건 발행                 │
         │  → Slack + Telegram 전송         │
         └──────────────────────────────────┘
```

---

## 10. 기술 환경

| 항목 | 값 |
|------|-----|
| **ARPT 프로젝트** | `/Users/evasfac/.openclaw/workspace/projects/arpt/` |
| **파이프라인 코드** | `projects/arpt/pipeline/` (Python 모듈) |
| **Scrapling venv** | `projects/arpt/.venv` |
| **Scrapling 버전** | 0.4.2 (all extras + Playwright browsers) |
| **Python** | 3.14.2 |
| **Supabase** | Pro Plan, ref: `ejbbdtjoqapheqieoohs` |
| **InfraNodus** | API 연동 완료 |
| **Gist 계정** | `epicevas-lgtm` |
| **Slack 채널** | `#C0AHPSNJJH5` |
| **xAI 모델** | `grok-4-1-fast-reasoning` (Responses API) |

### 파이프라인 코드 구조

```
projects/arpt/
├── pipeline/
│   ├── __init__.py
│   ├── __main__.py        # CLI 엔트리포인트
│   ├── config.py          # 설정, API 키, 가중치 프리셋
│   ├── ingredients.py     # 전성분 수집 (DB→화해→INCIDecoder)
│   ├── grok_async.py      # xAI Grok 비동기 분석 (asyncio+aiohttp)
│   ├── scorer.py          # 통합 스코어링 엔진 (5지표 + 가점/감점)
│   ├── tournament.py      # 토너먼트 엔진 (N→컷오프)
│   ├── infranodus.py      # InfraNodus API + LLM fallback Gap 분석
│   └── report.py          # 2종 리포트 생성 (처방/상품기획)
├── pilot-results/         # 파일럿 산출물
│   ├── PDRN-ampoule-pilot.md
│   ├── PDRN-앰플-처방제안서.md
│   └── PDRN-앰플-상품기획제안서.md
├── supabase-init.sql      # DB 스키마
├── .env                   # API 키 (Supabase, InfraNodus)
└── HANDOFF.md             # 웹사이트 개발 핸드오프 문서
```

### 실행 방법

```bash
cd projects/arpt && source .venv/bin/activate

# 전체 파이프라인 (전성분→스코어링→토너먼트→Gap→리포트)
python -m pipeline.run --session-id <uuid>

# 개별 단계
python -m pipeline.run --session-id <uuid> --phase ingredients
python -m pipeline.run --session-id <uuid> --phase scoring --preset trend
python -m pipeline.run --session-id <uuid> --phases scoring,tournament,gaps,reports
```

---

## 11. 파일럿 결과 (PDRN 앰플 × 10개)

### Gist 발행물

| 문서 | URL |
|------|-----|
| 📋 처방 제안서 (R&D용) | https://gist.github.com/epicevas-lgtm/90317efca53ecfbc80f69fb7e2e26b51 |
| 📊 상품 기획 제안서 (기획자용) | https://gist.github.com/epicevas-lgtm/13e505eb162d26fa8998df5718b4f7b6 |
| 🏆 파일럿 토너먼트 결과 | https://gist.github.com/epicevas-lgtm/ab24635d1da1c7c5f7fce4c8de5df8c7 |
| 📐 웹사이트 핸드오프 | https://gist.github.com/epicevas-lgtm/26a4d7a1b67647660b3fb802f7bae17d |

### 최종 토너먼트 (Grok 실시간 + 전성분 반영)

| 순위 | 브랜드 | Final | E | F | C | V | D |
|:----:|--------|------:|--:|--:|--:|--:|--:|
| 🥇 | SeoulCeuticals | 128.9 | 85 | 88 | 76 | 67 | 90 |
| 🥈 | medicube | 126.3 | 85 | 90 | 67 | 61 | 82 |
| 🥉 | Anua | 122.6 | 82 | 92 | 74 | 57 | 88 |
| 4 | VT Cosmetics (Essence) | 121.7 | 88 | 87 | 59 | 54 | 80 |
| 5 | VT Cosmetics (Cica) | 113.9 | 75 | 85 | 44 | 64 | 80 |

### 발견된 Gap (11건)
- InfraNodus 네트워크 Gap: 6건 (성분 수준)
- LLM 전략 Gap: 5건 (시장/마케팅 수준)
- 최고 기회: PDRN+레티놀 조합(95점) / 지성피부 타깃(90점) / 크림 포뮬레이션(85점)

### 전성분 수집 현황
- **Supabase DB hit:** 4/10 (Anua, VT×2, medicube)
- **INCIDecoder 크롤링:** 3/10 (Lollsea, Dr.Reju-All, REJURAN)
- **미수집:** 3/10 (Torriden, SeoulCeuticals, iUNIK — DB에 PDRN 라인 없음)

### 시스템 검증 결과
수집 ✅ | Supabase ✅ | 전성분 ✅ | Grok 비동기 ✅ | 스코어링 ✅ | 토너먼트 ✅ | InfraNodus ✅ | Gap분석 ✅ | 2종 리포트 ✅

---

## 12. 다음 단계 (로드맵)

### 완료

| 단계 | 작업 | 상태 |
|------|------|------|
| 1 | Supabase 프로젝트 연결 + 테이블 생성 | ✅ 완료 (evas_intel) |
| 2 | 데이터 소스 검증 (화해/아마존/YesStyle) | ✅ 완료 |
| 3 | 파일럿: "PDRN 앰플" × 10개 미니 토너먼트 | ✅ 완료 |

### 4대 과제 해결 완료 ✅

| # | 개선 항목 | 해결 방법 | 결과 |
|---|----------|----------|------|
| ✅1 | **xAI Grok 비동기** | asyncio+aiohttp, 120초 타임아웃, 룰 기반 fallback | 10/10 성공, 배치 5개씩 동시 |
| ✅2 | **전성분 연동** | Supabase DB(34K) 우선 → 화해 → INCIDecoder 크롤링 3단계 | 7/10 수집, DB hit 4건 |
| ✅3 | **InfraNodus 자동 Gap** | API 연동(150 nodes, 6 communities) + LLM 보강 | 6 network gaps + 5 LLM gaps = 11건 |
| ✅4 | **서브에이전트 병렬** | 배치 5개씩 동시 처리, 원커맨드 파이프라인 | `python -m pipeline.run` |
| ✅5 | **2종 리포트** | Grok 자동 생성, 처방 제안서 + 상품 기획 제안서 | Gist 자동 발행 |

### 남은 작업

| 단계 | 작업 | 우선순위 |
|------|------|---------|
| 1 | **50개 본게임 첫 실행** | 🔴 높음 |
| 2 | **모니터링 웹사이트** (다른 에이전트 담당) | 🔴 높음 |
| 3 | CosDNA/CosIng/CIR 스킬 스코어링 연동 | 🟡 중간 |
| 4 | PubMed 논문 수집 검증 | 🟡 중간 |
| 5 | Slack/Telegram 자동 전송 | 🟢 낮음 |

---

## 13. 철학

> "감이 아니라 데이터로 기획한다."
> 
> "50개 중 상위권은 이런 공통점이 있고, 아직 아무도 안 한 조합은 이거다."
>
> — Karpathy의 autoresearch 원리를 화장품 R&D에 적용

**Karpathy:** 700개 설정 실험 → validation loss로 경쟁 → 상위 20개 생존  
**ARPT:** 50개 제품 조사 → 다중 지표로 경쟁 → 상위 5개 기반 기획서

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-03-10 08:45 | 초기 설계 문서 |
| v1.1 | 2026-03-10 09:15 | 아마존/YesStyle 검증 추가, Sephora 차단 확인, 세션 추적 구조, 수집 전략 6단계 확장, Supabase 스키마 v1.1 (arpt_sessions 추가), Phase 1 상세화 |
| v1.2 | 2026-03-10 10:50 | 파일럿 결과 반영, 4대 개선과제 정의, Phase 4 → 2종 리포트, 스코어링 파이프라인 상세화, InfraNodus 자동화, 서브에이전트 병렬 아키텍처 |
| **v1.3** | **2026-03-10 11:50** | **4대 과제 전부 해결 완료.** 파이프라인 코드 구조(`pipeline/` 7개 모듈), Grok 비동기 10/10 성공, Supabase DB 우선 전성분 수집(34K hit), InfraNodus API 실연동(150 nodes/6 communities), 2종 리포트 Gist 발행 완료, 웹사이트 핸드오프 문서 |

---

*EVAS LAB | 2026-03-10 | v1.3*
