"""
EVAS Formulation Intelligence Engine — L1+L2+L3 통합
처방 요청 → 유사 레시피 검색 → 초안 생성 → 물성 예측 → 4축 검증 → 최적화

사용법:
  python formulation_engine.py "투명 SF 어성초 샴푸"
  python formulation_engine.py --test  (AOSP003 기반 테스트)
"""
import json, pickle, sys, os
import numpy as np
from collections import defaultdict, Counter
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── L2 모델 로드 ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARPT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'arpt')
MODEL_PATH = os.path.join(ARPT_DIR, 'l2_models.pkl')
with open(MODEL_PATH, 'rb') as f:
    l2 = pickle.load(f)

ph_model = l2['ph_model']
visc_model = l2['visc_model']
app_model = l2['app_model']
feature_incis = l2['feature_incis']
feature_idx = l2['feature_idx']

# ─── Engine B: 시장 프로파일 로드 ───
ENGINE_B_PATH = os.path.join(ARPT_DIR, 'engine_b_clustered_profiles.json')
engine_b_data = None
if os.path.exists(ENGINE_B_PATH):
    with open(ENGINE_B_PATH, 'r', encoding='utf-8') as f:
        engine_b_data = json.load(f)

# ─── 클러스터 centroids 로드 (시장 매핑용) ───
CLUSTER_PATH = os.path.join(ARPT_DIR, 'l1_clusters_k20.json')
cluster_centroids = None
if os.path.exists(CLUSTER_PATH):
    with open(CLUSTER_PATH, 'r', encoding='utf-8') as f:
        _cdata = json.load(f)
    # centroid 벡터 준비
    _all_incis = set()
    for cl in _cdata['results']:
        for item in cl['base_comp']:
            _all_incis.add(item['inci'])
    _centroid_incis = sorted(_all_incis)
    _centroid_idx = {name: i for i, name in enumerate(_centroid_incis)}
    _n_feat = len(_centroid_incis)
    
    cluster_centroids = {
        'centroids': {},
        'feat_idx': _centroid_idx,
        'n_feat': _n_feat,
        'meta': {}
    }
    for cl in _cdata['results']:
        cid = cl['cluster_id']
        vec = np.zeros(_n_feat)
        for item in cl['base_comp']:
            if item['inci'] in _centroid_idx:
                vec[_centroid_idx[item['inci']]] = item['avg_pct']
        cluster_centroids['centroids'][cid] = vec
        cluster_centroids['meta'][cid] = {
            'count': cl['count'],
            'type': cl['type'],
            'signature': cl['signature'],
            'name': cl.get('cluster_name', f"C{cid}")
        }


# ═══════════════════════════════════════════════════════════
# AGENT 1: RETRIEVER — L1에서 관련 데이터 검색
# ═══════════════════════════════════════════════════════════

