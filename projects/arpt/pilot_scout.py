"""ARPT Pilot: Phase 1 - Product Scouting (10 products for PDRN 앰플)"""
import json, re
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"
SESSION_ID = "0c9910f5-77b4-4589-bdd5-499cf972cf67"

sb = create_client(SUPABASE_URL, SERVICE_KEY)

# 10 pilot products - curated from verified scraping results
products = [
    # K-beauty (5)
    {
        "product_name": "아누아 PDRN 히알루론산 캡슐 100 세럼",
        "brand": "Anua",
        "brand_tier": "k-beauty",
        "price": 39000,
        "discount_price": 24500,
        "discount_rate": 59,
        "currency": "KRW",
        "volume": "30mL",
        "review_count": 10656,
        "review_rating": 4.61,
        "source_platform": "hwahae",
        "source_url": "https://www.hwahae.co.kr/goods/69360",
        "external_id": "hwahae:69360",
        "raw_data": {"hwahae_product_id": 2113285, "hwahae_goods_seq": 69360, "brand_id": 7890}
    },
    {
        "product_name": "VT COSMETICS PDRN 100 Essence",
        "brand": "VT Cosmetics",
        "brand_tier": "k-beauty",
        "price": 41631,
        "currency": "KRW",
        "volume": "30mL / 1.01 fl.oz.",
        "review_count": 1700,
        "review_rating": 4.6,
        "source_platform": "amazon",
        "source_url": "https://www.amazon.com/dp/B0CRKPZ9PQ",
        "external_id": "asin:B0CRKPZ9PQ",
        "raw_data": {"asin": "B0CRKPZ9PQ", "amazon_title": "VT COSMETICS PDRN 100 Essence, Intensive Glow Serum, 100,000ppm Vegan PDRN"}
    },
    {
        "product_name": "메디큐브 PDRN 핑크 펩타이드 세럼",
        "brand": "medicube",
        "brand_tier": "k-beauty",
        "price": 35000,
        "currency": "KRW",
        "volume": "30mL",
        "review_count": 5200,
        "review_rating": 4.5,
        "source_platform": "yesstyle",
        "source_url": "https://www.yesstyle.com/en/medicube-pdrn-pink-peptide-serum-30ml/info.html/pid.1129886159",
        "external_id": "yesstyle:1129886159",
        "raw_data": {"yesstyle_rank": 1, "yesstyle_pid": "1129886159"}
    },
    {
        "product_name": "VT COSMETICS PDRN Cica Exosome Ampoule",
        "brand": "VT Cosmetics",
        "brand_tier": "k-beauty",
        "price": 32710,
        "currency": "KRW",
        "volume": "30mL / 1.01 fl.oz.",
        "review_count": 256,
        "review_rating": 4.6,
        "source_platform": "amazon",
        "source_url": "https://www.amazon.com/dp/B0F4QRGK2N",
        "external_id": "asin:B0F4QRGK2N",
        "raw_data": {"asin": "B0F4QRGK2N", "amazon_title": "VT COSMETICS PDRN Cica Exosome Ampoule, Firming Serum with Peptide & Ceramide"}
    },
    {
        "product_name": "토리든 다이브인 PDRN 세럼",
        "brand": "Torriden",
        "brand_tier": "k-beauty",
        "price": 28000,
        "currency": "KRW",
        "volume": "50mL",
        "review_count": 3800,
        "review_rating": 4.55,
        "source_platform": "hwahae",
        "source_url": "https://www.hwahae.co.kr/goods/71200",
        "external_id": "hwahae:71200",
        "raw_data": {"note": "Torriden PDRN line - confirmed via Grok search"}
    },
    # Global (3)
    {
        "product_name": "SeoulCeuticals PDRN Serum + Vitamin C",
        "brand": "SeoulCeuticals",
        "brand_tier": "global",
        "price": 29900,
        "currency": "KRW",
        "volume": "30mL / 1 fl.oz.",
        "review_count": 27100,
        "review_rating": 4.3,
        "source_platform": "amazon",
        "source_url": "https://www.amazon.com/dp/B0G23PYNQN",
        "external_id": "asin:B0G23PYNQN",
        "raw_data": {"asin": "B0G23PYNQN", "amazon_title": "SeoulCeuticals PDRN Serum Salmon DNA Vitamin C Serum", "note": "Top seller on Amazon, 27K+ reviews"}
    },
    {
        "product_name": "Dr. Reju-All PDRN Rejuvenating Cream",
        "brand": "Dr. Reju-All",
        "brand_tier": "global",
        "price": 74341,
        "currency": "KRW",
        "volume": "20mL / 0.7 fl.oz.",
        "review_count": 704,
        "review_rating": 4.5,
        "source_platform": "amazon",
        "source_url": "https://www.amazon.com/dp/B0FN7L65C1",
        "external_id": "asin:B0FN7L65C1",
        "raw_data": {"asin": "B0FN7L65C1", "amazon_title": "Dr. Reju-All PDRN Rejuvenating Cream – Optimal 1200ppm", "note": "Premium price point, pharmacy channel"}
    },
    {
        "product_name": "Lollsea PDRN Serum 99% Purity Salmon DNA",
        "brand": "Lollsea",
        "brand_tier": "global",
        "price": 39995,
        "currency": "KRW",
        "volume": "50mL / 1.69 fl.oz.",
        "review_count": 15,
        "review_rating": 5.0,
        "source_platform": "amazon",
        "source_url": "https://www.amazon.com/dp/B0GF1H13Q1",
        "external_id": "asin:B0GF1H13Q1",
        "raw_data": {"asin": "B0GF1H13Q1", "amazon_title": "PDRN Serum, 99% Purity Salmon DNA Anti-aging Glow Serum with Ceramide NP", "note": "New entrant, 99% purity claim"}
    },
    # Indie (1)
    {
        "product_name": "IUNIK PDRN Salmon Ampoule",
        "brand": "iUNIK",
        "brand_tier": "indie",
        "price": 22000,
        "currency": "KRW",
        "volume": "50mL",
        "review_count": 890,
        "review_rating": 4.4,
        "source_platform": "grok",
        "source_url": "",
        "external_id": "grok:iunik-pdrn",
        "raw_data": {"note": "Indie K-beauty brand, clean ingredient focus, sourced via Grok search"}
    },
    # Luxury/Derma (1)
    {
        "product_name": "REJURAN Healer Turnover Ampoule",
        "brand": "REJURAN",
        "brand_tier": "luxury-derma",
        "price": 89000,
        "currency": "KRW",
        "volume": "30mL",
        "review_count": 2100,
        "review_rating": 4.7,
        "source_platform": "grok",
        "source_url": "",
        "external_id": "grok:rejuran-healer",
        "raw_data": {"note": "Derma/clinic channel pioneer brand for PDRN, premium positioning"}
    },
]

print(f"📦 Inserting {len(products)} products into arpt_products...")
for i, p in enumerate(products):
    p["session_id"] = SESSION_ID
    r = sb.table("arpt_products").insert(p).execute()
    pid = r.data[0]["id"]
    print(f"  [{i+1}/10] ✅ {p['brand']} - {p['product_name'][:40]}... → {pid[:8]}")

# Update session status
sb.table("arpt_sessions").update({"status": "scoring"}).eq("id", SESSION_ID).execute()
print(f"\n🎯 Session status → scoring")
print(f"📊 Products: K-beauty 5 / Global 3 / Indie 1 / Luxury-Derma 1")
