"""
L1 Knowledge Base — Step 2: evas_cooccurrence 생성
원료 쌍별 공출현 빈도 + Jaccard 유사도 + 함께 쓸 때 평균 농도
"""
import json
import time
from collections import defaultdict
from itertools import combinations
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Step 1: 전체 BOM 로드 ───
print("📥 Loading BOM data...")
all_rows = []
offset = 0
batch = 1000
while True:
    r = sb.table('evas_product_compositions').select(
        'product_code, inci_name_en, percentage'
    ).range(offset, offset + batch - 1).execute()
    if not r.data:
        break
    all_rows.extend(r.data)
    if len(r.data) < batch:
        break
    offset += batch
print(f"✅ {len(all_rows)} rows loaded")

# ─── Step 2: 제품별 원료 세트 + 농도 맵 ───
print("📊 Building product-ingredient maps...")
product_ingredients = defaultdict(set)       # product → {inci set}
product_inci_pct = defaultdict(dict)         # product → {inci: pct}

for row in all_rows:
    inci = row.get('inci_name_en')
    if not inci:
        continue
    pc = row['product_code']
    product_ingredients[pc].add(inci)
    pct = row.get('percentage')
    if pct is not None:
        try:
            product_inci_pct[pc][inci] = float(pct)
        except (ValueError, TypeError):
            pass

# 원료별 제품 세트
inci_products = defaultdict(set)
for pc, incis in product_ingredients.items():
    for inci in incis:
        inci_products[inci].add(pc)

# 최소 3회 이상 사용된 원료만 (너무 희귀한 건 의미 없음)
frequent_incis = {inci for inci, prods in inci_products.items() if len(prods) >= 3}
print(f"  3회+ 사용 원료: {len(frequent_incis)} / {len(inci_products)}")

# ─── Step 3: 공출현 계산 ───
print("🔗 Computing co-occurrence pairs...")
t0 = time.time()

# 제품 단위로 순회하면서 쌍 카운트 (combinations 방식이 가장 효율적)
pair_count = defaultdict(int)           # (a, b) → 공출현 횟수
pair_pcts_a = defaultdict(list)         # (a, b) → a의 농도 리스트
pair_pcts_b = defaultdict(list)         # (a, b) → b의 농도 리스트

for pc, incis in product_ingredients.items():
    # 빈도 3회 이상인 원료만 필터
    filtered = sorted(incis & frequent_incis)
    pct_map = product_inci_pct.get(pc, {})
    
    for a, b in combinations(filtered, 2):
        pair_count[(a, b)] += 1
        pct_a = pct_map.get(a)
        pct_b = pct_map.get(b)
        if pct_a is not None and pct_a > 0:
            pair_pcts_a[(a, b)].append(pct_a)
        if pct_b is not None and pct_b > 0:
            pair_pcts_b[(a, b)].append(pct_b)

elapsed = time.time() - t0
print(f"  총 쌍: {len(pair_count):,} ({elapsed:.1f}s)")

# ─── Step 4: Jaccard + 평균 농도 계산 & 필터링 ───
print("📐 Computing Jaccard & filtering...")

records = []
for (a, b), count in pair_count.items():
    a_count = len(inci_products[a])
    b_count = len(inci_products[b])
    union = len(inci_products[a] | inci_products[b])
    jaccard = count / union if union > 0 else 0
    
    # 공출현 2회 이상만 저장 (1회는 우연)
    if count < 2:
        continue
    
    pcts_a = pair_pcts_a.get((a, b), [])
    pcts_b = pair_pcts_b.get((a, b), [])
    
    records.append({
        'inci_a': a,
        'inci_b': b,
        'co_count': count,
        'jaccard': round(jaccard, 4),
        'a_count': a_count,
        'b_count': b_count,
        'avg_pct_when_together_a': round(sum(pcts_a) / len(pcts_a), 4) if pcts_a else None,
        'avg_pct_when_together_b': round(sum(pcts_b) / len(pcts_b), 4) if pcts_b else None,
    })

# Jaccard 높은 순 정렬
records.sort(key=lambda x: x['co_count'], reverse=True)
print(f"  저장할 쌍: {len(records):,}")

# ─── Step 5: 업로드 ───
print("💾 Uploading to Supabase...")
batch_size = 100
uploaded = 0
errors = 0

for i in range(0, len(records), batch_size):
    batch_data = records[i:i+batch_size]
    try:
        sb.table('evas_cooccurrence').upsert(batch_data, on_conflict='inci_a,inci_b').execute()
        uploaded += len(batch_data)
        if uploaded % 5000 == 0:
            print(f"  {uploaded:,}/{len(records):,}...")
    except Exception as e:
        errors += 1
        if errors <= 2:
            print(f"  ❌ Error at batch {i}: {e}")
        if errors >= 5:
            print("  Too many errors. Saving to JSON...")
            with open('l1_cooccurrence.json', 'w') as f:
                json.dump(records, f, ensure_ascii=False, default=str)
            break

print(f"\n✅ Uploaded: {uploaded:,} | Errors: {errors}")

# ─── Summary ───
print("\n" + "="*60)
print("📋 CO-OCCURRENCE SUMMARY")
print("="*60)

# Top 10 highest Jaccard pairs
top_jaccard = sorted(records, key=lambda x: x['jaccard'], reverse=True)
print("\n🔗 Top 10 최강 공출현 쌍 (Jaccard):")
for r in top_jaccard[:10]:
    print(f"  J={r['jaccard']:.3f} | {r['co_count']:4d}회 | {r['inci_a'][:30]} ↔ {r['inci_b'][:30]}")

# Top co-occurrence with Cocamidopropyl Betaine (헤어 관련)
betaine_pairs = [r for r in records if 'Cocamidopropyl Betaine' in (r['inci_a'], r['inci_b'])]
betaine_pairs.sort(key=lambda x: x['co_count'], reverse=True)
print(f"\n🧴 Cocamidopropyl Betaine 공출현 Top 10:")
for r in betaine_pairs[:10]:
    other = r['inci_b'] if r['inci_a'] == 'Cocamidopropyl Betaine' else r['inci_a']
    print(f"  {r['co_count']:4d}회 (J={r['jaccard']:.3f}) | {other}")

# Never-together detection (both frequently used but never co-occurring)
# Find pairs where both are used 50+ times but co_count is very low
print(f"\n⚠️ 자주 쓰지만 같이 안 쓰는 쌍 (각 50+회 사용, 공출현 5회 이하):")
rare_pairs = [r for r in records 
              if r['a_count'] >= 50 and r['b_count'] >= 50 and r['co_count'] <= 5]
rare_pairs.sort(key=lambda x: x['a_count'] + x['b_count'], reverse=True)
for r in rare_pairs[:10]:
    print(f"  {r['co_count']}회/{r['a_count']}+{r['b_count']} | {r['inci_a'][:30]} ↔ {r['inci_b'][:30]}")
