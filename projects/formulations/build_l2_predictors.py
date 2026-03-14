"""
L2 Prediction — pH/점도/성상 예측 모델
EVAS 1,254개 제품의 배합비 → 물성 예측
XGBoost for pH/viscosity, RandomForest for appearance classification
"""
import json, pickle, numpy as np
from collections import defaultdict, Counter
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Step 1: 데이터 로드 ───
print("📥 Loading BOM + product metadata...")
all_rows = []
offset = 0
while True:
    r = sb.table('evas_product_compositions').select(
        'product_code, inci_name_en, percentage'
    ).range(offset, offset + 999).execute()
    if not r.data: break
    all_rows.extend(r.data)
    if len(r.data) < 1000: break
    offset += 1000
print(f"  BOM: {len(all_rows)} rows")

all_prods = []
offset = 0
while True:
    r = sb.table('evas_labdoc_products').select(
        'product_code, ph_standard, viscosity_standard, specific_gravity, appearance'
    ).range(offset, offset + 999).execute()
    if not r.data: break
    all_prods.extend(r.data)
    if len(r.data) < 1000: break
    offset += 1000
prod_meta = {p['product_code']: p for p in all_prods}
print(f"  Products: {len(all_prods)}")

# ─── Step 2: Feature matrix ───
print("\n📊 Building feature matrix...")
product_comps = defaultdict(dict)
for row in all_rows:
    inci = row.get('inci_name_en')
    if not inci: continue
    pct = row.get('percentage')
    product_comps[row['product_code']][inci] = float(pct) if pct else 0.0

valid_products = {pc: c for pc, c in product_comps.items() if len(c) >= 5}

inci_usage = Counter()
for c in valid_products.values():
    for i in c: inci_usage[i] += 1
feature_incis = [i for i, c in inci_usage.most_common() if c >= 5]
feature_idx = {i: idx for idx, i in enumerate(feature_incis)}
print(f"  Features: {len(feature_incis)} ingredients")

# ─── Step 3: pH 파싱 ───
def parse_ph(ph_str):
    """'5.50 ± 1.00' → 5.5"""
    if not ph_str or ph_str == 'NONE' or ph_str == 'none':
        return None
    try:
        return float(ph_str.split('±')[0].strip())
    except:
        return None

def parse_viscosity(v_str):
    """'15,000 ± 5,000' → 15000"""
    if not v_str or v_str == 'NONE' or v_str == 'none':
        return None
    try:
        return float(v_str.split('±')[0].strip().replace(',', ''))
    except:
        return None

def classify_appearance(app_str):
    """성상 → 투명/반투명/불투명/크림/기타"""
    if not app_str:
        return None
    app = app_str.lower()
    if '투명' in app and '반투명' not in app and '불투명' not in app:
        return 'transparent'
    elif '반투명' in app:
        return 'translucent'
    elif '크림' in app or '백색' in app:
        return 'cream'
    elif '점액' in app or '젤' in app:
        return 'gel'
    elif '오일' in app or '유상' in app:
        return 'oil'
    elif '펄' in app:
        return 'pearl'
    elif '분말' in app or '파우더' in app:
        return 'powder'
    else:
        return 'other'

# ─── Step 4: 학습 데이터 구성 ───
print("\n🔬 Preparing training data...")

ph_X, ph_y = [], []
visc_X, visc_y = [], []
app_X, app_y = [], []

for pc, comps in valid_products.items():
    meta = prod_meta.get(pc, {})
    
    # Feature vector
    x = np.zeros(len(feature_incis))
    for inci, pct in comps.items():
        if inci in feature_idx:
            x[feature_idx[inci]] = pct
    
    # pH
    ph = parse_ph(meta.get('ph_standard'))
    if ph and 2 <= ph <= 12:
        ph_X.append(x)
        ph_y.append(ph)
    
    # Viscosity
    visc = parse_viscosity(meta.get('viscosity_standard'))
    if visc and visc > 0:
        visc_X.append(x)
        visc_y.append(np.log10(visc))  # log scale for viscosity
    
    # Appearance
    app = classify_appearance(meta.get('appearance'))
    if app:
        app_X.append(x)
        app_y.append(app)

ph_X, ph_y = np.array(ph_X), np.array(ph_y)
visc_X, visc_y = np.array(visc_X), np.array(visc_y)
app_X, app_y = np.array(app_X), np.array(app_y)

print(f"  pH 학습 데이터: {len(ph_y)} samples")
print(f"    범위: {ph_y.min():.1f} ~ {ph_y.max():.1f}, 평균: {ph_y.mean():.2f}")
print(f"  점도 학습 데이터: {len(visc_y)} samples")
print(f"    범위: {10**visc_y.min():.0f} ~ {10**visc_y.max():.0f} cps")
print(f"  성상 학습 데이터: {len(app_y)} samples")
print(f"    분포: {dict(Counter(app_y))}")

# ─── Step 5: 모델 학습 ───
from sklearn.model_selection import cross_val_score, KFold
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score

kf = KFold(n_splits=5, shuffle=True, random_state=42)

