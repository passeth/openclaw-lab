"""개선 #2: INCIDecoder 전성분 수집 + CIR/CosDNA/CosIng 연동
- INCIDecoder: 글로벌 제품 전성분 크롤링 (Scrapling)
- 화해 __NEXT_DATA__: K-뷰티 전성분
- CIR/CosDNA/CosIng: 핵심 성분 안전성/효능 데이터
"""
import json
import re
import subprocess
import os
from typing import Optional

VENV_BIN = os.path.join(os.path.dirname(__file__), '..', '.venv', 'bin')


def search_incidecoder(product_name: str, brand: str = "") -> Optional[str]:
    """Search INCIDecoder and return the first matching product URL"""
    query = f"{brand} {product_name}" if brand else product_name
    query = re.sub(r'[^\w\s]', '', query).strip()
    words = query.split()[:5]
    search_q = '+'.join(words)
    
    url = f"https://incidecoder.com/search?query={search_q}"
    out_file = "/tmp/arpt-inci-search.html"
    cmd = f'{VENV_BIN}/scrapling extract get "{url}" "{out_file}" --impersonate chrome'
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        with open(out_file, 'r') as f:
            html = f.read()
        links = re.findall(r'href="(/products/[^"]+)"', html)
        # Filter out /products/create
        links = [l for l in links if l != '/products/create']
        if links:
            return f"https://incidecoder.com{links[0]}"
    except Exception as e:
        print(f"    ⚠️ INCIDecoder search error: {e}")
    return None


def fetch_incidecoder_ingredients(product_url: str) -> Optional[str]:
    """Fetch full ingredients list from INCIDecoder product page"""
    out_file = "/tmp/arpt-inci-product.html"
    cmd = f'{VENV_BIN}/scrapling extract get "{product_url}" "{out_file}" --impersonate chrome -s "#ingredlist-short"'
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        with open(out_file, 'r') as f:
            html = f.read()
        # Extract ingredient names from ingred-link spans
        ings = re.findall(r'class="ingred-link[^"]*"[^>]*>([^<]+)', html)
        if ings:
            return ", ".join(ings)
        # Fallback: strip all tags
        text = re.sub(r'<[^>]+>', ' ', html).strip()
        text = re.sub(r'\s+', ' ', text).strip()
        if text and len(text) > 10:
            return text
    except Exception as e:
        print(f"    ⚠️ INCIDecoder fetch error: {e}")
    return None


def fetch_hwahae_ingredients(goods_id: int) -> Optional[str]:
    """Fetch ingredients from 화해 product page via __NEXT_DATA__"""
    url = f"https://www.hwahae.co.kr/goods/{goods_id}?goods_tab=review_ingredients"
    cmd = f'{VENV_BIN}/scrapling extract fetch "{url}" --network-idle --css "script#__NEXT_DATA__"'
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=45)
        text = r.stdout.strip()
        if not text:
            return None
        
        # Parse __NEXT_DATA__ JSON
        data = json.loads(text)
        props = data.get("props", {}).get("pageProps", {})
        
        # Try multiple paths
        ingredients = None
        
        # Path 1: goods detail
        goods = props.get("goods", {})
        if isinstance(goods, dict):
            ingredients = goods.get("ingredients_str") or goods.get("full_ingredients")
        
        # Path 2: ingredient list
        if not ingredients:
            ing_list = props.get("ingredients", [])
            if ing_list:
                ingredients = ", ".join([i.get("name_en") or i.get("name_ko", "") for i in ing_list])
        
        return ingredients if ingredients else None
    except Exception as e:
        print(f"  ⚠️ 화해 ingredients error for goods/{goods_id}: {e}")
    return None


def search_supabase_incidecoder(brand: str, product_name: str, supabase_client) -> Optional[str]:
    """Search our own incidecoder_products table first (34K+ products!)"""
    # Clean search terms
    en_name = re.sub(r'[가-힣ㄱ-ㅎㅏ-ㅣ]+', '', product_name).strip()
    
    # Strategy 1: brand + product name search
    if brand and en_name:
        r = supabase_client.table("incidecoder_products") \
            .select("product_name, ingredients_list, brand") \
            .ilike("brand", f"%{brand}%") \
            .ilike("product_name", f"%{en_name[:30]}%") \
            .limit(3).execute()
        if r.data:
            best = r.data[0]
            ings = best.get("ingredients_list", "")
            if ings and len(ings) > 10:
                print(f"    ✅ Supabase DB: {best['brand']} - {best['product_name'][:40]} ({len(ings)} chars)")
                return ings
    
    # Strategy 2: product name keywords
    keywords = [w for w in en_name.split() if len(w) > 3][:3]
    for kw in keywords:
        r = supabase_client.table("incidecoder_products") \
            .select("product_name, ingredients_list, brand") \
            .ilike("product_name", f"%{kw}%") \
            .ilike("brand", f"%{brand}%") \
            .limit(3).execute()
        if r.data:
            best = r.data[0]
            ings = best.get("ingredients_list", "")
            if ings and len(ings) > 10:
                print(f"    ✅ Supabase DB (keyword '{kw}'): {best['brand']} - {best['product_name'][:40]}")
                return ings
    
    return None


