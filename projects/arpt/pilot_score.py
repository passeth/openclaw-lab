"""ARPT Pilot: Phase 2 - Scoring (simplified for 10-product pilot)"""
import json, math, re, subprocess, time
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"
SESSION_ID = "0c9910f5-77b4-4589-bdd5-499cf972cf67"
XAI_KEY = os.getenv("XAI_API_KEY", "")

sb = create_client(SUPABASE_URL, SERVICE_KEY)

# Fetch products
products = sb.table("arpt_products").select("*").eq("session_id", SESSION_ID).execute().data
print(f"📊 Scoring {len(products)} products...\n")

def grok_analyze(product_name, brand):
    """Call xAI Grok to analyze a PDRN product"""
    prompt = f"""Analyze this PDRN skincare product for R&D benchmarking. Be concise and score each metric 0-100.

Product: {product_name} by {brand}

Score these metrics (0-100 each) with brief justification:
1. Efficacy Score: Key active ingredients effectiveness, clinical evidence for PDRN concentration
2. Formulation Score: Ingredient synergy, stability, texture, pH optimization
3. Differentiation Score: Unique ingredients, patents, novel delivery systems, claims

Also assess:
4. Is this product launched within last 2 years? (yes/no/unknown)
5. Is this brand trending on social media recently? (yes/no/unknown)

Format your response as JSON:
{{"efficacy_score": 0, "efficacy_reason": "", "formulation_score": 0, "formulation_reason": "", "differentiation_score": 0, "diff_reason": "", "launched_recent": "", "trending": ""}}"""
    
    cmd = f"""curl -s -X POST 'https://api.x.ai/v1/responses' \
  -H 'Authorization: Bearer {XAI_KEY}' \
  -H 'Content-Type: application/json' \
  -d '{json.dumps({
    "model": "grok-4-1-fast-reasoning",
    "input": [{"role": "user", "content": prompt}],
    "tools": [{"type": "web_search"}],
    "max_output_tokens": 1500
  })}'"""
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    try:
        resp = json.loads(result.stdout)
        for item in resp.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        return c["text"]
    except:
        pass
    return None

def calc_consumer_score(rating, review_count):
    """Consumer satisfaction: rating × log(reviews) normalized to 0-100"""
    if not rating or not review_count:
        return 50
    # Max theoretical: 5.0 × log10(100000) = 5.0 × 5 = 25
    raw = rating * math.log10(max(review_count, 1))
    return min(100, raw * 4)  # scale to 0-100

def calc_value_score(price, volume_str):
    """Value score: lower price per mL = higher score"""
    if not price or not volume_str:
        return 50
    # Extract mL from volume string
    import re
    ml_match = re.search(r'(\d+)\s*(?:mL|ml)', volume_str)
    if not ml_match:
        return 50
    ml = int(ml_match.group(1))
    price_per_ml = price / ml
    # Benchmark: 500 KRW/mL = average (50), 200 = great (90), 3000 = poor (10)
    score = max(10, min(90, 100 - (price_per_ml / 30)))
    return round(score, 1)

def parse_grok_json(text):
    """Extract JSON from Grok response"""
    if not text:
        return {}
    # Find JSON block
    import re
    json_match = re.search(r'\{[^{}]*"efficacy_score"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    # Try to find any JSON
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                return json.loads(line)
            except:
                continue
    return {}

WEIGHTS = {"efficacy": 0.30, "formulation": 0.20, "consumer": 0.20, "value": 0.15, "differentiation": 0.15}

for i, p in enumerate(products):
    print(f"[{i+1}/10] 🔍 {p['brand']} - {p['product_name'][:40]}...")
    
    # Grok analysis
    grok_text = grok_analyze(p["product_name"], p["brand"])
    grok_data = parse_grok_json(grok_text)
    
    # Scores
    efficacy = grok_data.get("efficacy_score", 60)
    formulation = grok_data.get("formulation_score", 55)
    differentiation = grok_data.get("differentiation_score", 50)
    consumer = calc_consumer_score(p.get("review_rating"), p.get("review_count"))
    value = calc_value_score(p.get("price"), p.get("volume"))
    
    # Freshness bonus
    launched_recent = grok_data.get("launched_recent", "unknown")
    trending = grok_data.get("trending", "unknown")
    
    launch_freshness = 10 if launched_recent == "yes" else (5 if launched_recent == "unknown" else 0)
    sns_buzz = 10 if trending == "yes" else (3 if trending == "unknown" else 0)
    freshness_total = launch_freshness + sns_buzz
    
    # Staleness penalty
    staleness_total = 0
    if p.get("review_count", 0) > 5000 and (p.get("review_rating", 0) < 4.3):
        staleness_total -= 5  # high volume but declining quality signal
    
    # Weighted total
    base = (efficacy * WEIGHTS["efficacy"] + 
            formulation * WEIGHTS["formulation"] + 
            consumer * WEIGHTS["consumer"] + 
            value * WEIGHTS["value"] + 
            differentiation * WEIGHTS["differentiation"])
    
    final = base + freshness_total + staleness_total
    
    score_data = {
        "product_id": p["id"],
        "efficacy_score": efficacy,
        "efficacy_evidence": {"reason": grok_data.get("efficacy_reason", ""), "source": "grok"},
        "formulation_score": formulation,
        "formulation_notes": {"reason": grok_data.get("formulation_reason", ""), "source": "grok"},
        "consumer_score": round(consumer, 1),
        "consumer_raw": {"rating": p.get("review_rating"), "review_count": p.get("review_count"), "formula": "rating * log10(reviews) * 4"},
        "value_score": round(value, 1),
        "value_calc": {"price": p.get("price"), "volume": p.get("volume"), "price_per_ml": round(p.get("price", 0) / max(1, int(re.search(r'(\d+)', p.get("volume", "30")).group() if re.search(r'(\d+)', p.get("volume", "30")) else "30")), 1)},
        "differentiation_score": differentiation,
        "diff_evidence": {"reason": grok_data.get("diff_reason", ""), "source": "grok"},
        "launch_freshness": launch_freshness,
        "sns_buzz": sns_buzz,
        "freshness_total": freshness_total,
        "staleness_total": staleness_total,
        "base_weighted": round(base, 2),
        "final_score": round(final, 2),
        "preset_used": "default"
    }
    
    sb.table("arpt_scores").insert(score_data).execute()
    print(f"  📈 Base: {base:.1f} | Fresh: +{freshness_total} | Stale: {staleness_total} | Final: {final:.1f}")
    
    time.sleep(1)  # rate limit

# Update session
sb.table("arpt_sessions").update({"status": "tournament"}).eq("id", SESSION_ID).execute()
print(f"\n🏆 Phase 2 complete → status: tournament")