# pH 모델
print("\n🧪 Training pH predictor...")
ph_model = GradientBoostingRegressor(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    min_samples_leaf=5, random_state=42
)
ph_scores = cross_val_score(ph_model, ph_X, ph_y, cv=kf, scoring='neg_mean_absolute_error')
print(f"  5-fold MAE: {-ph_scores.mean():.3f} ± {ph_scores.std():.3f}")
ph_model.fit(ph_X, ph_y)

# pH feature importance
ph_importance = sorted(zip(feature_incis, ph_model.feature_importances_),
                       key=lambda x: x[1], reverse=True)[:10]
print(f"  Top features:")
for inci, imp in ph_importance:
    print(f"    {imp:.3f} | {inci}")

# 점도 모델
print("\n🧪 Training viscosity predictor...")
visc_model = GradientBoostingRegressor(
    n_estimators=200, max_depth=5, learning_rate=0.1,
    min_samples_leaf=5, random_state=42
)
visc_scores = cross_val_score(visc_model, visc_X, visc_y, cv=kf, scoring='neg_mean_absolute_error')
print(f"  5-fold MAE (log10): {-visc_scores.mean():.3f} ± {visc_scores.std():.3f}")
print(f"  → 실제 점도 오차: ~{10**(-visc_scores.mean()):.1f}배 범위")
visc_model.fit(visc_X, visc_y)

visc_importance = sorted(zip(feature_incis, visc_model.feature_importances_),
                        key=lambda x: x[1], reverse=True)[:10]
print(f"  Top features:")
for inci, imp in visc_importance:
    print(f"    {imp:.3f} | {inci}")

# 성상 분류
print("\n🧪 Training appearance classifier...")
app_model = RandomForestClassifier(
    n_estimators=200, max_depth=10, min_samples_leaf=3, random_state=42
)
app_scores = cross_val_score(app_model, app_X, app_y, cv=kf, scoring='accuracy')
print(f"  5-fold accuracy: {app_scores.mean():.3f} ± {app_scores.std():.3f}")
app_model.fit(app_X, app_y)

app_importance = sorted(zip(feature_incis, app_model.feature_importances_),
                       key=lambda x: x[1], reverse=True)[:10]
print(f"  Top features:")
for inci, imp in app_importance:
    print(f"    {imp:.3f} | {inci}")

# ─── Step 6: 모델 저장 ───
print("\n💾 Saving models...")
models = {
    'ph_model': ph_model,
    'visc_model': visc_model,
    'app_model': app_model,
    'feature_incis': feature_incis,
    'feature_idx': feature_idx,
    'app_classes': list(app_model.classes_),
    'stats': {
        'ph_mae': round(-ph_scores.mean(), 3),
        'ph_samples': len(ph_y),
        'visc_mae_log': round(-visc_scores.mean(), 3),
        'visc_samples': len(visc_y),
        'app_accuracy': round(app_scores.mean(), 3),
        'app_samples': len(app_y),
    }
}

with open('l2_models.pkl', 'wb') as f:
    pickle.dump(models, f)
print("  Saved to l2_models.pkl")

# ─── Step 7: 테스트 ─── 
print("\n" + "="*60)
print("🧪 TEST: AOSP003 (어성초 캡슐 스크럽 샴푸) 예측")
print("="*60)
aosp003 = valid_products.get('AOSP003', {})
if aosp003:
    x_test = np.zeros(len(feature_incis))
    for inci, pct in aosp003.items():
        if inci in feature_idx:
            x_test[feature_idx[inci]] = pct
    x_test = x_test.reshape(1, -1)
    
    pred_ph = ph_model.predict(x_test)[0]
    pred_visc = 10 ** visc_model.predict(x_test)[0]
    pred_app = app_model.predict(x_test)[0]
    pred_app_proba = dict(zip(app_model.classes_, 
                              [round(p, 3) for p in app_model.predict_proba(x_test)[0]]))
    
    actual = prod_meta.get('AOSP003', {})
    print(f"  pH:  예측 {pred_ph:.2f} | 실제 {actual.get('ph_standard', 'N/A')}")
    print(f"  점도: 예측 {pred_visc:.0f} cps | 실제 {actual.get('viscosity_standard', 'N/A')}")
    print(f"  성상: 예측 {pred_app} | 실제 {actual.get('appearance', 'N/A')}")
    print(f"  성상 확률: {json.dumps(pred_app_proba)}")

# ─── Summary ───
print("\n" + "="*60)
print("📋 L2 PREDICTION MODELS SUMMARY")
print("="*60)
print(f"  pH 모델:    MAE {-ph_scores.mean():.3f} (±{ph_scores.std():.3f}) — {len(ph_y)} samples")
print(f"  점도 모델:  MAE {-visc_scores.mean():.3f} log10 — {len(visc_y)} samples")
print(f"  성상 분류:  Accuracy {app_scores.mean():.1%} — {len(app_y)} samples")
print(f"  Feature 수: {len(feature_incis)}")
print(f"  모델 파일:  l2_models.pkl")