def collect_ingredients_for_product(product: dict, supabase_client=None) -> Optional[str]:
    """Multi-source ingredient collection for a single product
    Priority: 1) Already has → 2) Supabase DB → 3) 화해 → 4) INCIDecoder scrape
    """
    brand = product.get("brand", "")
    name = product.get("product_name", "")
    source = product.get("source_platform", "")
    external_id = product.get("external_id", "")
    
    print(f"  🧪 Collecting ingredients: {brand} - {name[:35]}...")
    
    # Already has ingredients?
    if product.get("full_ingredients"):
        print(f"    ✅ Already has ingredients ({len(product['full_ingredients'])} chars)")
        return product["full_ingredients"]
    
    # Strategy 1: Supabase incidecoder_products (34K+ products, no scraping needed!)
    if supabase_client:
        result = search_supabase_incidecoder(brand, name, supabase_client)
        if result:
            return result
    
    # Strategy 2: 화해 products → 화해 detail page
    if source == "hwahae" and external_id:
        goods_id_match = re.search(r'hwahae:(\d+)', external_id)
        if goods_id_match:
            result = fetch_hwahae_ingredients(int(goods_id_match.group(1)))
            if result:
                print(f"    ✅ 화해: {len(result)} chars")
                return result
    
    # Strategy 3: INCIDecoder scrape (fallback)
    en_name = re.sub(r'[가-힣ㄱ-ㅎㅏ-ㅣ]+', '', name).strip()
    search_term = en_name if en_name else name
    inci_url = search_incidecoder(search_term, brand)
    if inci_url:
        result = fetch_incidecoder_ingredients(inci_url)
        if result:
            print(f"    ✅ INCIDecoder scrape: {len(result)} chars, {result.count(',') + 1} ingredients")
            return result
    
    # Strategy 4: Brand + keyword search on INCIDecoder
    if brand:
        inci_url2 = search_incidecoder(brand + " PDRN")
        if inci_url2 and inci_url2 != inci_url:
            result = fetch_incidecoder_ingredients(inci_url2)
            if result:
                print(f"    ✅ INCIDecoder scrape (brand): {len(result)} chars")
                return result
    
    print(f"    ⚠️ No ingredients found")
    return None


def analyze_key_ingredients(ingredients_str: str) -> dict:
    """Extract and categorize key ingredients from INCI list"""
    if not ingredients_str:
        return {"actives": [], "concerns": [], "base": []}
    
    ingredients = [i.strip() for i in ingredients_str.split(',')]
    
    # Known active ingredients (cosmetics R&D relevant)
    ACTIVES = {
        'niacinamide': 'brightening/barrier',
        'retinol': 'anti-aging/turnover',
        'retinal': 'anti-aging/turnover',
        'ascorbic acid': 'antioxidant/brightening',
        'sodium ascorbyl phosphate': 'vitamin C derivative',
        'hyaluronic acid': 'hydration',
        'sodium hyaluronate': 'hydration',
        'ceramide np': 'barrier repair',
        'ceramide ap': 'barrier repair',
        'ceramide eop': 'barrier repair',
        'salicylic acid': 'exfoliation/anti-acne',
        'glycolic acid': 'exfoliation',
        'lactic acid': 'gentle exfoliation',
        'adenosine': 'anti-wrinkle',
        'peptide': 'anti-aging',
        'acetyl hexapeptide-8': 'anti-aging peptide',
        'palmitoyl tripeptide-1': 'collagen peptide',
        'sodium dna': 'PDRN/repair',
        'polydeoxyribonucleotide': 'PDRN/repair',
        'centella asiatica': 'soothing/cica',
        'madecassoside': 'cica active',
        'asiaticoside': 'cica active',
        'panthenol': 'soothing/hydration',
        'allantoin': 'soothing',
        'alpha-arbutin': 'brightening',
        'tranexamic acid': 'brightening',
        'bakuchiol': 'retinol alternative',
        'squalane': 'emollient/barrier',
        'tocopherol': 'antioxidant',
    }
    
    CONCERNS = {
        'fragrance': 'potential irritant',
        'parfum': 'potential irritant',
        'alcohol denat': 'drying',
        'ethanol': 'drying',
        'ci 77891': 'colorant',
        'benzophenone': 'UV filter concern',
    }
    
    actives = []
    concerns = []
    base = []
    
    for ing in ingredients:
        ing_lower = ing.lower().strip()
        matched = False
        
        for key, role in ACTIVES.items():
            if key in ing_lower:
                actives.append({"name": ing.strip(), "role": role})
                matched = True
                break
        
        if not matched:
            for key, risk in CONCERNS.items():
                if key in ing_lower:
                    concerns.append({"name": ing.strip(), "risk": risk})
                    matched = True
                    break
        
        if not matched:
            base.append(ing.strip())
    
    return {
        "actives": actives,
        "concerns": concerns,
        "base_count": len(base),
        "total_count": len(ingredients)
    }


def collect_all_ingredients(products: list[dict], supabase_client) -> int:
    """Collect ingredients for all products and update Supabase.
    Returns count of successful collections."""
    collected = 0
    for i, p in enumerate(products):
        ingredients = collect_ingredients_for_product(p, supabase_client)
        if ingredients:
            # Update product in Supabase
            analysis = analyze_key_ingredients(ingredients)
            supabase_client.table("arpt_products").update({
                "full_ingredients": ingredients,
                "raw_data": {
                    **(p.get("raw_data") or {}),
                    "ingredient_analysis": analysis
                }
            }).eq("id", p["id"]).execute()
            collected += 1
            p["full_ingredients"] = ingredients  # update in-memory too
    
    print(f"\n📊 Ingredients collected: {collected}/{len(products)}")
    return collected
