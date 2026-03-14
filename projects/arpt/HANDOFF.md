# ARPT 모니터링 웹사이트 — 개발 핸드오프 문서

> **목적:** ARPT(Auto Research Product Tournament)가 Supabase에 저장한 리서치 데이터를 웹에서 열람·검색할 수 있는 대시보드 구축
> **작성일:** 2026-03-10
> **작성자:** ARPT 파이프라인 에이전트

---

## 1. 프로젝트 개요

### ARPT란?
화장품 특정 주제(예: "PDRN 앰플")를 입력하면 자동으로:
1. **Scout** — 50개 경쟁 제품을 수집 (화해, 아마존, YesStyle 등)
2. **Score** — 5개 지표로 멀티스코어링 (효능/처방/소비자/가성비/차별화) + 최신성 가점
3. **Tournament** — 50→20→10→5 토너먼트로 챔피언 선정
4. **Report** — 2종 리포트 자동 발행 (처방 제안서 + 상품 기획 제안서)

### 데이터 흐름
```
사용자 주제 입력 → arpt_sessions 생성
                        ↓
                 arpt_products (50개 제품 원본)
                        ↓
                 arpt_scores (50개 스코어링)
                        ↓
                 arpt_rounds (토너먼트 3라운드)
                        ↓
                 arpt_gaps (구조적 공백/기회)
                        ↓
                 GitHub Gist (최종 리포트 2종)
```

---

## 2. Supabase 연결 정보

| 항목 | 값 |
|------|-----|
| **Project Ref** | `ejbbdtjoqapheqieoohs` |
| **API URL** | `https://ejbbdtjoqapheqieoohs.supabase.co` |
| **anon key** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxMDQ0NDIsImV4cCI6MjA4ODY4MDQ0Mn0.Rqz2HjxPRJeGSzm8c2c8ZErepY9BLA3zdafc939gnig` |
| **Plan** | Pro |

> ⚠️ **웹사이트는 anon key로 read-only 접근.** service_role key는 절대 프론트엔드에 노출하지 말 것.
> RLS policy를 추가해야 anon 접근 가능 (아래 섹션 참고).

---

## 3. 테이블 구조 (5개 테이블)

### 3.1 `arpt_sessions` — 세션 마스터

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | UUID (PK) | 세션 고유 ID | `0c9910f5-77b4-...` |
| `topic` | TEXT | 리서치 주제 | `"PDRN 앰플"` |
| `keywords` | TEXT[] | 확장 키워드 배열 | `["PDRN", "연어DNA", ...]` |
| `preset` | TEXT | 가중치 프리셋 | `"default"` / `"trend"` / `"stable"` / `"innovation"` |
| `product_count` | INTEGER | 수집 제품 수 | `10` (파일럿), `50` (본게임) |
| `status` | TEXT | 파이프라인 진행 상태 | `"scouting"` → `"scoring"` → `"tournament"` → `"completed"` |
| `config` | JSONB | 세션 설정 (소스, 가중치 등) | `{"pilot": true, "sources": ["hwahae","amazon"], "weights": {...}}` |
| `gist_url` | TEXT | 최종 리포트 Gist URL | `"https://gist.github.com/..."` |
| `gist_id` | TEXT | Gist ID | `"ab24635d..."` |
| `started_at` | TIMESTAMPTZ | 시작 시각 | |
| `completed_at` | TIMESTAMPTZ | 완료 시각 | |
| `error_log` | JSONB | 에러 기록 | |

**status 상태 머신:**
```
scouting → scoring → tournament → completed
                                → error (어느 단계에서든)
