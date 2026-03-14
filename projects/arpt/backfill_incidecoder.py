"""Backfill incidecoder_products with PDRN products not yet in DB"""
import re
import subprocess
import json
import time
import uuid
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"
VENV_BIN = ".venv/bin"

sb = create_client(SUPABASE_URL, SERVICE_KEY)

# Get existing slugs
existing = sb.table("incidecoder_products").select("slug").ilike("slug", "%pdrn%").execute().data
existing2 = sb.table("incidecoder_products").select("slug").ilike("product_name", "%pdrn%").execute().data
existing_slugs = set(p["slug"] for p in (existing + existing2) if p.get("slug"))

# All PDRN URLs from INCIDecoder search
all_slugs = []
for q in ['PDRN+serum', 'PDRN+ampoule', 'PDRN+essence', 'salmon+DNA+serum', 'Torriden+PDRN', 'PDRN+cream']:
    url = f"https://incidecoder.com/search?query={q}"
    out = "/tmp/arpt-bulk-search.html"
    subprocess.run(f'{VENV_BIN}/scrapling extract get "{url}" "{out}" --impersonate chrome',
                   shell=True, capture_output=True, timeout=30)
    with open(out) as f:
        html = f.read()
    links = re.findall(r'href="/products/([^"]+)"', html)
    for slug in links:
        if slug != "create" and slug not in all_slugs:
            all_slugs.append(slug)

# Filter to not-in-DB
missing = [s for s in all_slugs if s not in existing_slugs]
print(f"📊 Total: {len(all_slugs)} | In DB: {len(existing_slugs)} | Missing: {len(missing)}")

# Scrape and insert missing products
added = 0
errors = 0
for i, slug in enumerate(missing):
    product_url = f"https://incidecoder.com/products/{slug}"
    out_file = "/tmp/arpt-inci-backfill.html"
    
    try:
        # Fetch product page
        cmd = f'{VENV_BIN}/scrapling extract get "{product_url}" "{out_file}" --impersonate chrome'
        subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        
        with open(out_file) as f:
            html = f.read()
        
        # Extract product name
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        product_name = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()
        
        # Extract brand
        brand_match = re.search(r'<a[^>]*href="/brands/[^"]*"[^>]*>([^<]+)</a>', html)
        brand = brand_match.group(1).strip() if brand_match else ""
        brand_slug = brand.lower().replace(' ', '-') if brand else ""
        
        # Extract ingredients
        ings_cmd = f'{VENV_BIN}/scrapling extract get "{product_url}" "{out_file}" --impersonate chrome -s "#ingredlist-short"'
        subprocess.run(ings_cmd, shell=True, capture_output=True, timeout=30)
        with open(out_file) as f:
            ings_html = f.read()
        ings = re.findall(r'class="ingred-link[^"]*"[^>]*>([^<]+)', ings_html)
        ingredients_list = ", ".join(ings) if ings else ""
        
        if not ingredients_list:
            print(f"  [{i+1}/{len(missing)}] ⚠️ {slug} — no ingredients")
            errors += 1
            continue
        
        # Insert to DB
        row = {
            "id": str(uuid.uuid4()),
            "brand": brand,
            "brand_slug": brand_slug,
            "product_name": product_name,
            "slug": slug,
            "ingredients_list": ingredients_list,
            "source_url": product_url,
        }
        
        sb.table("incidecoder_products").insert(row).execute()
        added += 1
        print(f"  [{i+1}/{len(missing)}] ✅ {brand} — {product_name[:40]} ({len(ings)} ingredients)")
        
        time.sleep(0.5)  # Rate limit
        
    except Exception as e:
        errors += 1
        print(f"  [{i+1}/{len(missing)}] ❌ {slug}: {e}")

print(f"\n📊 Results: Added {added} | Errors {errors} | Total missing was {len(missing)}")
