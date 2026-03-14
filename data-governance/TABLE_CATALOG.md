# EVAS Intel DB — 테이블 카탈로그 (v3 최종)

> Supabase EVAS Intel (`ejbbdtjoqapheqieoohs`) — 2026-03-10 마이그레이션  
> 이전 프로젝트: `rtbydkobtrqurvxrajep` (용량 초과로 이전)  
> 최종 정리: 2026-03-10 10:20  
> 작성: obsi + passeth

---

## 📊 전체 현황: 16개 테이블 / 1,057,878행

---

### 🏭 `evas_` — 자사 내부 데이터 (7개 / 47,671행)

| # | 테이블 | 행 수 | 설명 |
|---|--------|------:|------|
| 1 | `evas_labdoc_products` | 1,572 | 자사 제품 마스터 (MES) |
| 2 | `evas_labdoc_ingredients` | 1,066 | 자사 원료 마스터 (MES) |
| 3 | `evas_product_compositions` | 39,415 | 자사 제품 전성분 BOM (1,254제품) |
| 4 | `evas_research_product_contexts_v2` | 735 | 제품 컨텍스트 팩 (분석 입력) |
| 5 | `evas_research_product_interactions_v2` | 117 | 성분 조합 상호작용 분석 |
| 6 | `evas_research_tech_reports_v2` | 738 | 기술 보고서 (30~60KB/건, Opus v3) |
| 7 | `evas_research_pipeline_runs_v2` | 4,028 | 파이프라인 실행 로그 |

**생성 이력:**
- `evas_labdoc_*`: Commerce DB(`labdoc_product_bom`, `labdoc_ingredients`) → Intel 동기화
- `evas_product_compositions`: Commerce BOM SELECT → Intel INSERT (2026-03-04, 255→1,254제품 확장)
- `evas_research_*`: Evidence-Locked Pipeline v2 — Claude Opus/시지푸스 스킬로 자사 제품 심층 분석

---

### 🧬 `cosing_` — EU CosIng 성분 규제 (4개 / 81,267행)

| # | 테이블 | 행 수 | 설명 |
|---|--------|------:|------|
| 8 | `cosing_substances` | 18,942 | EU CosIng 성분 마스터 (PK=substance_id) |
| 9 | `cosing_substance_functions` | 29,985 | 성분→기능 매핑 (N:M) |
| 10 | `cosing_regulations` | 2,379 | EU 규제 조항 (Annex II~VI) |
| 11 | `cosing_function_contexts` | 29,961 | LLM 생성 성분 컨텍스트 (Kimi K2) |

**생성 이력:**
- `cosing_substances/substance_functions/regulations`: EU CosIng CSV 공식 데이터 파싱
- `cosing_function_contexts`: `generate_contexts_v2.py` — per-substance 방식, Kimi K2 Turbo, 5워커 병렬. 6필드(mechanism, typical_conc, product_types, when_primary, when_secondary, incompatibility). 규제는 DB JOIN만 허용 (LLM 환각 방지)

---

### 🔬 `incidecoder_` — INCIDecoder 기반 + 연구 (5개 / 928,940행)

| # | 테이블 | 행 수 | 설명 |
|---|--------|------:|------|
| 12 | `incidecoder_ingredients` | 1,320 | INCIDecoder 성분 DB (크롤링) |
| 13 | `incidecoder_products` | 34,774 | INCIDecoder 제품 DB (크롤링) |
| 14 | `incidecoder_composition_inferred` | 885,533 | 성분비 추론 (labbot, Kimi K2.5) |
| 15 | `incidecoder_research_ingredient_evidence_v2` | 5,993 | 성분별 논문 근거 (Grok 딥리서치) |
| 16 | `incidecoder_research_ingredient_safety_v2` | 1,320 | 성분별 안전성 요약 (Grok) |

**생성 이력:**
- `incidecoder_ingredients/products`: INCIDecoder 사이트 크롤링
- `incidecoder_composition_inferred`: labbot이 `incidecoder_products` 34,774개의 전성분 순서에서 Kimi K2.5로 함량% 추론. 6,598제품/19% 시점에서 중단. 처방 레퍼런스 용도
- `incidecoder_research_ingredient_evidence_v2`: Stage 0-A — `scripts/pipeline_v2/stage0_ingredient_evidence.js`, Grok(xAI) 딥리서치, 1,317/1,320 성분 완료, $50.08
- `incidecoder_research_ingredient_safety_v2`: Stage 0-A에서 함께 생성

---

## 🏗️ 데이터 파이프라인 흐름도

