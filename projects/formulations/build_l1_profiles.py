"""
L1 Knowledge Base — Step 1: evas_ingredient_profiles 생성
39,415행 BOM → 766종 원료 프로파일 집계 → Supabase 저장
"""
import json
import sys
from collections import Counter, defaultdict
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Step 1: 전체 BOM 데이터 로드 (페이지네이션) ───
print("📥 Loading all BOM data...")
all_rows = []
offset = 0
batch = 1000
while True:
    r = sb.table('evas_product_compositions').select(
        'product_code, product_category, inci_name_en, inci_name_kr, percentage, rank'
    ).range(offset, offset + batch - 1).execute()
    if not r.data:
        break
    all_rows.extend(r.data)
    if len(r.data) < batch:
        break
    offset += batch
    if offset % 10000 == 0:
        print(f"  ... {offset} rows loaded")

print(f"✅ Total rows loaded: {len(all_rows)}")

# ─── Step 2: 원료별 통계 집계 ───
print("\n📊 Computing ingredient profiles...")

# 제품별 원료 세트 (공출현 계산용)
product_ingredients = defaultdict(set)
for row in all_rows:
    if row.get('inci_name_en'):
        product_ingredients[row['product_code']].add(row['inci_name_en'])

# 원료별 데이터 수집
ingredient_data = defaultdict(lambda: {
    'percentages': [],
    'products': set(),
    'categories': Counter(),
    'kr_name': None,
    'ranks': []
})

for row in all_rows:
    inci = row.get('inci_name_en')
    if not inci:
        continue
    d = ingredient_data[inci]
    pct = row.get('percentage')
    if pct is not None:
        try:
            pct_f = float(pct)
            d['percentages'].append(pct_f)
        except (ValueError, TypeError):
            pass
    d['products'].add(row['product_code'])
    if row.get('product_category'):
        d['categories'][row['product_category']] += 1
    if row.get('inci_name_kr') and not d['kr_name']:
        d['kr_name'] = row['inci_name_kr']
    if row.get('rank'):
        try:
            d['ranks'].append(int(row['rank']))
        except (ValueError, TypeError):
            pass

total_products = len(product_ingredients)
print(f"  Unique ingredients: {len(ingredient_data)}")
print(f"  Unique products: {total_products}")

# ─── Step 3: 공출현 계산 (Top 10 + Bottom) ───
print("\n🔗 Computing co-occurrence (this may take a moment)...")

# 원료별 제품 세트 (빠른 lookup)
inci_products = {inci: d['products'] for inci, d in ingredient_data.items()}

# 사용 빈도 Top 100 원료에 대해서만 전체 공출현 계산 (766^2는 과함)
sorted_by_usage = sorted(ingredient_data.items(), key=lambda x: len(x[1]['products']), reverse=True)
top_ingredients = [inci for inci, _ in sorted_by_usage[:200]]

cooccurrence = {}
for i, inci_a in enumerate(ingredient_data.keys()):
    prods_a = inci_products[inci_a]
    if len(prods_a) < 2:  # 1회 사용 원료는 스킵
        continue
    scores = []
    for inci_b in top_ingredients:
        if inci_a == inci_b:
            continue
        prods_b = inci_products[inci_b]
        intersection = len(prods_a & prods_b)
        union = len(prods_a | prods_b)
        if union > 0 and intersection > 0:
            jaccard = intersection / union
            scores.append((inci_b, intersection, round(jaccard, 3)))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    cooccurrence[inci_a] = {
        'top_5': [(s[0], s[1]) for s in scores[:5]],
        'never_with_count': sum(1 for s in scores if s[1] == 0)
    }

print(f"  Co-occurrence computed for {len(cooccurrence)} ingredients")

# ─── Step 4: 프로파일 빌드 ───
print("\n🏗️ Building profiles...")

