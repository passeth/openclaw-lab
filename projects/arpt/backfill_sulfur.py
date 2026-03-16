"""INCIDecoder sulfur 키워드 제품 수집 → incidecoder_products DB 업데이트"""
import re
import subprocess
import json
import time
import uuid
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"
VENV_BIN = "/Users/evasfac/.openclaw/workspace/projects/arpt/.venv/bin"

sb = create_client(SUPABASE_URL, SERVICE_KEY)

# 기존 sulfur 관련 slugs
existing_raw = sb.table("incidecoder_products").select("slug").execute().data
existing_slugs = set(p["slug"] for p in existing_raw if p.get("slug"))
print(f"기존 DB 전체: {len(existing_slugs)}건")

# INCIDecoder sulfur 검색 (페이지 순회)
all_slugs = []
for page in range(1, 10):  # 최대 9페이지
    if page == 1:
        url = "https://incidecoder.com/search?query=sulfur&type=product"
    else:
        url = f"https://incidecoder.com/search?query=sulfur&type=product&page={page}"
    
    out = "/tmp/sulfur-search.html"
    result = subprocess.run(
        f'{VENV_BIN}/scrapling extract get "{url}" "{out}" --impersonate chrome',
        shell=True, capture_output=True, timeout=30
    )
    
    try:
        with open(out) as f:
            html = f.read()
    except:
        print(f"페이지 {page}: 파일 없음, 종료")
        break
    
    links = re.findall(r'href="/products/([^"]+)"', html)
    new_links = [s for s in links if s != "create" and s not in all_slugs]
    
    if not new_links:
        print(f"페이지 {page}: 결과 없음 → 종료")
        break
    
    print(f"페이지 {page}: {len(new_links)}개 수집")
    all_slugs.extend(new_links)
    time.sleep(0.5)

# Prequel Redness Reform도 직접 추가
extra = ["prequel-redness-reform-sulfur-cleanser", "prequel-redness-reform-soothing-cleanser"]
for s in extra:
    if s not in all_slugs:
        all_slugs.append(s)

missing = [s for s in all_slugs if s not in existing_slugs]
print(f"\n총 수집: {len(all_slugs)} | 이미 DB: {len(all_slugs)-len(missing)} | 신규: {len(missing)}")

# 신규 제품 스크래핑 → DB 삽입
added, errors = 0, 0
for i, slug in enumerate(missing):
    product_url = f"https://incidecoder.com/products/{slug}"
    out_file = "/tmp/inci-sulfur-product.html"
    
    try:
        subprocess.run(
            f'{VENV_BIN}/scrapling extract get "{product_url}" "{out_file}" --impersonate chrome',
            shell=True, capture_output=True, timeout=30
        )
        with open(out_file) as f:
            html = f.read()
        
        # 제품명
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        product_name = title_match.group(1).strip() if title_match else slug.replace('-', ' ').title()
        
        # 브랜드
        brand_match = re.search(r'href="/brands/([^"]*)"[^>]*>([^<]+)</a>', html)
        brand = brand_match.group(2).strip() if brand_match else ""
        brand_slug_val = brand_match.group(1).strip() if brand_match else ""
        
        # 전성분 (두 가지 패턴 시도)
        ings = re.findall(r'class="ingred-link[^"]*"[^>]*>([^<]+)', html)
        if not ings:
            ings = re.findall(r'"ingredient"[^>]*>([^<]+)<', html)
        
        ingredients_list = ", ".join(i.strip() for i in ings if i.strip()) if ings else ""
        
        if not ingredients_list:
            print(f"  [{i+1}/{len(missing)}] ⚠️ {slug} — 전성분 없음 (404 또는 미수집)")
            errors += 1
            continue
        
        row = {
            "id": str(uuid.uuid4()),
            "brand": brand,
            "brand_slug": brand_slug_val,
            "product_name": product_name,
            "slug": slug,
            "ingredients_list": ingredients_list,
            "source_url": product_url,
        }
        
        sb.table("incidecoder_products").insert(row).execute()
        added += 1
        print(f"  [{i+1}/{len(missing)}] ✅ [{brand}] {product_name[:50]} ({len(ings)}개 성분)")
        time.sleep(0.6)
        
    except Exception as e:
        errors += 1
        print(f"  [{i+1}/{len(missing)}] ❌ {slug}: {e}")

print(f"\n🏁 완료 — 추가: {added}건 | 오류: {errors}건 | 신규 대상: {len(missing)}건")
