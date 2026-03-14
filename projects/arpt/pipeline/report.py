"""ARPT Report Generator — 2종 리포트 자동 생성
Report A: 처방 제안서 (R&D 연구원용)
Report B: 상품 기획 제안서 (상품기획자용)
"""
import json
import asyncio
import aiohttp
import re
from datetime import datetime
from typing import Optional

from .config import XAI_API_KEY, XAI_MODEL, XAI_BASE_URL
from .ingredients import analyze_key_ingredients


async def _call_grok_report(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Grok for report generation"""
    payload = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": max_tokens
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                XAI_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=180)
            ) as resp:
                data = await resp.json()
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for c in item.get("content", []):
                            if c.get("type") == "output_text":
                                return c["text"]
    except Exception as e:
        print(f"  ❌ Grok report error: {e}")
    return None


def _build_data_context(session_data: dict, products: list, scores: list, gaps: list, champions: list) -> str:
    """Build common data context string for report prompts"""
    topic = session_data.get("topic", "")
    
    # Product + score merged view
    score_map = {}
    for s in scores:
        score_map[s["product_id"]] = s
    
    product_lines = []
    for p in products:
        s = score_map.get(p["id"], {})
        ings = p.get("full_ingredients", "")
        analysis = (p.get("raw_data") or {}).get("ingredient_analysis", {})
        actives = [a["name"] + "(" + a["role"] + ")" for a in analysis.get("actives", [])] if analysis else []
        
        is_champ = p["id"] in [c["product_id"] for c in champions]
        champ_mark = "🏆" if is_champ else "  "
        
        line = f"""{champ_mark} {p['brand']} — {p['product_name']}
   Tier: {p.get('brand_tier','?')} | Price: ₩{p.get('price',0):,} / {p.get('volume','?')} | Rating: {p.get('review_rating','?')} ({p.get('review_count',0):,} reviews)
   Scores: E:{s.get('efficacy_score','?')} F:{s.get('formulation_score','?')} C:{s.get('consumer_score','?')} V:{s.get('value_score','?')} D:{s.get('differentiation_score','?')} → Final:{s.get('final_score','?')}
   Freshness: +{s.get('freshness_total',0)} | Staleness: {s.get('staleness_total',0)}"""
        if actives:
            line += f"\n   Active ingredients: {', '.join(actives[:8])}"
        if ings:
            line += f"\n   Full INCI ({ings.count(',') + 1} ingredients): {ings[:300]}..."
        product_lines.append(line)
    
    gap_lines = []
    for g in gaps:
        evidence = g.get("evidence", {}) or {}
        gap_lines.append(f"- [{g.get('opportunity_score',0)}점] {g.get('gap_type','')}: {g.get('gap_description','')}")
        if evidence.get("suggested_action"):
            gap_lines.append(f"  → 제안: {evidence['suggested_action']}")
    
    return f"""## 주제: {topic}
## 제품 {len(products)}개 (🏆 = 챔피언)
{chr(10).join(product_lines)}

## Gap 분석 ({len(gaps)}건)
{chr(10).join(gap_lines)}
"""


def _report_a_prompt(data_context: str, topic: str) -> str:
    """Report A: 처방 제안서 프롬프트"""
    return f"""당신은 화장품 R&D 처방 전문가입니다. 아래 ARPT 토너먼트 데이터를 분석하여 **처방 제안서**를 작성하세요.

대상 독자: 제형 연구원, 처방 개발자
목적: 챔피언 제품의 처방 분석 → 신제품 처방 설계 근거

{data_context}

## 작성 지침
아래 구조로 한글 마크다운 리포트를 작성하세요:

# 🧪 ARPT 처방 제안서 — "{topic}"

## 1. 핵심 성분 분석
- 챔피언 제품 전성분 비교 (공통 성분 vs 차별 성분)
- 활성 성분별 역할과 추정 함량 범위
- PDRN(Sodium DNA) 관련 성분의 위치와 역할 분석
- 안전성 프로파일 요약

## 2. 처방 패턴 분석
- 공통 베이스 구조 (유화제, 증점제, 보존제 패턴)
- 성분 시너지 맵 (상호 강화 조합)
- 성분 충돌 경고 (pH 불일치, 안정성 리스크)

## 3. 구조적 공백 → 처방 기회
- Gap별 추천 성분 조합 (구체적 INCI명 제시)
- 예상 안정성 이슈 및 해결 방향
- 참고 문헌/논문

## 4. 신처방 제안 (3안)
- **Safe Bet**: 검증된 성분 조합 + 개선점 → 전성분 초안
- **Trend Rider**: 트렌드 성분 투입 → 전성분 초안
- **Blue Ocean**: 미탐색 조합 → 전성분 초안
- 각 안별: 예상 pH, 제형 타입, 안정성 유의사항

## 5. 원료 소싱 참고
- 핵심 원료 추천 및 원가 추정 범위

**분량: 충분히 상세하게. 연구원이 바로 처방 설계에 참고할 수 있을 정도.**
"""


def _report_b_prompt(data_context: str, topic: str) -> str:
    """Report B: 상품 기획 제안서 프롬프트"""
    return f"""당신은 화장품 상품 기획 전문가입니다. 아래 ARPT 토너먼트 데이터를 분석하여 **상품 기획 제안서**를 작성하세요.

대상 독자: 상품 기획자, 마케팅팀, 영업팀
목적: 시장 기회 분석 → 신제품 포지셔닝 + 상품 기획 의사결정 근거

{data_context}

## 작성 지침
아래 구조로 한글 마크다운 리포트를 작성하세요:

# 📊 ARPT 상품 기획 제안서 — "{topic}"

## 1. 시장 경쟁 구도
- 전체 순위표 (점수 + 주요 지표 요약)
- 브랜드 티어별 분포 (K-뷰티/글로벌/인디/럭셔리)
- 가격대별 분포 (저가/중가/고가/프리미엄)
- 간단한 포지셔닝 분석 (가격 vs 소비자만족도)

## 2. 챔피언 5개 프로필
- 각 제품별 강점/약점 요약
- 소비자 리뷰 핵심 키워드 추정 (긍정/부정)
- 왜 이 제품이 챔피언이 되었는가

## 3. 트렌드 & 소비자 인사이트
- 최신성 가점 분석 (왜 이 제품들이 높은 가점?)
- 소비자가 가장 원하는 것

## 4. 기회 영역 (Gap → 상품 컨셉)
- Gap별 타깃 고객 프로파일
- 예상 가격대 + 채널 전략
- 경쟁 강도 평가

## 5. 신상품 기획안 (3안)
- **Safe Bet / Trend Rider / Blue Ocean**
- 각 안별: 상품명 제안, 가격대, 타깃, 채널, 패키지 컨셉, USP
- 예상 포지셔닝 (기존 챔피언 대비 위치)

## 6. 실행 로드맵
- 개발 → 시제품 → 인허가 → 양산 타임라인 (대략)
- Go/No-Go 판단 체크리스트

**분량: 충분히 상세하게. 기획자가 바로 기획서에 인용할 수 있을 정도. 수치와 구체적 제안 중심.**
"""


def generate_reports(session_id: str, supabase_client) -> dict:
    """Generate both reports and return markdown strings"""
    print("\n" + "="*60)
    print("📝 PHASE: Report Generation (2종)")
    print("="*60)
    
    sb = supabase_client
    
    # Fetch all data
    session_data = sb.table("arpt_sessions").select("*").eq("id", session_id).single().execute().data
    products = sb.table("arpt_products").select("*").eq("session_id", session_id).execute().data
    
    product_ids = [p["id"] for p in products]
    scores = sb.table("arpt_scores").select("*").in_("product_id", product_ids).execute().data
    gaps = sb.table("arpt_gaps").select("*").eq("session_id", session_id).order("opportunity_score", desc=True).execute().data
    champions = sb.table("arpt_rounds").select("product_id, round_score").eq("session_id", session_id).eq("advanced", True).order("round_score", desc=True).execute().data
    
    topic = session_data.get("topic", "Unknown")
    data_context = _build_data_context(session_data, products, scores, gaps, champions)
    
    # Generate Report A
    print("\n📋 Generating Report A: 처방 제안서...")
    prompt_a = _report_a_prompt(data_context, topic)
    report_a = asyncio.run(_call_grok_report(prompt_a, max_tokens=10000))
    
    if report_a:
        # Add metadata header
        report_a = f"""<!-- ARPT Report A: 처방 제안서 | {topic} | {datetime.now().strftime('%Y-%m-%d')} -->
<!-- Session: {session_id} -->

{report_a}

---
*EVAS LAB | ARPT v1.2 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        print(f"  ✅ Report A: {len(report_a):,} chars")
    else:
        print("  ❌ Report A generation failed")
        report_a = f"# 처방 제안서 생성 실패\nSession: {session_id}"
    
    # Generate Report B
    print("\n📊 Generating Report B: 상품 기획 제안서...")
    prompt_b = _report_b_prompt(data_context, topic)
    report_b = asyncio.run(_call_grok_report(prompt_b, max_tokens=10000))
    
    if report_b:
        report_b = f"""<!-- ARPT Report B: 상품 기획 제안서 | {topic} | {datetime.now().strftime('%Y-%m-%d')} -->
<!-- Session: {session_id} -->

{report_b}

---
*EVAS LAB | ARPT v1.2 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        print(f"  ✅ Report B: {len(report_b):,} chars")
    else:
        print("  ❌ Report B generation failed")
        report_b = f"# 상품 기획 제안서 생성 실패\nSession: {session_id}"
    
    return {"report_a": report_a, "report_b": report_b, "topic": topic}