def retrieve(keywords: list[str], category: str = None, constraints: dict = None):
    """
    L1 Knowledge Base에서 관련 정보 검색
    Returns: similar_products, ingredient_profiles, cluster_info, cooccurrence_warnings
    """
    result = {
        'similar_products': [],
        'ingredient_profiles': {},
        'cluster_info': None,
        'cooccurrence_data': {},
    }
    
    # 1. 키워드 원료의 프로파일 조회
    print("  🔍 [Retriever] 원료 프로파일 조회...")
    for kw in keywords:
        profiles = sb.table('evas_ingredient_profiles').select('*').ilike('inci_name_en', f'%{kw}%').execute().data
        if not profiles:
            profiles = sb.table('evas_ingredient_profiles').select('*').ilike('inci_name_kr', f'%{kw}%').execute().data
        for p in profiles:
            result['ingredient_profiles'][p['inci_name_en']] = p
    
    print(f"    → {len(result['ingredient_profiles'])}개 원료 프로파일 발견")
    
    # 2. 카테고리 기반 클러스터 조회
    if category:
        print(f"  🔍 [Retriever] '{category}' 클러스터 검색...")
        clusters = sb.table('evas_base_formulas').select('*').execute().data
        for cl in clusters:
            cats = cl.get('categories', {})
            if category in cats:
                if not result['cluster_info'] or cats.get(category, 0) > result['cluster_info'].get('categories', {}).get(category, 0):
                    result['cluster_info'] = cl
        if result['cluster_info']:
            print(f"    → 클러스터: {result['cluster_info']['cluster_name']}")
    
    # 3. 키워드 원료가 포함된 EVAS 제품 검색
    print("  🔍 [Retriever] 유사 EVAS 제품 검색...")
    if keywords:
        main_kw = keywords[0]
        # Search in compositions
        matches = sb.table('evas_product_compositions').select(
            'product_code, inci_name_en, percentage'
        ).ilike('inci_name_en', f'%{main_kw}%').execute().data
        
        if not matches:
            matches = sb.table('evas_product_compositions').select(
                'product_code, inci_name_en, percentage'
            ).ilike('inci_name_kr', f'%{main_kw}%').execute().data
        
        product_codes = list(set(m['product_code'] for m in matches))[:10]
        
        for pc in product_codes:
            prod = sb.table('evas_labdoc_products').select(
                'product_code, korean_name, appearance, ph_standard, viscosity_standard'
            ).eq('product_code', pc).execute().data
            if prod:
                # Get full composition
                comp = sb.table('evas_product_compositions').select(
                    'inci_name_en, inci_name_kr, percentage, rank'
                ).eq('product_code', pc).order('rank').execute().data
                result['similar_products'].append({
                    'meta': prod[0],
                    'composition': comp
                })
        
        print(f"    → {len(result['similar_products'])}개 유사 제품 발견")
    
    # 4. 핵심 원료의 공출현 데이터
    print("  🔍 [Retriever] 공출현 데이터 조회...")
    for inci in list(result['ingredient_profiles'].keys())[:5]:
        cooc = sb.table('evas_cooccurrence').select(
            'inci_a, inci_b, co_count, jaccard'
        ).or_(f'inci_a.eq.{inci},inci_b.eq.{inci}').order('co_count', desc=True).limit(10).execute().data
        if cooc:
            result['cooccurrence_data'][inci] = cooc
    
    return result


# ═══════════════════════════════════════════════════════════
# AGENT 2: PREDICTOR — L2 물성 예측
# ═══════════════════════════════════════════════════════════

def predict_properties(composition: list[dict]):
    """
    배합 리스트 → pH, 점도, 성상 예측
    composition: [{'inci': 'Water', 'pct': 75.0}, ...]
    """
    x = np.zeros(len(feature_incis))
    for item in composition:
        inci = item['inci']
        if inci in feature_idx:
            x[feature_idx[inci]] = item['pct']
    
    x = x.reshape(1, -1)
    
    pred_ph = float(ph_model.predict(x)[0])
    pred_visc = float(10 ** visc_model.predict(x)[0])
    pred_app = app_model.predict(x)[0]
    pred_app_proba = dict(zip(
        [str(c) for c in app_model.classes_],
        [round(float(p), 3) for p in app_model.predict_proba(x)[0]]
    ))
    
    return {
        'ph': round(pred_ph, 2),
        'viscosity_cps': round(pred_visc, 0),
        'appearance': str(pred_app),
        'appearance_proba': pred_app_proba
    }


# ═══════════════════════════════════════════════════════════
# AGENT 3: CRITIC — 4축 검증
# ═══════════════════════════════════════════════════════════

