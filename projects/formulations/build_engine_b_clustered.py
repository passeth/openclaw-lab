"""
Engine B v2: 시장 제품을 EVAS k=20 클러스터에 매핑
→ 같은 처방 구조 기준으로 EVAS vs 시장 비교
"""
import json
import numpy as np
from collections import defaultdict, Counter
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Step 1: EVAS 클러스터 Centroids 로드 ───
print("📥 Step 1: Loading EVAS cluster centroids...")

with open('/Users/evasfac/.openclaw/workspace/projects/arpt/l1_clusters_k20.json', 'r') as f:
    cluster_data = json.load(f)

# 전체 feature space 구축 (모든 클러스터에 등장하는 원료)
all_ingredients = set()
for cl in cluster_data['results']:
    for item in cl['base_comp']:
        all_ingredients.add(item['inci'])
        
# EVAS BOM에서 전체 원료 리스트 (더 완전한 feature space)
print("  Loading EVAS ingredient universe...")
evas_ingrs = []
offset = 0
while True:
    r = sb.table('evas_ingredient_profiles').select('inci_name_en').range(offset, offset+999).execute()
    if not r.data: break
    evas_ingrs.extend(row['inci_name_en'] for row in r.data)
    if len(r.data) < 1000: break
    offset += 1000
all_ingredients.update(evas_ingrs)

feature_names = sorted(all_ingredients)
feat_idx = {name: i for i, name in enumerate(feature_names)}
n_features = len(feature_names)
print(f"  Feature space: {n_features} ingredients")

# EVAS 원료 프로파일 전체 로드 (Step 4에서 재사용)
print("  Loading EVAS profiles for lookup...")
evas_ingredients_map = {}
offset = 0
while True:
    r = sb.table('evas_ingredient_profiles').select('inci_name_en, usage_count, avg_pct').range(offset, offset+999).execute()
    if not r.data: break
    for row in r.data:
        evas_ingredients_map[row['inci_name_en']] = row
    if len(r.data) < 1000: break
    offset += 1000
print(f"  EVAS profiles loaded: {len(evas_ingredients_map)}")

# Centroid 벡터 생성
centroids = np.zeros((20, n_features))
cluster_meta = {}
for cl in cluster_data['results']:
    cid = cl['cluster_id']
    for item in cl['base_comp']:
        if item['inci'] in feat_idx:
            centroids[cid, feat_idx[item['inci']]] = item['avg_pct']
    cluster_meta[cid] = {
        'count_evas': cl['count'],
        'type': cl['type'],
        'signature': cl['signature'],
    }

# 의미 있는 클러스터만 (5개+ 제품)
significant_clusters = [cid for cid, meta in cluster_meta.items() if meta['count_evas'] >= 5]
print(f"  Significant clusters (5+): {len(significant_clusters)}")
for cid in sorted(significant_clusters):
    m = cluster_meta[cid]
    print(f"    C{cid}: {m['count_evas']:>3}개 | {m['type']} | sig={m['signature'][:30]}")

# ─── Step 2: 시장 제품 로드 + 제품별 조성 벡터 빌드 ───
print("\n📥 Step 2: Loading market product compositions...")

# 제품별로 그룹화
market_products = defaultdict(list)  # product_key → [{inci, pct}]
offset = 0
batch_count = 0

while True:
    r = sb.table('incidecoder_composition_inferred').select(
        'brand, product_name, inci_name_en, estimated_pct_mid, confidence'
    ).range(offset, offset + 999).execute()
    
    if not r.data:
        break
    
    for row in r.data:
        inci = row.get('inci_name_en', '')
        pct = row.get('estimated_pct_mid')
        # 파싱 잔여물 필터링
        if not inci or not pct or 'geeky details' in inci or len(inci) > 100:
            continue
        key = f"{row.get('brand', '')}|||{row.get('product_name', '')}"
        market_products[key].append({
            'inci': inci,
            'pct': float(pct),
            'confidence': row.get('confidence', 'low')
        })
    
    offset += 1000
    batch_count += 1
    if batch_count % 100 == 0:
        print(f"  ... loaded {offset:,} rows, {len(market_products):,} products")

print(f"  Total: {len(market_products):,} products from {offset:,} rows")

# ─── Step 3: 각 시장 제품 → 가장 가까운 EVAS 클러스터 매핑 ───
print("\n📊 Step 3: Mapping market products to EVAS clusters...")

cluster_assignments = defaultdict(list)  # cluster_id → [product compositions]
unmapped = 0

for pkey, ingredients in market_products.items():
    if len(ingredients) < 3:  # 원료 3개 미만이면 스킵
        unmapped += 1
        continue
    
    # 제품 벡터 생성
    vec = np.zeros(n_features)
    for item in ingredients:
        if item['inci'] in feat_idx:
            vec[feat_idx[item['inci']]] = item['pct']
    
    # 코사인 유사도로 가장 가까운 클러스터 찾기
    # (유클리드 거리보다 농도 스케일에 robust)
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        unmapped += 1
        continue
    
    best_cid = -1
    best_sim = -1
    for cid in significant_clusters:
        c_norm = np.linalg.norm(centroids[cid])
        if c_norm == 0:
            continue
        sim = np.dot(vec, centroids[cid]) / (vec_norm * c_norm)
        if sim > best_sim:
            best_sim = sim
            best_cid = cid
    
    if best_cid >= 0 and best_sim > 0.1:  # 최소 유사도 threshold
        brand, pname = pkey.split('|||', 1)
        cluster_assignments[best_cid].append({
            'brand': brand,
            'product_name': pname,
            'ingredients': ingredients,
            'similarity': round(float(best_sim), 4)
        })
    else:
        unmapped += 1

