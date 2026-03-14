"""ARPT Phase 1: Auto Product Scouting via xAI Grok
50개 제품을 자동 수집 (K-beauty 25, Global 15, Indie 7, Luxury/Derma 3)
"""
import asyncio
import aiohttp
import json
import re
import uuid
from typing import Optional

from .config import XAI_API_KEY, XAI_MODEL, XAI_BASE_URL, GROK_TIMEOUT


TIER_TARGETS = {
    "k-beauty": 25,
    "global": 15,
    "indie": 7,
    "luxury-derma": 3,
}

def _build_scout_prompt(topic: str, tier: str, count: int, exclude_brands: list[str] = None) -> str:
    exclude_text = ""
    if exclude_brands:
        exclude_text = f"\n\nEXCLUDE these brands (already collected): {', '.join(exclude_brands)}"
    
    tier_guidance = {
        "k-beauty": "Korean beauty brands sold on Korean platforms (Oliveyoung, Coupang, 화해). Include both major (Amorepacific, LG H&H sub-brands) and mid-tier popular brands.",
        "global": "International brands available globally (Amazon, Sephora, Ulta, YesStyle). Include US, EU, Japanese, Southeast Asian brands.",
        "indie": "Independent/clean beauty/DTC brands. Small batch, niche, or emerging brands with unique positioning.",
        "luxury-derma": "Luxury or dermatological/clinical brands. Premium price point, clinic channel, or medical-grade products.",
    }
    
    return f"""You are a cosmetics market research expert. Search the web for competing products in this category.

TOPIC: {topic}
TIER: {tier} — {tier_guidance[tier]}
FIND: {count} products{exclude_text}

For EACH product, provide:
- product_name: Full official product name
- brand: Brand name
- price: Price in KRW (convert if needed, approximate is OK)
- volume: Product volume (e.g., "30mL")
- review_count: Approximate number of reviews across platforms
- review_rating: Average rating (1-5 scale)
- source_platform: Where you found it (amazon/oliveyoung/hwahae/yesstyle/coupang/sephora/other)
- source_url: Product URL (if available)
- key_claims: Main marketing claims (1-2 sentences)
- key_ingredients: Top 3-5 active ingredients

Respond ONLY with a JSON array (no markdown, no explanation):
[{{"product_name": "...", "brand": "...", "price": 0, "volume": "...", "review_count": 0, "review_rating": 0.0, "source_platform": "...", "source_url": "...", "key_claims": "...", "key_ingredients": "..."}}]

IMPORTANT:
- Each product must be DISTINCT (no duplicates, no same product different sizes)
- Include real products currently on sale (not discontinued)
- Prioritize products with high review counts and recent launches
- Return EXACTLY {count} products"""


def _parse_products_json(text: str) -> list[dict]:
    """Extract JSON array from Grok response, handling truncated output"""
    if not text:
        return []
    
    # Find the start of the JSON array
    start = text.find('[')
    if start == -1:
        return []
    
    json_text = text[start:]
    
    # Try full parse first
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        pass
    
    # Handle truncated JSON: find last complete object
    results = []
    # Split by },{ pattern to find individual objects
    depth = 0
    obj_start = None
    for i, ch in enumerate(json_text):
        if ch == '{' and depth == 0:
            obj_start = i
            depth = 1
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and obj_start is not None:
                obj_str = json_text[obj_start:i+1]
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict) and obj.get("product_name"):
                        results.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None
    
    return results


async def _scout_tier(topic: str, tier: str, count: int, exclude_brands: list[str] = None) -> list[dict]:
    """Scout products for a single tier via Grok"""
    prompt = _build_scout_prompt(topic, tier, count, exclude_brands)
    payload = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 16000,
    }
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                XAI_BASE_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=180)  # 3min for large lists
            ) as resp:
                data = await resp.json()
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for c in item.get("content", []):
                            if c.get("type") == "output_text":
                                products = _parse_products_json(c["text"])
                                return products
    except asyncio.TimeoutError:
        print(f"  ⏱️ TIMEOUT: {tier} scouting")
    except Exception as e:
        print(f"  ❌ ERROR: {tier}: {e}")
    return []


async def scout_all_tiers(topic: str) -> list[dict]:
    """Scout products across all tiers in parallel"""
    all_products = []
    collected_brands = set()
    
    # Run tiers sequentially to avoid brand overlap
    for tier, target_count in TIER_TARGETS.items():
        print(f"\n🔍 Scouting {tier} ({target_count} products)...")
        exclude = list(collected_brands) if collected_brands else None
        
        products = await _scout_tier(topic, tier, target_count, exclude)
        
        # Deduplicate by brand+name
        unique = []
        for p in products:
            brand = p.get("brand", "").strip()
            name = p.get("product_name", "").strip()
            key = f"{brand}|{name}".lower()
            if key not in {f"{pp.get('brand','')}|{pp.get('product_name','')}".lower() for pp in all_products + unique}:
                p["brand_tier"] = tier
                unique.append(p)
                collected_brands.add(brand)
        
        all_products.extend(unique)
        print(f"  ✅ {tier}: {len(unique)}/{target_count} unique products")
        
        # Small delay between tiers
        await asyncio.sleep(2)
    
    return all_products


def run_scout(topic: str, session_id: str, sb) -> list[dict]:
    """Full scouting phase: Grok search → Supabase insert
    
    Returns list of inserted product dicts with IDs
    """
    print("="*60)
    print(f"🔍 PHASE: Product Scouting — '{topic}'")
    print(f"   Target: {sum(TIER_TARGETS.values())} products")
    print(f"   Distribution: {dict(TIER_TARGETS)}")
    print("="*60)
    
    # Scout via Grok
    products = asyncio.run(scout_all_tiers(topic))
    
    print(f"\n📦 Total scouted: {len(products)}")
    
    # Insert to Supabase
    inserted = []
    for i, p in enumerate(products):
        row = {
            "session_id": session_id,
            "product_name": p.get("product_name", "Unknown"),
            "brand": p.get("brand", "Unknown"),
            "brand_tier": p.get("brand_tier", "unknown"),
            "price": p.get("price"),
            "currency": "KRW",
            "volume": p.get("volume"),
            "review_count": p.get("review_count"),
            "review_rating": p.get("review_rating"),
            "source_platform": p.get("source_platform", "grok"),
            "source_url": p.get("source_url", ""),
            "external_id": f"grok:{uuid.uuid4().hex[:8]}",
            "raw_data": {
                "key_claims": p.get("key_claims", ""),
                "key_ingredients": p.get("key_ingredients", ""),
                "scouted_by": "grok_auto",
            }
        }
        
        try:
            r = sb.table("arpt_products").insert(row).execute()
            pid = r.data[0]["id"]
            row["id"] = pid
            inserted.append(row)
            tier_emoji = {"k-beauty": "🇰🇷", "global": "🌍", "indie": "🔬", "luxury-derma": "💎"}.get(row["brand_tier"], "📦")
            print(f"  [{i+1}/{len(products)}] {tier_emoji} {row['brand']:20s} — {row['product_name'][:45]}")
        except Exception as e:
            print(f"  [{i+1}/{len(products)}] ❌ {row['brand']}: {e}")
    
    # Update session
    tier_counts = {}
    for p in inserted:
        t = p.get("brand_tier", "unknown")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    
    sb.table("arpt_sessions").update({
        "status": "scoring",
        "product_count": len(inserted),
    }).eq("id", session_id).execute()
    
    print(f"\n📊 Inserted: {len(inserted)} products")
    for t, c in tier_counts.items():
        print(f"   {t}: {c}")
    
    return inserted