def critique(composition: list[dict], predictions: dict, 
             retrieved: dict, constraints: dict = None):
    """
    4축 검증:
    1. 원료 EVAS 검증도
    2. 비호환성 체크
    3. 안전 농도 범위
    4. 예측 물성 vs 목표
    """
    constraints = constraints or {}
    issues = []
    warnings = []
    passes = []
    
    # ─── Axis 1: 원료 검증도 ───
    print("  ✓ [Critic] Axis 1: 원료 EVAS 검증도...")
    verified = 0
    limited = 0
    novel = 0
    novel_list = []
    
    for item in composition:
        inci = item['inci']
        profile = retrieved['ingredient_profiles'].get(inci)
        
        if not profile:
            # DB에서 직접 조회
            p = sb.table('evas_ingredient_profiles').select('usage_count, avg_pct, max_pct').eq('inci_name_en', inci).execute().data
            if p:
                profile = p[0]
        
        if profile:
            usage = profile.get('usage_count', 0)
            max_pct = profile.get('max_pct')
            
            if usage >= 10:
                verified += 1
                # 최대 사용 농도 초과 체크
                if max_pct and item['pct'] > float(max_pct) * 1.5:
                    warnings.append(f"⚠️ {inci}: {item['pct']}% 제안 — EVAS 최대 {max_pct}%의 {item['pct']/float(max_pct):.1f}배")
            elif usage >= 3:
                limited += 1
                warnings.append(f"⚠️ {inci}: EVAS {usage}회만 사용 (제한적 검증)")
            else:
                novel += 1
                novel_list.append(inci)
        else:
            novel += 1
            novel_list.append(inci)
    
    total = verified + limited + novel
    verified_pct = verified / total * 100 if total > 0 else 0
    
    if verified_pct >= 80:
        passes.append(f"✅ Axis 1: 원료 검증도 {verified_pct:.0f}% ({verified}✅ {limited}⚠️ {novel}🚨)")
    elif verified_pct >= 60:
        warnings.append(f"⚠️ Axis 1: 원료 검증도 {verified_pct:.0f}% — 신규 원료 다수")
    else:
        issues.append(f"❌ Axis 1: 원료 검증도 {verified_pct:.0f}% — EVAS 미검증 원료 과다")
    
    if novel_list:
        issues.append(f"🚨 EVAS 미검증 원료: {', '.join(novel_list[:5])}")
    
    # ─── Axis 2: 비호환성 ───
    print("  ✓ [Critic] Axis 2: 비호환성 체크...")
    inci_names = [item['inci'] for item in composition]
    
    # cosing incompatibility는 substance_id 기반 — 주요 원료만 체크
    for item in composition[:15]:  # 상위 15개만
        subs = sb.table('cosing_substances').select('substance_id').ilike('inci_name', item['inci']).limit(1).execute().data
        if subs:
            sid = subs[0]['substance_id']
            incompat = sb.table('cosing_function_contexts').select('incompatibility').eq('substance_id', sid).not_.is_('incompatibility', 'null').limit(1).execute().data
            if incompat and incompat[0].get('incompatibility'):
                inc_text = incompat[0]['incompatibility'][:120]
                warnings.append(f"⚠️ {item['inci']}: {inc_text}")
    
    # 공출현 0회 쌍 체크 (상위 10개 원료만, 단순명만)
    top_items = [item for item in composition if item['pct'] > 0.1][:10]
    for i, item_a in enumerate(top_items):
        for item_b in top_items[i+1:]:
            a_name = item_a['inci']
            b_name = item_b['inci']
            # 특수문자 있는 원료명은 스킵 (PostgREST 파싱 이슈)
            if any(c in a_name + b_name for c in '().,/'):
                continue
            try:
                cooc = sb.table('evas_cooccurrence').select('co_count').or_(
                    f'and(inci_a.eq.{a_name},inci_b.eq.{b_name}),'
                    f'and(inci_a.eq.{b_name},inci_b.eq.{a_name})'
                ).execute().data
                if cooc and cooc[0]['co_count'] == 0:
                    warnings.append(f"⚠️ {a_name} + {b_name}: EVAS에서 공출현 0회")
            except Exception:
                pass  # 쿼리 실패 시 스킵
    
    incompat_warnings = [w for w in warnings if '공출현 0회' in w or '⚠️' in w]
    if not incompat_warnings:
        passes.append("✅ Axis 2: 비호환성 경고 없음")
    
    # ─── Axis 3: 안전 농도 ───
    print("  ✓ [Critic] Axis 3: 안전 농도 범위...")
    safety_ok = True
    for item in composition:
        safety = sb.table('incidecoder_research_ingredient_safety_v2').select(
            'max_conc_face, max_conc_body, irritation_risk'
        ).eq('inci_name', item['inci']).execute().data
        if safety:
            s = safety[0]
            # 간단한 체크 (body 기준)
            max_body = s.get('max_conc_body')
            if max_body:
                try:
                    max_val = float(str(max_body).replace('%', '').strip())
                    if item['pct'] > max_val:
                        issues.append(f"❌ {item['inci']}: {item['pct']}% > 안전 한계 {max_val}%")
                        safety_ok = False
                except (ValueError, TypeError):
                    pass
    
    if safety_ok:
        passes.append("✅ Axis 3: 전 원료 안전 범위 내")
    
    # ─── Axis 4: 물성 예측 vs 목표 ───
    print("  ✓ [Critic] Axis 4: 예측 물성 vs 목표...")
    target_ph = constraints.get('target_ph')
    target_visc = constraints.get('target_viscosity')
    target_transparent = constraints.get('transparent', False)
    
    if target_ph:
        ph_diff = abs(predictions['ph'] - target_ph)
        if ph_diff <= 0.5:
            passes.append(f"✅ Axis 4a: pH {predictions['ph']} (목표 {target_ph}, 차이 {ph_diff:.2f})")
        else:
            issues.append(f"❌ Axis 4a: pH {predictions['ph']} — 목표 {target_ph}에서 {ph_diff:.1f} 벗어남")
    
    if target_visc:
        visc_ratio = predictions['viscosity_cps'] / target_visc
        if 0.5 <= visc_ratio <= 2.0:
            passes.append(f"✅ Axis 4b: 점도 {predictions['viscosity_cps']:.0f} cps (목표 {target_visc})")
        else:
            issues.append(f"❌ Axis 4b: 점도 {predictions['viscosity_cps']:.0f} cps — 목표 {target_visc}의 {visc_ratio:.1f}배")
    
    if target_transparent:
        trans_prob = predictions['appearance_proba'].get('transparent', 0)
        if trans_prob >= 0.5:
            passes.append(f"✅ Axis 4c: 투명 확률 {trans_prob:.0%}")
        elif trans_prob >= 0.3:
            warnings.append(f"⚠️ Axis 4c: 투명 확률 {trans_prob:.0%} — 리스크 있음")
        else:
            issues.append(f"❌ Axis 4c: 투명 확률 {trans_prob:.0%} — 투명 달성 어려움")
    
    # ─── 신뢰도 점수 ───
    score = 100
    score -= len(issues) * 15
    score -= len(warnings) * 5
    score = max(0, min(100, score))
    
    return {
        'score': score,
        'passes': passes,
        'warnings': warnings,
        'issues': issues,
        'axis_results': {
            'ingredient_verification': f"{verified_pct:.0f}% ({verified}/{total})",
            'novel_ingredients': novel_list,
            'incompatibility_warnings': len([w for w in warnings if '비호환' in w or '공출현' in w]),
            'safety_violations': len([i for i in issues if '안전 한계' in i]),
        }
    }