```
[EU CosIng 공식]
  cosing_substances ─── 성분 마스터 (18,942)
    ├── cosing_substance_functions ─── 기능 매핑 (29,985)
    ├── cosing_regulations ─── 규제 (2,379)
    └── cosing_function_contexts ─── AI 컨텍스트 (29,961)

[INCIDecoder 크롤링]
  incidecoder_ingredients ─── 성분 프로파일 (1,320)
    ├── incidecoder_research_ingredient_evidence_v2 ─── 논문 근거 (5,993)
    └── incidecoder_research_ingredient_safety_v2 ─── 안전성 (1,320)
  incidecoder_products ─── 시장 제품 (34,774)
    └── incidecoder_composition_inferred ─── 성분비 추론 (885,533)

[EVAS 내부]
  evas_labdoc_ingredients ─── 자사 원료 (1,066)
  evas_labdoc_products ─── 자사 제품 (1,572)
  evas_product_compositions ─── 자사 BOM (39,415)
    ├── evas_research_product_contexts_v2 ─── 컨텍스트 (735)
    │     ├── evas_research_product_interactions_v2 ─── 상호작용 (117)
    │     └── evas_research_tech_reports_v2 ─── 기술보고서 (738)
    └── evas_research_pipeline_runs_v2 ─── 실행 로그 (4,028)

[ARPT — 제품 토너먼트 (2026-03-10 신규)]
  arpt_sessions ─── 토너먼트 세션 마스터
    ├── arpt_products ─── 수집 제품 원본 (50개/세션)
    │     └── arpt_scores ─── 다중 지표 스코어링
    ├── arpt_rounds ─── 토너먼트 라운드 기록 (3라운드)
    └── arpt_gaps ─── 구조적 공백/기회 영역

[미생성 — prefix 예약]
  oliveyoung_* ─── 올리브영 랭킹/제품/리뷰
  amazon_* ─── 아마존 마켓 데이터
  influencer_* ─── 인플루언서 모니터링
```

---

## 📌 Prefix 규칙 (확정)

| Prefix | 오리진 | 설명 |
|--------|--------|------|
| `evas_` | 자사 MES/OMS | 제품/원료/BOM |
| `evas_research_` | 자사 제품 기반 AI 분석 | Evidence-Locked 파이프라인 |
| `cosing_` | EU CosIng 공식 | 성분 규제 온톨로지 |
| `incidecoder_` | INCIDecoder 크롤링 | 시장 성분/제품 + AI 추론/연구 |
| `oliveyoung_` | 올리브영 크롤링 | 랭킹/제품/리뷰 시계열 |
| `amazon_` | 아마존 크롤링 | 마켓 데이터 |
| `influencer_` | YouTube/소셜 | 콘텐츠 모니터링 |
| `arpt_` | ARPT 토너먼트 | 제품 수집/스코어링/토너먼트/갭 분석 |

---

## 🗑️ 삭제 이력 (2026-03-05)

총 19개 테이블 삭제:
`rv2_whitepapers`, `rv2_research_proposals`, `oy_products`, `oy_rankings`, `oy_review_summary`, `oy_product_intel`, `influencer_ingredient_mentions`, `influencer_monitor_sessions`, `influencer_videos`, `innovation_briefs`, `pipeline_runs_v2`, `prep_product_contexts`, `product_reports`, `inferred_compositions`, `cosing_functions_master`, `research_market_reports_v2`, `evidence_claims`, `evidence_papers`, `rv2_formulation_reports`, `tech_reports`

---

## 📋 에이전트 전달 사항

> **2026-03-05 테이블명 전면 변경**  
> 기존 쿼리의 테이블명을 아래와 같이 교체:
>
> | 이전 | 현재 |
> |------|------|
> | `lab_products` | `incidecoder_products` |
> | `lab_ingredients` | `incidecoder_ingredients` |
> | `rv2_composition_inferred` | `incidecoder_composition_inferred` |
> | `product_compositions` | `evas_product_compositions` |
> | `labdoc_ingredients` | `evas_labdoc_ingredients` |
> | `labdoc_products` | `evas_labdoc_products` |
> | `rv2_ingredient_evidence` | `incidecoder_research_ingredient_evidence_v2` |
> | `rv2_ingredient_safety` | `incidecoder_research_ingredient_safety_v2` |
> | `rv2_product_contexts` | `evas_research_product_contexts_v2` |
> | `rv2_product_interactions` | `evas_research_product_interactions_v2` |
> | `rv2_tech_reports` | `evas_research_tech_reports_v2` |
> | `rv2_pipeline_runs` | `evas_research_pipeline_runs_v2` |