print(f"  Mapped: {sum(len(v) for v in cluster_assignments.values()):,}")
print(f"  Unmapped: {unmapped:,}")

# ─── Step 4: 클러스터별 시장 프로파일 ───
print("\n📊 Step 4: Building cluster-level market profiles...")

engine_b_profiles = {}

for cid in sorted(significant_clusters):
    products = cluster_assignments.get(cid, [])
    if not products:
        continue
    
    meta = cluster_meta[cid]
    
    # 원료별 통계
    inci_stats = defaultdict(lambda: {'pcts': [], 'count': 0})
    for prod in products:
        for item in prod['ingredients']:
            s = inci_stats[item['inci']]
            s['pcts'].append(item['pct'])
            s['count'] += 1
    
    # EVAS 프로파일 로드 (해당 클러스터의 base_comp)
    evas_base = {}
    for cl in cluster_data['results']:
        if cl['cluster_id'] == cid:
            evas_base = {item['inci']: item['avg_pct'] for item in cl['base_comp']}
            break
    
    # 원료 프로파일
    ingr_profiles = []
    for inci, s in inci_stats.items():
        if s['count'] < 2:
            continue
        
        evas_pct = evas_base.get(inci)
        # Supabase 쿼리 대신 미리 로드한 데이터 사용
        evas_info = evas_ingredients_map.get(inci)
        in_evas = evas_info is not None
        evas_usage = evas_info['usage_count'] if evas_info else 0
        
        market_avg = np.mean(s['pcts'])
        
        ingr_profiles.append({
            'inci': inci,
            'market_product_count': s['count'],
            'market_usage_pct': round(s['count'] / len(products) * 100, 1),
            'market_avg_pct': round(float(market_avg), 3),
            'market_median_pct': round(float(np.median(s['pcts'])), 3),
            'in_evas': in_evas,
            'evas_cluster_pct': round(evas_pct, 3) if evas_pct else None,
            'evas_usage_count': evas_usage,
            'gap_type': 'market_only' if not in_evas else 'both',
            'concentration_diff': round(float(market_avg) - evas_pct, 3) if evas_pct else None
        })
    
    ingr_profiles.sort(key=lambda x: x['market_product_count'], reverse=True)
    
    # 시장에만 있는 원료 (확장 기회)
    market_only = [p for p in ingr_profiles if p['gap_type'] == 'market_only' and p['market_product_count'] >= 3]
    # 농도 차이 큰 원료
    conc_diffs = [p for p in ingr_profiles if p['concentration_diff'] is not None and abs(p['concentration_diff']) > 0.5]
    
    profile = {
        'cluster_id': cid,
        'evas_count': meta['count_evas'],
        'market_count': len(products),
        'type': meta['type'],
        'signature': meta['signature'],
        'avg_similarity': round(float(np.mean([p['similarity'] for p in products])), 4),
        'top_ingredients': ingr_profiles[:30],
        'market_only_ingredients': sorted(market_only, key=lambda x: x['market_product_count'], reverse=True)[:20],
        'concentration_gaps': sorted(conc_diffs, key=lambda x: abs(x['concentration_diff']), reverse=True)[:15],
        'sample_products': sorted(products, key=lambda x: x['similarity'], reverse=True)[:5]
    }
    
    engine_b_profiles[cid] = profile
    
    print(f"\n  C{cid}: EVAS {meta['count_evas']}개 ↔ 시장 {len(products)}개 | sim={profile['avg_similarity']:.3f}")
    print(f"    유형: {meta['type']} | sig: {meta['signature'][:30]}")
    if market_only[:3]:
        print(f"    🔵 시장에만 있는 Top 3:")
        for p in market_only[:3]:
            print(f"      {p['market_product_count']}개 | avg {p['market_avg_pct']:.1f}% | {p['inci'][:50]}")
    if conc_diffs[:2]:
        print(f"    📊 농도 차이 Top 2:")
        for p in conc_diffs[:2]:
            d = p['concentration_diff']
            arrow = "시장↑" if d > 0 else "EVAS↑"
            print(f"      {p['inci'][:40]:40s} 차이 {abs(d):.1f}% ({arrow})")

# ─── Step 5: 저장 ───
print("\n\n💾 Saving...")

# JSON
output = {
    'meta': {
        'total_market_products': len(market_products),
        'mapped_products': sum(len(v) for v in cluster_assignments.values()),
        'unmapped_products': unmapped,
        'feature_space': n_features,
        'significant_clusters': len(significant_clusters),
    },
    'profiles': {str(k): v for k, v in engine_b_profiles.items()}
}

with open('/Users/evasfac/.openclaw/workspace/projects/arpt/engine_b_clustered_profiles.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"  → engine_b_clustered_profiles.json")

# Summary
print("\n" + "="*60)
print("📊 ENGINE B SUMMARY")
print("="*60)
mapped = sum(len(v) for v in cluster_assignments.values())
print(f"  시장 제품 총: {len(market_products):,}")
print(f"  매핑 성공: {mapped:,} ({mapped/len(market_products)*100:.1f}%)")
print(f"  매핑 실패: {unmapped:,}")
print(f"  활성 클러스터: {len(engine_b_profiles)}")
for cid, p in sorted(engine_b_profiles.items()):
    mo = len(p['market_only_ingredients'])
    print(f"    C{cid}: EVAS {p['evas_count']}↔시장 {p['market_count']} | 시장에만 있는 원료 {mo}종")

print("\n✅ Engine B (clustered) complete!")