# ═══════════════════════════════════════════════════════════
# ENGINE B: 시장 확장 분석
# ═══════════════════════════════════════════════════════════

def market_expansion(composition: list[dict], constraints: dict = None):
    """
    처방을 가장 가까운 EVAS 클러스터에 매핑 → 해당 클러스터의 시장 데이터와 비교
    Returns: cluster_id, market_only ingredients, concentration gaps, expansion suggestions
    """
    if not engine_b_data or not cluster_centroids:
        return None
    
    constraints = constraints or {}
    
    # 1. 처방 → 클러스터 매핑
    vec = np.zeros(cluster_centroids['n_feat'])
    for item in composition:
        if item['inci'] in cluster_centroids['feat_idx']:
            vec[cluster_centroids['feat_idx'][item['inci']]] = item['pct']
    
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        return None
    
    best_cid = -1
    best_sim = -1
    for cid, centroid in cluster_centroids['centroids'].items():
        c_norm = np.linalg.norm(centroid)
        if c_norm == 0:
            continue
        sim = np.dot(vec, centroid) / (vec_norm * c_norm)
        if sim > best_sim:
            best_sim = sim
            best_cid = cid
    
    if best_cid < 0:
        return None
    
    meta = cluster_centroids['meta'].get(best_cid, {})
    profile = engine_b_data.get('profiles', {}).get(str(best_cid))
    
    if not profile:
        return {
            'cluster_id': best_cid,
            'cluster_name': meta.get('name', f'C{best_cid}'),
            'similarity': round(float(best_sim), 4),
            'market_count': 0,
            'market_only': [],
            'concentration_gaps': [],
            'expansion_suggestions': []
        }
    
    # 2. 현재 처방에 없는 시장 인기 원료 찾기
    current_incis = {item['inci'] for item in composition}
    
    market_only = []
    for ingr in profile.get('market_only_ingredients', []):
        if ingr['inci'] not in current_incis and ingr['market_product_count'] >= 3:
            market_only.append(ingr)
    
    # 3. 농도 차이 분석 (현재 처방 vs 시장 평균)
    concentration_gaps = []
    for ingr in profile.get('top_ingredients', []):
        if ingr['inci'] in current_incis:
            current_pct = next((i['pct'] for i in composition if i['inci'] == ingr['inci']), 0)
            market_avg = ingr['market_avg_pct']
            if current_pct > 0 and market_avg > 0:
                diff = market_avg - current_pct
                ratio = market_avg / current_pct if current_pct > 0.01 else 999
                if abs(diff) > 0.3 and (ratio > 1.5 or ratio < 0.67):
                    concentration_gaps.append({
                        'inci': ingr['inci'],
                        'current_pct': round(current_pct, 3),
                        'market_avg_pct': round(market_avg, 3),
                        'diff': round(diff, 3),
                        'direction': '시장↑' if diff > 0 else '현재↑',
                        'market_product_count': ingr['market_product_count']
                    })
    
    concentration_gaps.sort(key=lambda x: abs(x['diff']), reverse=True)
    
    # 4. 확장 제안 생성
    suggestions = []
    for ingr in market_only[:5]:
        suggestions.append(
            f"🔵 {ingr['inci']}: 시장 {ingr['market_product_count']}개 제품에서 사용 "
            f"(avg {ingr['market_avg_pct']:.1f}%) — EVAS 미사용이지만 시장 표준"
        )
    
    for gap in concentration_gaps[:3]:
        if gap['direction'] == '시장↑':
            suggestions.append(
                f"📊 {gap['inci']}: 현재 {gap['current_pct']:.1f}% → "
                f"시장 평균 {gap['market_avg_pct']:.1f}% (시장이 {abs(gap['diff']):.1f}% 더 사용)"
            )
    
    return {
        'cluster_id': best_cid,
        'cluster_name': meta.get('name', f'C{best_cid}'),
        'cluster_type': meta.get('type', ''),
        'similarity': round(float(best_sim), 4),
        'evas_count': profile.get('evas_count', 0),
        'market_count': profile.get('market_count', 0),
        'market_only': market_only[:10],
        'concentration_gaps': concentration_gaps[:10],
        'expansion_suggestions': suggestions,
    }


