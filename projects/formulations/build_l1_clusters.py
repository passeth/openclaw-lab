"""
L1 Knowledge Base — Step 3: 제품 클러스터링 + 베이스 포뮬러 추출
1,254개 제품을 배합 패턴으로 그룹핑 → 각 클러스터의 "평균 처방" 추출
"""
import json
import numpy as np
from collections import defaultdict, Counter
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Step 1: BOM + 물성 데이터 로드 ───
print("📥 Loading BOM data...")
all_rows = []
offset = 0
while True:
    r = sb.table('evas_product_compositions').select(
        'product_code, product_category, inci_name_en, percentage'
    ).range(offset, offset + 999).execute()
    if not r.data:
        break
    all_rows.extend(r.data)
    if len(r.data) < 1000:
        break
    offset += 1000
print(f"  BOM: {len(all_rows)} rows")

# 물성 데이터
print("📥 Loading product metadata...")
all_prods = []
offset = 0
while True:
    r = sb.table('evas_labdoc_products').select(
        'product_code, korean_name, appearance, ph_standard, viscosity_standard'
    ).range(offset, offset + 999).execute()
    if not r.data:
        break
    all_prods.extend(r.data)
    if len(r.data) < 1000:
        break
    offset += 1000
prod_meta = {p['product_code']: p for p in all_prods}
print(f"  Products: {len(all_prods)}")

# ─── Step 2: 제품 × 원료 매트릭스 ───
print("\n📊 Building product-ingredient matrix...")
product_comps = defaultdict(dict)  # product → {inci: pct}
product_cats = {}

for row in all_rows:
    inci = row.get('inci_name_en')
    if not inci:
        continue
    pc = row['product_code']
    pct = row.get('percentage')
    if pct is not None:
        try:
            product_comps[pc][inci] = float(pct)
        except (ValueError, TypeError):
            product_comps[pc][inci] = 0.0
    else:
        product_comps[pc][inci] = 0.0
    if row.get('product_category'):
        product_cats[pc] = row['product_category']

# 최소 5개 이상 원료가 있는 제품만
valid_products = {pc: comps for pc, comps in product_comps.items() if len(comps) >= 5}
print(f"  Valid products (5+ ingredients): {len(valid_products)}")

# 10회 이상 사용된 원료만 feature로 (차원 축소)
inci_usage = Counter()
for comps in valid_products.values():
    for inci in comps:
        inci_usage[inci] += 1

feature_incis = [inci for inci, cnt in inci_usage.most_common() if cnt >= 10]
feature_idx = {inci: i for i, inci in enumerate(feature_incis)}
print(f"  Feature ingredients (10+ usage): {len(feature_incis)}")

# 매트릭스 생성
product_list = sorted(valid_products.keys())
matrix = np.zeros((len(product_list), len(feature_incis)))

for i, pc in enumerate(product_list):
    for inci, pct in valid_products[pc].items():
        if inci in feature_idx:
            matrix[i, feature_idx[inci]] = pct

print(f"  Matrix shape: {matrix.shape}")

# ─── Step 3: KMeans 클러스터링 ───
print("\n🔬 Clustering products...")
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# 정규화
scaler = StandardScaler()
matrix_scaled = scaler.fit_transform(matrix)

# 최적 k 탐색 (8~20)
best_k = 12
best_score = -1
for k in range(8, 21):
    km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    labels = km.fit_predict(matrix_scaled)
    score = silhouette_score(matrix_scaled, labels, sample_size=min(5000, len(matrix_scaled)))
    if score > best_score:
        best_score = score
        best_k = k
    print(f"  k={k}: silhouette={score:.3f}")

print(f"\n  ✅ Best k={best_k} (silhouette={best_score:.3f})")

# 최종 클러스터링
km = KMeans(n_clusters=best_k, random_state=42, n_init=10, max_iter=300)
labels = km.fit_predict(matrix_scaled)
distances = km.transform(matrix_scaled)

# ─── Step 4: 클러스터 분석 + 이름 부여 ───
print("\n🏷️ Analyzing clusters...")

base_formulas = []
product_cluster_records = []

