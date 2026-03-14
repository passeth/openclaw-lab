"""통합 스코어링 엔진
Grok 비동기 결과 + 전성분 분석 + 소비자/가성비 계산 → final_score
"""
import math
import re
from typing import Optional

from .config import WEIGHT_PRESETS


def calc_consumer_score(rating: float, review_count: int) -> float:
    """Consumer satisfaction: rating × log(reviews) normalized to 0-100"""
    if not rating or not review_count:
        return 50.0
    raw = rating * math.log10(max(review_count, 1))
    return min(100.0, round(raw * 4, 1))


def calc_value_score(price: float, volume_str: str) -> float:
    """Value score: lower price per mL = higher score"""
    if not price or not volume_str:
        return 50.0
    ml_match = re.search(r'(\d+)', volume_str)
    if not ml_match:
        return 50.0
    ml = int(ml_match.group())
    if ml == 0:
        return 50.0
    price_per_ml = price / ml
    # Benchmark: 500 KRW/mL = average (50), 200 = great (90), 3000 = poor (10)
    score = max(10.0, min(90.0, 100 - (price_per_ml / 30)))
    return round(score, 1)


def compute_final_score(
    product: dict,
    grok_data: dict,
    preset: str = "default"
) -> dict:
    """Compute all scores and return complete score row for Supabase"""
    
    weights = WEIGHT_PRESETS.get(preset, WEIGHT_PRESETS["default"])
    
    # Base metrics
    efficacy = grok_data.get("efficacy_score", 60)
    formulation = grok_data.get("formulation_score", 55)
    differentiation = grok_data.get("differentiation_score", 50)
    consumer = calc_consumer_score(
        product.get("review_rating"),
        product.get("review_count")
    )
    value = calc_value_score(
        float(product.get("price") or 30000),
        product.get("volume") or "30mL"
    )
    
    # Freshness bonuses (from Grok or fallback)
    search_momentum = grok_data.get("search_momentum", 5)
    paper_trend = grok_data.get("paper_trend", 3)
    sns_buzz = grok_data.get("sns_buzz", 3)
    launch_freshness = grok_data.get("launch_freshness", 5)
    ingredient_trend = grok_data.get("ingredient_trend", 3)
    freshness_total = search_momentum + paper_trend + sns_buzz + launch_freshness + ingredient_trend
    
    # Staleness penalties
    review_staleness = grok_data.get("review_staleness", 0)
    ingredient_staleness = grok_data.get("ingredient_staleness", 0)
    no_renewal = grok_data.get("no_renewal", 0)
    staleness_total = review_staleness + ingredient_staleness + no_renewal
    
    # Weighted base
    base_weighted = round(
        efficacy * weights["efficacy"] +
        formulation * weights["formulation"] +
        consumer * weights["consumer"] +
        value * weights["value"] +
        differentiation * weights["differentiation"],
        2
    )
    
    final_score = round(base_weighted + freshness_total + staleness_total, 2)
    
    # Extract volume for price_per_ml
    ml_match = re.search(r'(\d+)', product.get("volume") or "30")
    ml = int(ml_match.group()) if ml_match else 30
    price = float(product.get("price") or 30000)
    
    return {
        "product_id": product["id"],
        "efficacy_score": efficacy,
        "efficacy_evidence": {
            "reason": grok_data.get("efficacy_reason", ""),
            "source": grok_data.get("_source", "fallback")
        },
        "formulation_score": formulation,
        "formulation_notes": {
            "reason": grok_data.get("formulation_reason", ""),
            "source": grok_data.get("_source", "fallback")
        },
        "consumer_score": consumer,
        "consumer_raw": {
            "rating": product.get("review_rating"),
            "review_count": product.get("review_count"),
            "formula": "rating*log10(reviews)*4"
        },
        "value_score": value,
        "value_calc": {
            "price_krw": price,
            "volume_ml": ml,
            "price_per_ml": round(price / max(ml, 1), 1)
        },
        "differentiation_score": differentiation,
        "diff_evidence": {
            "reason": grok_data.get("diff_reason", ""),
            "source": grok_data.get("_source", "fallback")
        },
        "search_momentum": search_momentum,
        "paper_trend": paper_trend,
        "sns_buzz": sns_buzz,
        "launch_freshness": launch_freshness,
        "ingredient_trend": ingredient_trend,
        "freshness_total": freshness_total,
        "review_staleness": review_staleness,
        "ingredient_staleness": ingredient_staleness,
        "no_renewal": no_renewal,
        "staleness_total": staleness_total,
        "base_weighted": base_weighted,
        "final_score": final_score,
        "preset_used": preset
    }