# ═══════════════════════════════════════════════════════════
# AGENT 4: OPTIMIZER — 검증 실패 시 수정 제안
# ═══════════════════════════════════════════════════════════

def optimize(composition: list[dict], critique_result: dict, 
             predictions: dict, constraints: dict = None):
    """
    Critic 결과 기반 자동 수정 제안
    """
    constraints = constraints or {}
    suggestions = []
    modified = [dict(item) for item in composition]  # deep copy
    
    for issue in critique_result['issues']:
        if 'pH' in issue and '벗어남' in issue:
            target = constraints.get('target_ph', 5.5)
            if predictions['ph'] > target:
                suggestions.append(f"💡 pH 낮추기: Citric Acid 증량 또는 추가 (현재 예측 {predictions['ph']} → 목표 {target})")
            else:
                suggestions.append(f"💡 pH 올리기: Triethanolamine 또는 Arginine 추가")
        
        if '투명' in issue:
            suggestions.append("💡 투명도 개선: 불투명 원료 제거/감량 (Glyceryl Stearate, Stearyl Alcohol, TiO₂)")
            suggestions.append("💡 투명 점증제 사용: Carbomer, HEC, Xanthan Gum")
        
        if '안전 한계' in issue:
            # Extract ingredient name
            inci = issue.split(':')[0].replace('❌ ', '')
            suggestions.append(f"💡 {inci} 감량 필요")
        
        if '미검증 원료' in issue:
            suggestions.append("💡 EVAS 미검증 원료 → 소량 시제(500g) 안정성 테스트 선행 권장")
    
    for warning in critique_result['warnings']:
        if 'EVAS 최대' in warning:
            parts = warning.split(':')
            inci = parts[0].replace('⚠️ ', '').strip()
            suggestions.append(f"💡 {inci}: EVAS 최대 농도 참고하여 감량 검토")
    
    return {
        'suggestions': suggestions,
        'modified_composition': modified,  # Future: auto-apply fixes
        'optimization_rounds': 1
    }


