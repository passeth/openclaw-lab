"""개선 #1: xAI Grok 비동기 분석
- asyncio + aiohttp로 병렬 호출
- 120초 타임아웃
- 실패 시 룰 기반 fallback
"""
import asyncio
import aiohttp
import json
import re
from typing import Optional

from .config import XAI_API_KEY, XAI_MODEL, XAI_BASE_URL, GROK_TIMEOUT


def _build_scoring_prompt(product_name: str, brand: str, ingredients: str = "") -> str:
    ing_section = f"\nFull Ingredients (INCI): {ingredients}" if ingredients else ""
    return f"""You are a cosmetics R&D analyst. Analyze this product for competitive benchmarking.

Product: {product_name}
Brand: {brand}{ing_section}

Score these metrics (0-100) with brief justification:
1. efficacy_score: Active ingredient effectiveness, clinical evidence, concentration
2. formulation_score: Ingredient synergy, stability, texture, pH optimization, safety profile
3. differentiation_score: Unique ingredients, patents, novel delivery systems, unique claims

Also assess freshness signals:
4. search_momentum: Is search volume rising? (0-15, 15=rapidly rising)
5. sns_buzz: Social media mentions accelerating? (0-10, 10=viral)
6. launch_freshness: Launched within 1yr=10, 2yr=5, older=0
7. ingredient_trend: Contains trending ingredients this year? (0-5)
8. paper_trend: Recent scientific publications on key ingredients? (0-10)

And staleness signals:
9. review_staleness: Recent review ratio declining? (0 to -10)
10. ingredient_staleness: All actives are 10yr+ commodity ingredients? (0 to -10)
11. no_renewal: No formula update in 3+ years? (0 to -5)

Respond ONLY with a JSON object (no markdown, no explanation):
{{"efficacy_score": 0, "efficacy_reason": "", "formulation_score": 0, "formulation_reason": "", "differentiation_score": 0, "diff_reason": "", "search_momentum": 0, "sns_buzz": 0, "launch_freshness": 0, "ingredient_trend": 0, "paper_trend": 0, "review_staleness": 0, "ingredient_staleness": 0, "no_renewal": 0}}"""


def _parse_grok_json(text: str) -> dict:
    """Extract JSON from Grok response, handling markdown blocks"""
    if not text:
        return {}
    # Try markdown code block first
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    json_match = re.search(r'\{[^{}]*"efficacy_score"[^}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


async def _call_grok_single(
    session: aiohttp.ClientSession,
    product_name: str,
    brand: str,
    ingredients: str = "",
    timeout: int = GROK_TIMEOUT
) -> Optional[dict]:
    """Single async Grok API call with timeout"""
    prompt = _build_scoring_prompt(product_name, brand, ingredients)
    payload = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 2000
    }
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with session.post(
            XAI_BASE_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            data = await resp.json()
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            return _parse_grok_json(c["text"])
    except asyncio.TimeoutError:
        print(f"  ⏱️ TIMEOUT ({timeout}s): {brand} - {product_name[:30]}")
    except Exception as e:
        print(f"  ❌ ERROR: {brand} - {product_name[:30]}: {e}")
    return None


def _fallback_scores(brand: str, review_rating: float = 4.0, review_count: int = 100) -> dict:
    """Rule-based fallback when Grok fails"""
    # Brand tier heuristics
    brand_lower = brand.lower()
    if brand_lower in ['rejuran', 'sk-ii', 'la mer', 'sulwhasoo']:
        base_eff, base_form, base_diff = 85, 82, 85
    elif brand_lower in ['anua', 'vt cosmetics', 'medicube', 'torriden', 'cosrx']:
        base_eff, base_form, base_diff = 72, 70, 65
    elif brand_lower in ['seoulceuticals', 'lollsea']:
        base_eff, base_form, base_diff = 65, 62, 60
    else:
        base_eff, base_form, base_diff = 60, 58, 55
    
    # Adjust by reviews
    if review_rating and review_rating > 4.5:
        base_eff += 5
        base_form += 3
    
    return {
        "efficacy_score": base_eff,
        "efficacy_reason": "[fallback] brand-tier heuristic",
        "formulation_score": base_form,
        "formulation_reason": "[fallback] brand-tier heuristic",
        "differentiation_score": base_diff,
        "diff_reason": "[fallback] brand-tier heuristic",
        "search_momentum": 5,
        "sns_buzz": 5 if review_count > 1000 else 3,
        "launch_freshness": 5,
        "ingredient_trend": 3,
        "paper_trend": 3,
        "review_staleness": 0,
        "ingredient_staleness": 0,
        "no_renewal": 0,
        "_fallback": True
    }


async def analyze_batch(products: list[dict], concurrency: int = 5) -> dict:
    """Analyze a batch of products with Grok, falling back as needed.
    
    Args:
        products: list of product dicts from Supabase
        concurrency: max concurrent requests
        
    Returns:
        dict mapping product_id -> scoring dict
    """
    results = {}
    sem = asyncio.Semaphore(concurrency)
    
    async def _analyze_one(product):
        async with sem:
            pid = product["id"]
            brand = product.get("brand", "Unknown")
            name = product.get("product_name", "")
            ingredients = product.get("full_ingredients", "") or ""
            
            async with aiohttp.ClientSession() as session:
                grok_result = await _call_grok_single(session, name, brand, ingredients)
            
            if grok_result and "efficacy_score" in grok_result:
                grok_result["_source"] = "grok"
                results[pid] = grok_result
                print(f"  ✅ Grok: {brand} - E:{grok_result['efficacy_score']} F:{grok_result['formulation_score']} D:{grok_result['differentiation_score']}")
            else:
                fallback = _fallback_scores(brand, product.get("review_rating"), product.get("review_count"))
                results[pid] = fallback
                print(f"  🔄 Fallback: {brand} - E:{fallback['efficacy_score']} F:{fallback['formulation_score']} D:{fallback['differentiation_score']}")
    
    tasks = [_analyze_one(p) for p in products]
    await asyncio.gather(*tasks)
    return results


def run_batch(products: list[dict], concurrency: int = 5) -> dict:
    """Sync wrapper for analyze_batch"""
    return asyncio.run(analyze_batch(products, concurrency))