```

### 3.2 `arpt_products` — 수집 제품 원본

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | UUID (PK) | 제품 고유 ID | |
| `session_id` | UUID (FK → sessions) | 소속 세션 | |
| `product_name` | TEXT | 제품명 | `"아누아 PDRN 히알루론산 캡슐 100 세럼"` |
| `brand` | TEXT | 브랜드 | `"Anua"` |
| `brand_tier` | TEXT | 브랜드 등급 | `"k-beauty"` / `"global"` / `"indie"` / `"luxury-derma"` |
| `price` | NUMERIC | 가격 | `39000` |
| `discount_price` | NUMERIC | 할인가 | `24500` |
| `discount_rate` | NUMERIC | 할인율 (%) | `59` |
| `currency` | TEXT | 통화 | `"KRW"` |
| `volume` | TEXT | 용량 | `"30mL"` |
| `review_count` | INTEGER | 리뷰 수 | `10656` |
| `review_rating` | NUMERIC | 평점 (5.0 만점) | `4.61` |
| `full_ingredients` | TEXT | 전성분 (INCI) | (현재 미수집, 개선 예정) |
| `source_url` | TEXT | 소스 URL | `"https://www.hwahae.co.kr/goods/69360"` |
| `source_platform` | TEXT | 수집 출처 | `"hwahae"` / `"amazon"` / `"yesstyle"` / `"grok"` |
| `image_url` | TEXT | 제품 이미지 URL | |
| `external_id` | TEXT | 출처별 고유 ID | `"hwahae:69360"` / `"asin:B0CRKPZ9PQ"` |
| `raw_data` | JSONB | **원본 데이터 전체** (절대 삭제 안 함) | 소스별 원시 데이터 |
| `scraped_at` | TIMESTAMPTZ | 수집 시각 | |

**brand_tier 분포 목표 (50개 본게임):**
- `k-beauty`: 25개
- `global`: 15개
- `indie`: 7개
- `luxury-derma`: 3개

### 3.3 `arpt_scores` — 스코어링 결과

| 컬럼 | 타입 | 설명 | 범위 |
|------|------|------|------|
| `id` | UUID (PK) | | |
| `product_id` | UUID (FK → products) | 제품 참조 | |
| `efficacy_score` | NUMERIC | 성분 효능 지수 | 0~100 |
| `efficacy_evidence` | JSONB | 효능 근거 | `{"reason": "...", "source": "grok"}` |
| `formulation_score` | NUMERIC | 처방 완성도 | 0~100 |
| `formulation_notes` | JSONB | 처방 분석 | |
| `consumer_score` | NUMERIC | 소비자 만족도 | 0~100 |
| `consumer_raw` | JSONB | 소비자 점수 원본 | `{"rating": 4.61, "review_count": 10656, "formula": "..."}` |
| `value_score` | NUMERIC | 가성비 | 0~100 |
| `value_calc` | JSONB | 가성비 계산 상세 | `{"price_krw": 39000, "volume_ml": 30, "price_per_ml": 1300}` |
| `differentiation_score` | NUMERIC | 차별화도 | 0~100 |
| `diff_evidence` | JSONB | 차별화 근거 | |
| `search_momentum` | NUMERIC | 검색 모멘텀 가점 | 0~15 |
| `paper_trend` | NUMERIC | 논문 트렌드 가점 | 0~10 |
| `sns_buzz` | NUMERIC | SNS 버즈 가점 | 0~10 |
| `launch_freshness` | NUMERIC | 출시 신선도 가점 | 0~10 |
| `ingredient_trend` | NUMERIC | 트렌드 성분 가점 | 0~5 |
| `freshness_total` | NUMERIC | **최신성 가점 합계** | 0~50 |
| `review_staleness` | NUMERIC | 리뷰 노후화 감점 | 0~-10 |
| `ingredient_staleness` | NUMERIC | 성분 진부도 감점 | 0~-10 |
| `no_renewal` | NUMERIC | 리뉴얼 부재 감점 | 0~-5 |
| `staleness_total` | NUMERIC | **올드패션 감점 합계** | 0~-25 |
| `base_weighted` | NUMERIC | 가중 기본 점수 | |
| `final_score` | NUMERIC | **최종 점수** | base + freshness + staleness |
| `preset_used` | TEXT | 적용된 프리셋 | |
| `scored_at` | TIMESTAMPTZ | 스코어링 시각 | |

**점수 산출 공식:**
```
base_weighted = efficacy×0.30 + formulation×0.20 + consumer×0.20 + value×0.15 + differentiation×0.15
final_score = base_weighted + freshness_total + staleness_total
```

### 3.4 `arpt_rounds` — 토너먼트 라운드

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID (PK) | |
| `session_id` | UUID (FK → sessions) | |
| `round_number` | INT | 라운드 번호 (1, 2, 3) |
| `product_id` | UUID (FK → products) | |
| `round_score` | NUMERIC | 해당 라운드 점수 |
| `rank_in_round` | INT | 라운드 내 순위 |
| `analysis` | JSONB | 라운드 분석 상세 |
| `advanced` | BOOLEAN | 다음 라운드 진출 여부 |
| `eliminated_reason` | TEXT | 탈락 사유 |
| `evaluated_at` | TIMESTAMPTZ | |

**토너먼트 구조 (50개 본게임):**
```
Round 1: 50 → 20 (점수 순위 컷)
Round 2: 20 → 10 (심층 분석)
Round 3: 10 → 5  (네트워크 분석)
```

### 3.5 `arpt_gaps` — 구조적 공백 (기회 영역)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID (PK) | |
| `session_id` | UUID (FK → sessions) | |
| `gap_type` | TEXT | 공백 유형 | 
| `gap_description` | TEXT | 공백 설명 (한글) |
| `opportunity_score` | NUMERIC | 기회 점수 (0~100) |
| `evidence` | JSONB | 근거 데이터 |
| `infranodus_data` | JSONB | InfraNodus 네트워크 분석 결과 (향후) |
| `related_products` | UUID[] | 관련 제품 ID 배열 |
| `discovered_at` | TIMESTAMPTZ | |

**gap_type 값들:**
- `ingredient_combo` — 미탐색 성분 조합
- `price_tier` — 가격대 공백
- `target_skin` — 타깃 피부 타입 공백
- `formulation` — 제형 공백
- `claim` — 클레임/마케팅 공백

---

## 4. 테이블 관계 (ERD)

```
arpt_sessions (1)
  ├──< arpt_products (N)     -- session_id FK
  │       └──< arpt_scores (N)  -- product_id FK
  ├──< arpt_rounds (N)       -- session_id FK + product_id FK
  └──< arpt_gaps (N)         -- session_id FK
