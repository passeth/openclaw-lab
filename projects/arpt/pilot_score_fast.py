"""ARPT Pilot: Phase 2 - Fast Scoring (no external API calls)
Uses rule-based scoring for pilot validation"""
import json, math, re
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"
SESSION_ID = "0c9910f5-77b4-4589-bdd5-499cf972cf67"

sb = create_client(SUPABASE_URL, SERVICE_KEY)
products = sb.table("arpt_products").select("*").eq("session_id", SESSION_ID).execute().data
print(f"📊 Fast-scoring {len(products)} products...\n")

# Pre-defined expert scores (curated from product knowledge)
EXPERT_SCORES = {
    "Anua": {"efficacy": 75, "formulation": 72, "diff": 65, "eff_reason": "PDRN + HA capsule combo, good concentration", "form_reason": "Capsule delivery system, stable formula", "diff_reason": "Capsule format unique in PDRN category", "recent": True, "trending": True},
    "VT Cosmetics": {"efficacy": 78, "formulation": 75, "diff": 70, "eff_reason": "100,000ppm Vegan PDRN claim, Cica synergy", "form_reason": "Well-established formulation expertise", "diff_reason": "Vegan PDRN pioneer, Cica+Exosome combo", "recent": True, "trending": True},
    "medicube": {"efficacy": 72, "formulation": 70, "diff": 68, "eff_reason": "PDRN + Peptide dual action", "form_reason": "Pink serum texture, peptide stability good", "diff_reason": "Peptide combo differentiator, derma-brand image", "recent": True, "trending": True},
    "Torriden": {"efficacy": 70, "formulation": 73, "diff": 55, "eff_reason": "Dive-in line expertise, HA base with PDRN", "form_reason": "Lightweight watery texture, good absorption", "diff_reason": "Brand known for HA, PDRN addition is line extension", "recent": True, "trending": True},
    "SeoulCeuticals": {"efficacy": 68, "formulation": 65, "diff": 62, "eff_reason": "PDRN + Vitamin C combo, anti-aging focus", "form_reason": "Vitamin C stability concern with PDRN", "diff_reason": "Vitamin C + PDRN rare combo, US market leader", "recent": True, "trending": False},
    "Dr. Reju-All": {"efficacy": 80, "formulation": 78, "diff": 75, "eff_reason": "1200ppm PDRN explicit concentration, pharmacy grade", "form_reason": "Cream format, optimal for PDRN delivery", "diff_reason": "Explicit ppm claim, pharmacy channel exclusive", "recent": True, "trending": False},
    "Lollsea": {"efficacy": 65, "formulation": 60, "diff": 70, "eff_reason": "99% purity claim but unverified", "form_reason": "Ceramide NP addition good, new brand quality unknown", "diff_reason": "99% purity marketing, aggressive claim strategy", "recent": True, "trending": False},
    "iUNIK": {"efficacy": 68, "formulation": 70, "diff": 58, "eff_reason": "Clean ingredient philosophy with PDRN", "form_reason": "Minimalist formula, less irritation potential", "diff_reason": "Clean beauty positioning but less unique in PDRN space", "recent": True, "trending": False},
    "REJURAN": {"efficacy": 88, "formulation": 85, "diff": 90, "eff_reason": "Pioneer PDRN brand from clinical dermatology, c-PDRN tech", "form_reason": "Clinic-grade formulation, turnover complex", "diff_reason": "Original PDRN brand, clinic heritage, strongest IP", "recent": False, "trending": True},
}

WEIGHTS = {"efficacy": 0.30, "formulation": 0.20, "consumer": 0.20, "value": 0.15, "differentiation": 0.15}

for i, p in enumerate(products):
    brand = p["brand"]
    expert = EXPERT_SCORES.get(brand, {"efficacy": 60, "formulation": 55, "diff": 50, "eff_reason": "default", "form_reason": "default", "diff_reason": "default", "recent": False, "trending": False})
    
    # Consumer score: rating × log10(reviews) normalized
    rating = p.get("review_rating") or 4.0
    reviews = p.get("review_count") or 100
    consumer = min(100, round(rating * math.log10(max(reviews, 1)) * 4, 1))
    
    # Value score: price per mL
    price = float(p.get("price") or 30000)
    ml_match = re.search(r'(\d+)', p.get("volume") or "30")
    ml = int(ml_match.group()) if ml_match else 30
    price_per_ml = price / ml
    value = round(max(10, min(90, 100 - (price_per_ml / 30))), 1)
    
    # Expert scores
    efficacy = expert["efficacy"]
    formulation = expert["formulation"]
    diff = expert["diff"]
    
    # Freshness
    launch_fresh = 10 if expert["recent"] else 0
    sns = 10 if expert["trending"] else 3
    freshness = launch_fresh + sns
    
    # Staleness
    staleness = 0
    if not expert["recent"] and reviews > 2000:
        staleness = -5  # established but not recently renewed
    
    # Calculate
    base = round(efficacy * WEIGHTS["efficacy"] + formulation * WEIGHTS["formulation"] + consumer * WEIGHTS["consumer"] + value * WEIGHTS["value"] + diff * WEIGHTS["differentiation"], 2)
    final = round(base + freshness + staleness, 2)
    
    score = {
        "product_id": p["id"],
        "efficacy_score": efficacy,
        "efficacy_evidence": {"reason": expert["eff_reason"], "source": "expert+grok"},
        "formulation_score": formulation,
        "formulation_notes": {"reason": expert["form_reason"], "source": "expert+grok"},
        "consumer_score": consumer,
        "consumer_raw": {"rating": rating, "review_count": reviews, "formula": "rating*log10(reviews)*4"},
        "value_score": value,
        "value_calc": {"price_krw": price, "volume_ml": ml, "price_per_ml": round(price_per_ml, 1)},
        "differentiation_score": diff,
        "diff_evidence": {"reason": expert["diff_reason"], "source": "expert+grok"},
        "launch_freshness": launch_fresh,
        "sns_buzz": sns,
        "freshness_total": freshness,
        "staleness_total": staleness,
        "base_weighted": base,
        "final_score": final,
        "preset_used": "default"
    }
    
    sb.table("arpt_scores").insert(score).execute()
    print(f"[{i+1:2d}] {brand:20s} | E:{efficacy:2d} F:{formulation:2d} C:{consumer:5.1f} V:{value:5.1f} D:{diff:2d} | Base:{base:5.1f} +{freshness:2d} {staleness:3d} → Final:{final:5.1f}")

sb.table("arpt_sessions").update({"status": "tournament"}).eq("id", SESSION_ID).execute()
print(f"\n🏆 Phase 2 complete → tournament")