# ═══════════════════════════════════════════════════════════
# ORCHESTRATOR — 전체 파이프라인
# ═══════════════════════════════════════════════════════════

def run_formulation_check(composition: list[dict], 
                          keywords: list[str] = None,
                          category: str = None,
                          constraints: dict = None):
    """
    처방 검증 전체 파이프라인
    
    composition: [{'inci': 'Water', 'pct': 75.0}, ...]
    keywords: ['Houttuynia', 'Menthol'] — 검색 키워드
    category: 'hair' — 제품 카테고리
    constraints: {'target_ph': 5.5, 'transparent': True, 'target_viscosity': 5000}
    """
    print("="*60)
    print("🏭 EVAS Formulation Intelligence Engine v1")
    print("="*60)
    
    keywords = keywords or [item['inci'] for item in composition[:3]]
    constraints = constraints or {}
    
    # Agent 1: Retriever
    print("\n📥 Agent 1: RETRIEVER")
    retrieved = retrieve(keywords, category, constraints)
    
    # Agent 2: Predictor
    print("\n📊 Agent 2: PREDICTOR")
    predictions = predict_properties(composition)
    print(f"  pH: {predictions['ph']}")
    print(f"  점도: {predictions['viscosity_cps']:.0f} cps")
    print(f"  성상: {predictions['appearance']} ({json.dumps(predictions['appearance_proba'])})")
    
    # Agent 3: Critic
    print("\n🔍 Agent 3: CRITIC")
    critique_result = critique(composition, predictions, retrieved, constraints)
    
    # Agent 4: Optimizer
    print("\n🔧 Agent 4: OPTIMIZER")
    optimization = optimize(composition, critique_result, predictions, constraints)
    
    # Engine B: Market Expansion
    print("\n🔵 Engine B: MARKET EXPANSION")
    market_result = market_expansion(composition, constraints)
    
    # ─── Final Report ───
    print("\n" + "="*60)
    print(f"📋 FORMULATION VERIFICATION REPORT")
    print(f"   신뢰도: {critique_result['score']}/100")
    print("="*60)
    
    print(f"\n📊 예측 물성:")
    print(f"  pH:    {predictions['ph']}")
    print(f"  점도:  {predictions['viscosity_cps']:.0f} cps")
    print(f"  성상:  {predictions['appearance']}")
    if constraints.get('transparent'):
        print(f"  투명:  {predictions['appearance_proba'].get('transparent', 0):.0%}")
    
    print(f"\n✅ PASS ({len(critique_result['passes'])}):")
    for p in critique_result['passes']:
        print(f"  {p}")
    
    if critique_result['warnings']:
        print(f"\n⚠️ WARNINGS ({len(critique_result['warnings'])}):")
        for w in critique_result['warnings']:
            print(f"  {w}")
    
    if critique_result['issues']:
        print(f"\n❌ ISSUES ({len(critique_result['issues'])}):")
        for i in critique_result['issues']:
            print(f"  {i}")
    
    if optimization['suggestions']:
        print(f"\n💡 SUGGESTIONS:")
        for s in optimization['suggestions']:
            print(f"  {s}")
    
    # Similar products
    if retrieved['similar_products']:
        print(f"\n🔗 유사 EVAS 제품:")
        for sp in retrieved['similar_products'][:3]:
            m = sp['meta']
            print(f"  {m['product_code']}: {m.get('korean_name', 'N/A')}")
            print(f"    pH: {m.get('ph_standard', 'N/A')} | 점도: {m.get('viscosity_standard', 'N/A')}")
    
    if retrieved['cluster_info']:
        print(f"\n📦 해당 클러스터: {retrieved['cluster_info']['cluster_name']}")
    
    # ─── Engine B Market Section ───
    if market_result:
        print(f"\n{'─'*60}")
        print(f"🔵 ENGINE B: 시장 확장 분석")
        print(f"{'─'*60}")
        print(f"  매핑 클러스터: C{market_result['cluster_id']} ({market_result.get('cluster_type', '')})")
        print(f"  유사도: {market_result['similarity']}")
        print(f"  EVAS {market_result.get('evas_count', '?')}개 ↔ 시장 {market_result['market_count']}개")
        
        if market_result['expansion_suggestions']:
            print(f"\n  💡 확장 제안:")
            for s in market_result['expansion_suggestions']:
                print(f"    {s}")
        
        if market_result['concentration_gaps']:
            print(f"\n  📊 농도 벤치마크 (현재 vs 시장):")
            for g in market_result['concentration_gaps'][:5]:
                print(f"    {g['inci'][:40]:40s} 현재 {g['current_pct']:>5.1f}% → 시장 {g['market_avg_pct']:>5.1f}% ({g['direction']})")
        
        if market_result['market_only']:
            print(f"\n  🆕 시장에서 많이 쓰지만 이 처방에 없는 원료:")
            for m in market_result['market_only'][:5]:
                print(f"    {m['market_product_count']:>3}개 제품 | avg {m['market_avg_pct']:>5.1f}% | {m['inci'][:50]}")
    
    return {
        'predictions': predictions,
        'critique': critique_result,
        'optimization': optimization,
        'market_expansion': market_result,
        'retrieved': {
            'similar_count': len(retrieved['similar_products']),
            'profiles_count': len(retrieved['ingredient_profiles']),
            'cluster': retrieved['cluster_info']['cluster_name'] if retrieved['cluster_info'] else None
        }
    }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    if '--test' in sys.argv:
        # AOSP003 기반 테스트
        print("🧪 TEST MODE: AOSP003 배합으로 검증\n")
        
        comp = sb.table('evas_product_compositions').select(
            'inci_name_en, percentage'
        ).eq('product_code', 'AOSP003').order('rank').execute().data
        
        composition = [{'inci': c['inci_name_en'], 'pct': float(c['percentage'] or 0)} 
                       for c in comp if c.get('inci_name_en')]
        
        run_formulation_check(
            composition=composition,
            keywords=['Houttuynia', 'Menthol', 'Cocamidopropyl Betaine'],
            category='hair',
            constraints={'target_ph': 5.8, 'target_viscosity': 5500, 'transparent': False}
        )
    else:
        print("Usage: python formulation_engine.py --test")
        print("       (Full integration is called from the AI assistant)")