profiles = []
for inci, d in ingredient_data.items():
    pcts = d['percentages']
    pcts_nonzero = [p for p in pcts if p > 0]
    
    top_cooc = cooccurrence.get(inci, {}).get('top_5', [])
    
    profile = {
        'inci_name_en': inci,
        'inci_name_kr': d['kr_name'],
        'usage_count': len(d['products']),
        'usage_pct': round(len(d['products']) / total_products * 100, 1),
        'avg_pct': round(sum(pcts_nonzero) / len(pcts_nonzero), 4) if pcts_nonzero else None,
        'max_pct': round(max(pcts_nonzero), 4) if pcts_nonzero else None,
        'min_pct': round(min(pcts_nonzero), 4) if pcts_nonzero else None,
        'median_pct': round(sorted(pcts_nonzero)[len(pcts_nonzero)//2], 4) if pcts_nonzero else None,
        'avg_rank': round(sum(d['ranks']) / len(d['ranks']), 1) if d['ranks'] else None,
        'categories': dict(d['categories']) if d['categories'] else None,
        'top_cooccurrence': [{'inci': c[0], 'count': c[1]} for c in top_cooc] if top_cooc else None,
        'product_codes': list(d['products'])
    }
    profiles.append(profile)

profiles.sort(key=lambda x: x['usage_count'], reverse=True)
print(f"  Total profiles: {len(profiles)}")

# ─── Step 5: Supabase 테이블 생성 (via REST — 테이블이 없으면 만들기) ───
print("\n💾 Uploading to Supabase...")

# 먼저 기존 테이블 확인/삭제
try:
    existing = sb.table('evas_ingredient_profiles').select('inci_name_en', count='exact').limit(0).execute()
    if existing.count and existing.count > 0:
        print(f"  Existing table found with {existing.count} rows. Clearing...")
        # 전체 삭제
        sb.table('evas_ingredient_profiles').delete().neq('inci_name_en', '___impossible___').execute()
        print("  Cleared.")
except Exception as e:
    print(f"  Table doesn't exist yet or error: {e}")
    print("  Will need to create table via SQL. Creating via insert (auto-create if RLS allows)...")

# 배치 업로드
batch_size = 50
uploaded = 0
errors = 0
for i in range(0, len(profiles), batch_size):
    batch_data = profiles[i:i+batch_size]
    # product_codes를 JSON 문자열로 (너무 길 수 있으므로 제한)
    for p in batch_data:
        if p['product_codes'] and len(p['product_codes']) > 50:
            p['product_codes'] = p['product_codes'][:50]  # 상위 50개만
    try:
        sb.table('evas_ingredient_profiles').upsert(batch_data, on_conflict='inci_name_en').execute()
        uploaded += len(batch_data)
    except Exception as e:
        errors += 1
        if errors == 1:
            print(f"  ❌ Upload error (batch {i}): {e}")
            print(f"  Sample row: {json.dumps(batch_data[0], ensure_ascii=False, default=str)[:300]}")
        if errors >= 3:
            print("  Too many errors. Table might not exist. Need SQL creation first.")
            break

if errors == 0:
    print(f"\n✅ Successfully uploaded {uploaded} ingredient profiles!")
else:
    print(f"\n⚠️ Upload had {errors} errors. {uploaded} profiles uploaded.")
    print("  → Table needs to be created via SQL first. Dumping profiles to JSON...")
    with open('l1_ingredient_profiles.json', 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2, default=str)
    print(f"  → Saved to l1_ingredient_profiles.json ({len(profiles)} profiles)")

# ─── Summary ───
print("\n" + "="*60)
print("📋 L1 INGREDIENT PROFILES SUMMARY")
print("="*60)
print(f"  총 원료: {len(profiles)}")
print(f"  총 제품: {total_products}")
print(f"  총 BOM 행: {len(all_rows)}")
print(f"\n  Top 10 원료 (사용 빈도):")
for p in profiles[:10]:
    print(f"    {p['usage_count']:4d}회 ({p['usage_pct']:5.1f}%) | avg {str(p['avg_pct']):>8}% | {p['inci_name_en']}")
print(f"\n  카테고리별 제품 수:")
all_cats = Counter()
for p in profiles:
    if p['categories']:
        for cat, cnt in p['categories'].items():
            pass
# recount from product level
prod_cat_map = {}
for row in all_rows:
    if row.get('product_category') and row['product_code'] not in prod_cat_map:
        prod_cat_map[row['product_code']] = row['product_category']
cat_counts = Counter(prod_cat_map.values())
for cat, cnt in cat_counts.most_common():
    print(f"    {cat}: {cnt}")
print(f"    (미분류): {total_products - len(prod_cat_map)}")