for c in range(best_k):
    mask = labels == c
    cluster_indices = np.where(mask)[0]
    cluster_products = [product_list[i] for i in cluster_indices]
    
    # 평균 배합
    cluster_matrix = matrix[mask]
    avg_composition = np.mean(cluster_matrix, axis=0)
    
    # 상위 원료 (평균 % 높은 순)
    top_indices = np.argsort(avg_composition)[::-1]
    base_comp = []
    for idx in top_indices[:20]:
        avg_pct = float(avg_composition[idx])
        if avg_pct < 0.001:
            break
        base_comp.append({
            'inci': feature_incis[idx],
            'avg_pct': round(avg_pct, 3),
            'usage_in_cluster': int(np.sum(cluster_matrix[:, idx] > 0))
        })
    
    # 카테고리 분포
    cats = Counter(product_cats.get(pc, 'unknown') for pc in cluster_products)
    
    # 물성 정보
    phs = []
    viscs = []
    appearances = []
    for pc in cluster_products:
        meta = prod_meta.get(pc, {})
        if meta.get('ph_standard'):
            phs.append(meta['ph_standard'])
        if meta.get('viscosity_standard'):
            viscs.append(meta['viscosity_standard'])
        if meta.get('appearance'):
            appearances.append(meta['appearance'])
    
    # 대표 제품 (중심에 가장 가까운 3개)
    cluster_distances = distances[mask, c]
    closest = np.argsort(cluster_distances)[:3]
    rep_products = []
    for idx in closest:
        pc = cluster_products[idx]
        meta = prod_meta.get(pc, {})
        rep_products.append({
            'product_code': pc,
            'korean_name': meta.get('korean_name', ''),
            'distance': round(float(cluster_distances[idx]), 3)
        })
    
    # 클러스터 이름 자동 추론
    dominant_cat = cats.most_common(1)[0][0] if cats else 'mixed'
    top_inci = base_comp[1]['inci'] if len(base_comp) > 1 else ''  # [0]은 보통 Water
    
    # 이름 생성 로직
    name_parts = []
    if dominant_cat != 'unknown':
        name_parts.append(dominant_cat.upper())
    
    # 핵심 특성 원료로 이름
    surfactants = ['Sodium Laureth Sulfate', 'Ammonium Laureth Sulfate', 'Cocamidopropyl Betaine',
                   'Sodium C14-16 Olefin Sulfonate', 'Myristic Acid']
    emulsifiers = ['Glyceryl Stearate', 'Cetyl Alcohol', 'Stearyl Alcohol', 'PEG-100 Stearate']
    oils = ['White Mineral Oil', 'Dimethicone', 'Hydrogenated Polydecene']
    
    has_surfactant = any(bc['inci'] in surfactants and bc['avg_pct'] > 1 for bc in base_comp)
    has_emulsifier = any(bc['inci'] in emulsifiers and bc['avg_pct'] > 0.5 for bc in base_comp)
    has_oil = any(bc['inci'] in oils and bc['avg_pct'] > 1 for bc in base_comp)
    
    if has_surfactant:
        name_parts.append('세정')
    elif has_emulsifier and has_oil:
        name_parts.append('에멀전')
    elif has_oil:
        name_parts.append('오일')
    else:
        name_parts.append('수용성')
    
    cluster_name = f"C{c}: {' '.join(name_parts)} ({len(cluster_products)})"
    
    print(f"\n  {cluster_name}")
    print(f"    제품 수: {len(cluster_products)}")
    print(f"    카테고리: {dict(cats)}")
    print(f"    대표 원료: {', '.join(bc['inci'][:25] for bc in base_comp[:5])}")
    print(f"    대표 제품: {rep_products[0]['korean_name'] if rep_products else 'N/A'}")
    
    base_formulas.append({
        'cluster_id': c,
        'cluster_name': cluster_name,
        'product_count': len(cluster_products),
        'avg_ingredient_count': round(float(np.mean([len(valid_products[pc]) for pc in cluster_products])), 1),
        'representative_products': rep_products,
        'base_composition': base_comp,
        'ph_range': f"{min(phs)} ~ {max(phs)}" if phs else None,
        'viscosity_range': f"{min(viscs)} ~ {max(viscs)}" if viscs else None,
        'appearance_types': dict(Counter(appearances).most_common(5)) if appearances else None,
        'categories': dict(cats)
    })
    
    for i, pc in enumerate(cluster_products):
        meta = prod_meta.get(pc, {})
        product_cluster_records.append({
            'product_code': pc,
            'cluster_id': c,
            'distance_to_center': round(float(distances[cluster_indices[i], c]), 4),
            'korean_name': meta.get('korean_name', ''),
            'category': product_cats.get(pc, '')
        })

# ─── Step 5: 업로드 ───
print("\n💾 Uploading base formulas...")
for bf in base_formulas:
    sb.table('evas_base_formulas').upsert(bf, on_conflict='cluster_id').execute()
print(f"  ✅ {len(base_formulas)} base formulas uploaded")

print("💾 Uploading product clusters...")
batch_size = 100
uploaded = 0
for i in range(0, len(product_cluster_records), batch_size):
    batch = product_cluster_records[i:i+batch_size]
    sb.table('evas_product_clusters').upsert(batch, on_conflict='product_code').execute()
    uploaded += len(batch)
print(f"  ✅ {uploaded} product-cluster assignments uploaded")

# ─── Final Summary ───
print("\n" + "="*60)
print("📋 CLUSTERING SUMMARY")
print("="*60)
for bf in base_formulas:
    print(f"\n  {bf['cluster_name']}")
    print(f"    제품: {bf['product_count']}개 | 평균 성분: {bf['avg_ingredient_count']}종")
    print(f"    pH: {bf.get('ph_range', 'N/A')} | 점도: {bf.get('viscosity_range', 'N/A')}")
    top3 = bf['base_composition'][:3]
    for t in top3:
        print(f"    → {t['inci'][:35]:35s} avg {t['avg_pct']:>7.2f}%  ({t['usage_in_cluster']}/{bf['product_count']})")
