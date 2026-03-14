"""
Engine B: 시장 벤치마크 프로파일 구축
incidecoder_composition_inferred (565K행) → 카테고리별 시장 평균 배합
+ EVAS gap 분석 (시장에선 쓰지만 EVAS는 안 쓰는 원료)
"""
import json
import numpy as np
from collections import defaultdict, Counter
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORIES = ['shampoo', 'cream', 'toner', 'serum', 'cleanser', 'sunscreen', 'mask', 'oil']

# ─── Step 1: 시장 데이터 로드 (카테고리별) ───
print("📥 Loading market composition data...")

market_data = defaultdict(list)  # category → [{inci, pct_mid, confidence, product}]
total_loaded = 0

for cat in CATEGORIES:
    print(f"  Loading '{cat}'...")
    offset = 0
    while True:
        r = sb.table('incidecoder_composition_inferred').select(
            'inci_name_en, estimated_pct_mid, confidence, brand, product_name'
        ).eq('product_category', cat).range(offset, offset + 999).execute()
        if not r.data:
            break
        for row in r.data:
            if row.get('inci_name_en') and row.get('estimated_pct_mid'):
                market_data[cat].append(row)
        total_loaded += len(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000
    print(f"    → {len(market_data[cat])} rows")

print(f"  Total loaded: {total_loaded}")

# ─── Step 2: EVAS 원료 세트 로드 ───
print("\n📥 Loading EVAS ingredient set...")
evas_profiles = []
offset = 0
while True:
    r = sb.table('evas_ingredient_profiles').select('inci_name_en, usage_count, avg_pct').range(offset, offset + 999).execute()
    if not r.data: break
    evas_profiles.extend(r.data)
    if len(r.data) < 1000: break
    offset += 1000

evas_ingredients = {p['inci_name_en']: p for p in evas_profiles}
print(f"  EVAS ingredients: {len(evas_ingredients)}")

# ─── Step 3: 카테고리별 시장 프로파일 생성 ───
print("\n📊 Building market profiles per category...")

market_profiles = {}

for cat in CATEGORIES:
    rows = market_data[cat]
    if not rows:
        continue
    
    # 원료별 통계
    inci_stats = defaultdict(lambda: {'pcts': [], 'confidences': [], 'products': set()})
    
    for row in rows:
        inci = row['inci_name_en']
        s = inci_stats[inci]
        try:
            pct = float(row['estimated_pct_mid'])
            if pct > 0:
                s['pcts'].append(pct)
                s['confidences'].append(row.get('confidence', 'low'))
                s['products'].add(f"{row.get('brand', '')}_{row.get('product_name', '')}")
        except (ValueError, TypeError):
            pass
    
    # 프로파일 빌드
    total_products = len(set(f"{r.get('brand', '')}_{r.get('product_name', '')}" for r in rows))
    
    profile_list = []
    for inci, s in inci_stats.items():
        if len(s['pcts']) < 2:  # 2개 미만은 스킵
            continue
        
        pcts = s['pcts']
        conf_dist = Counter(s['confidences'])
        high_conf_pct = conf_dist.get('high', 0) / len(s['confidences']) * 100
        
        # EVAS 비교
        evas_info = evas_ingredients.get(inci)
        in_evas = evas_info is not None
        evas_usage = evas_info['usage_count'] if evas_info else 0
        evas_avg = float(evas_info['avg_pct']) if evas_info and evas_info['avg_pct'] else None
        
        profile_list.append({
            'inci_name_en': inci,
            'product_count': len(s['products']),
            'usage_pct': round(len(s['products']) / total_products * 100, 1),
            'avg_pct': round(np.mean(pcts), 3),
            'median_pct': round(np.median(pcts), 3),
            'max_pct': round(max(pcts), 3),
            'min_pct': round(min(pcts), 3),
            'high_confidence_pct': round(high_conf_pct, 1),
            'in_evas': in_evas,
            'evas_usage': evas_usage,
            'evas_avg_pct': evas_avg,
            'gap_type': 'evas_only' if in_evas and len(s['products']) < 2 
                        else 'market_only' if not in_evas and len(s['products']) >= 3
                        else 'both' if in_evas 
                        else 'rare'
        })
    
    profile_list.sort(key=lambda x: x['product_count'], reverse=True)
    
    market_profiles[cat] = {
        'category': cat,
        'total_products': total_products,
        'total_ingredients': len(profile_list),
        'ingredients': profile_list
    }
    
    # Summary
    market_only = [p for p in profile_list if p['gap_type'] == 'market_only' and p['product_count'] >= 3]
    both = [p for p in profile_list if p['gap_type'] == 'both']
    
    print(f"\n  [{cat.upper()}] {total_products} products, {len(profile_list)} ingredients")
    print(f"    EVAS에도 있는 원료: {len(both)}")
    print(f"    시장에만 있는 원료 (3+제품): {len(market_only)}")
    
    # Top market-only ingredients
    if market_only:
        print(f"    🔵 시장에만 있는 Top 5:")
        for p in sorted(market_only, key=lambda x: x['product_count'], reverse=True)[:5]:
            print(f"      {p['product_count']}개 제품 | avg {p['avg_pct']:.1f}% | {p['inci_name_en'][:50]}")
    
    # 농도 차이 큰 원료 (EVAS vs 시장)
    conc_gaps = [(p, abs(p['avg_pct'] - p['evas_avg_pct']) / max(p['avg_pct'], 0.01)) 
                 for p in profile_list 
                 if p['evas_avg_pct'] and p['avg_pct'] > 0.1 and p['evas_avg_pct'] > 0.01]
    conc_gaps.sort(key=lambda x: x[1], reverse=True)
    if conc_gaps:
        print(f"    📊 EVAS vs 시장 농도 차이 Top 3:")
        for p, ratio in conc_gaps[:3]:
            direction = "↑" if p['avg_pct'] > p['evas_avg_pct'] else "↓"
            print(f"      {p['inci_name_en'][:40]:40s} EVAS {p['evas_avg_pct']:.2f}% vs 시장 {p['avg_pct']:.2f}% {direction}")

# ─── Step 4: Supabase 저장 ───
print("\n💾 Saving market profiles...")

# JSON으로 저장 (Supabase 테이블 생성 필요할 수 있으므로)
with open('engine_b_market_profiles.json', 'w', encoding='utf-8') as f:
    json.dump(market_profiles, f, ensure_ascii=False, indent=2, default=str)
print(f"  Saved to engine_b_market_profiles.json")

# Supabase에도 저장 시도
for cat, profile in market_profiles.items():
    record = {
        'category': cat,
        'total_products': profile['total_products'],
        'total_ingredients': profile['total_ingredients'],
        'top_ingredients': profile['ingredients'][:50],  # 상위 50개만
        'market_only_ingredients': [p for p in profile['ingredients'] 
                                    if p['gap_type'] == 'market_only' and p['product_count'] >= 3][:30],
        'concentration_gaps': [p for p in profile['ingredients']
                              if p.get('evas_avg_pct') and p['avg_pct'] > 0.1 
                              and abs(p['avg_pct'] - p['evas_avg_pct']) / max(p['avg_pct'], 0.01) > 0.5][:20]
    }
    try:
        sb.table('market_category_profiles').upsert(record, on_conflict='category').execute()
    except Exception as e:
        if 'PGRST205' in str(e):
            print(f"  ⚠️ Table 'market_category_profiles' doesn't exist yet. Data saved to JSON only.")
            break

print("\n✅ Engine B market profiles complete!")