```

**핵심 JOIN 패턴:**
```sql
-- 세션별 전체 결과 (제품 + 점수)
SELECT p.*, s.*
FROM arpt_products p
JOIN arpt_scores s ON s.product_id = p.id
WHERE p.session_id = '<session_id>'
ORDER BY s.final_score DESC;

-- 세션별 토너먼트 결과
SELECT r.*, p.product_name, p.brand
FROM arpt_rounds r
JOIN arpt_products p ON r.product_id = p.id
WHERE r.session_id = '<session_id>'
ORDER BY r.round_number, r.rank_in_round;

-- 세션별 Gap 분석
SELECT * FROM arpt_gaps
WHERE session_id = '<session_id>'
ORDER BY opportunity_score DESC;
```

---

## 5. RLS Policy (웹사이트 접근용)

현재 RLS가 활성화되어 있지만 policy가 없어서 anon key로 읽기 불가능. 
웹사이트 구축 전에 아래 SQL을 Supabase SQL Editor에서 실행:

```sql
-- 모든 ARPT 테이블에 read-only 접근 허용
CREATE POLICY "Allow public read on arpt_sessions"
  ON arpt_sessions FOR SELECT USING (true);

CREATE POLICY "Allow public read on arpt_products"
  ON arpt_products FOR SELECT USING (true);

CREATE POLICY "Allow public read on arpt_scores"
  ON arpt_scores FOR SELECT USING (true);

CREATE POLICY "Allow public read on arpt_rounds"
  ON arpt_rounds FOR SELECT USING (true);

CREATE POLICY "Allow public read on arpt_gaps"
  ON arpt_gaps FOR SELECT USING (true);
```

> 💡 쓰기는 service_role (파이프라인 에이전트) 전용. 웹에서는 읽기만.

---

## 6. 웹사이트 추천 페이지 구조

### 6.1 세션 목록 (메인 페이지)
```
/sessions
├── 세션 카드 리스트
│   ├── 주제명 (topic)
│   ├── 상태 배지 (status: scouting/scoring/tournament/completed)
│   ├── 제품 수 (product_count)
│   ├── 프리셋 (preset)
│   ├── 시작/완료 시간
│   └── Gist 링크 (있으면)
└── 검색/필터: 주제, 상태, 날짜
```

### 6.2 세션 상세 — 대시보드 뷰
```
/sessions/:id
├── 🏆 토너먼트 결과
│   ├── 순위표 (전체 제품 final_score 기준)
│   ├── 레이더 차트 (상위 5개 지표 비교)
│   └── 라운드별 진출/탈락 시각화
│
├── 📊 스코어링 상세
│   ├── 5개 지표 바 차트 (제품별 비교)
│   ├── 최신성 가점 / 올드패션 감점 시각화
│   └── 프리셋 가중치 표시
│
├── 📐 Gap 분석
│   ├── Gap 카드 (유형 + 기회점수 + 설명)
│   └── 기회 영역 버블 차트
│
└── 📋 리포트 링크
    ├── Report A: 처방 제안서 (Gist)
    └── Report B: 상품 기획 제안서 (Gist)
```

### 6.3 제품 상세
```
/products/:id
├── 기본 정보 (이름, 브랜드, 가격, 용량, 평점)
├── 스코어 카드 (5개 지표 + 가점/감점)
├── 소스 링크 (화해, 아마존 등)
├── 전성분 (있으면)
└── raw_data 펼치기 (원본 확인용)
```

### 6.4 비교 뷰
```
/compare?products=uuid1,uuid2,uuid3
├── 제품 2~5개 나란히 비교
├── 지표별 바 차트 오버레이
└── 가격/용량/가성비 비교표
```

### 6.5 포지셔닝 맵
```
/sessions/:id/map
├── 2D 스캐터 플롯
│   ├── X축: 가격 (value_score)
│   ├── Y축: 소비자만족도 (consumer_score)
│   ├── 버블 크기: final_score
│   └── 색상: brand_tier
└── 축 변경 가능 (efficacy/formulation/differentiation)
```

---

## 7. 기술 스택 추천

| 항목 | 추천 | 이유 |
|------|------|------|
| **프레임워크** | Next.js 15 (App Router) | Supabase 공식 지원, SSR/ISR |
| **UI** | shadcn/ui + Tailwind | 빠른 대시보드 구축 |
| **차트** | Recharts 또는 Nivo | 레이더 차트, 바 차트, 스캐터 플롯 |
| **Supabase 클라이언트** | `@supabase/supabase-js` v2 | 공식 SDK |
| **배포** | Vercel | Next.js 최적, 무료 티어 충분 |
| **도메인** | (TBD) | `arpt.evas.co.kr` 등 |

---

## 8. 현재 데이터 현황

| 테이블 | 행 수 | 비고 |
|--------|-------|------|
| `arpt_sessions` | 1 | 파일럿 1건 (PDRN 앰플) |
| `arpt_products` | 10 | 파일럿 10개 제품 |
| `arpt_scores` | 19 | ⚠️ 중복 있음 (스코어링 2회 실행, 정리 필요) |
| `arpt_rounds` | 19 | ⚠️ 중복 포함 |
| `arpt_gaps` | 3 | 정상 |

> **주의:** 파일럿 단계라 일부 중복 데이터 존재. 본게임 전 정리 예정.

---

## 9. 향후 추가 예정 테이블 (참고)

ARPT 외에 동일 Supabase 프로젝트에 다른 파이프라인 테이블도 존재/예정:

| Prefix | 테이블 수 | 용도 |
|--------|----------|------|
| `evas_*` | 7 | EVAS 제품/원료 데이터 |
| `cosing_*` | 4 | EU 화장품 성분 DB |
| `incidecoder_*` | 5 | INCIDecoder 성분 크롤링 |
| `arpt_*` | 5 | **이 문서의 대상** |

웹사이트 1단계는 `arpt_*`만 대상. 나중에 확장 가능.

---

## 10. 연락처

| 역할 | 누구 |
|------|------|
| **프로젝트 오너** | Sk Ji (passeth) — EVAS Cosmetic CEO |
| **파이프라인 에이전트** | OpenClaw ARPT Agent (이 문서 작성자) |
| **웹 개발** | (할당 예정) |

---

*EVAS LAB | ARPT Handoff Document | 2026-03-10 v1.0*
