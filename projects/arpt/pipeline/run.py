"""ARPT 통합 파이프라인 실행기
Usage: python -m pipeline.run --topic "PDRN 앰플"              # 새 세션 + 전체 파이프라인
       python -m pipeline.run --session-id <uuid>              # 기존 세션 이어서
       python -m pipeline.run --session-id <uuid> --phase scoring
       python -m pipeline.run --session-id <uuid> --phases ingredients,scoring,tournament,gaps
"""
import argparse
import sys
import time
import uuid as uuid_lib
from supabase import create_client

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY, BATCH_SIZE
from .scout import run_scout
from .ingredients import collect_all_ingredients
from .grok_async import run_batch as grok_batch
from .scorer import compute_final_score
from .tournament import run_tournament
from .infranodus import run_gap_analysis
from .report import generate_reports


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_session(topic: str, preset: str, sb) -> str:
    """Create a new ARPT session and return its UUID"""
    session_id = str(uuid_lib.uuid4())
    sb.table("arpt_sessions").insert({
        "id": session_id,
        "topic": topic,
        "preset": preset,
        "status": "scouting",
        "product_count": 0,
    }).execute()
    print(f"🆕 Session created: {session_id}")
    print(f"   Topic: {topic}")
    print(f"   Preset: {preset}")
    return session_id


def phase_scout(session_id: str, topic: str, sb):
    """Phase: Auto-scout products via Grok web search"""
    products = run_scout(topic, session_id, sb)
    print(f"✅ Scouting: {len(products)} products inserted")
    return products


def phase_ingredients(session_id: str, sb):
    """Phase: Collect full ingredients for all products"""
    print("\n" + "="*60)
    print("📦 PHASE: Ingredient Collection")
    print("="*60)
    
    products = sb.table("arpt_products").select("*").eq("session_id", session_id).execute().data
    collected = collect_all_ingredients(products, sb)
    print(f"✅ Ingredients: {collected}/{len(products)} products enriched")
    return products


def phase_scoring(session_id: str, sb, preset: str = "default"):
    """Phase: Score all products (Grok async + consumer/value calc)"""
    print("\n" + "="*60)
    print("📊 PHASE: Scoring")
    print("="*60)
    
    products = sb.table("arpt_products").select("*").eq("session_id", session_id).execute().data
    
    # Delete existing scores for this session's products (re-run safe)
    product_ids = [p["id"] for p in products]
    for pid in product_ids:
        sb.table("arpt_scores").delete().eq("product_id", pid).execute()
    
    # Batch Grok analysis (개선 #1 + #4: async + batched)
    total = len(products)
    all_grok_results = {}
    
    for batch_start in range(0, total, BATCH_SIZE):
        batch = products[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n🔍 Batch {batch_num}/{total_batches} ({len(batch)} products)")
        
        batch_results = grok_batch(batch, concurrency=BATCH_SIZE)
        all_grok_results.update(batch_results)
        
        if batch_start + BATCH_SIZE < total:
            time.sleep(2)  # Rate limit between batches
    
    # Compute final scores
    print(f"\n📈 Computing final scores...")
    for p in products:
        grok_data = all_grok_results.get(p["id"], {})
        score_row = compute_final_score(p, grok_data, preset)
        sb.table("arpt_scores").insert(score_row).execute()
        print(f"  {p['brand']:20s} → Final: {score_row['final_score']:6.1f} (E:{score_row['efficacy_score']} F:{score_row['formulation_score']} C:{score_row['consumer_score']:.0f} V:{score_row['value_score']:.0f} D:{score_row['differentiation_score']})")
    
    sb.table("arpt_sessions").update({"status": "tournament"}).eq("id", session_id).execute()
    print(f"\n✅ Scoring complete → tournament")


def phase_tournament(session_id: str, sb):
    """Phase: Run tournament rounds"""
    print("\n" + "="*60)
    print("🏆 PHASE: Tournament")
    print("="*60)
    
    # Clean previous rounds for this session
    sb.table("arpt_rounds").delete().eq("session_id", session_id).execute()
    
    champions = run_tournament(session_id, sb)
    
    sb.table("arpt_sessions").update({"status": "reporting"}).eq("id", session_id).execute()
    print(f"\n✅ Tournament complete → reporting")
    return champions


def phase_gaps(session_id: str, sb):
    """Phase: Gap analysis (InfraNodus → LLM fallback)"""
    print("\n" + "="*60)
    print("📐 PHASE: Gap Analysis")
    print("="*60)
    
    # Clean previous gaps
    sb.table("arpt_gaps").delete().eq("session_id", session_id).execute()
    
    # Get top products (advanced in latest round)
    products = sb.table("arpt_products").select("*").eq("session_id", session_id).execute().data
    
    gaps = run_gap_analysis(products, session_id, sb)
    print(f"\n✅ Gap analysis: {len(gaps)} gaps identified")
    return gaps


def phase_reports(session_id: str, sb):
    """Phase: Generate 2 reports and save as files"""
    reports = generate_reports(session_id, sb)
    
    import os
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'pilot-results')
    os.makedirs(out_dir, exist_ok=True)
    
    topic_slug = reports["topic"].replace(" ", "-")
    
    report_a_path = os.path.join(out_dir, f'{topic_slug}-처방제안서.md')
    report_b_path = os.path.join(out_dir, f'{topic_slug}-상품기획제안서.md')
    
    with open(report_a_path, 'w') as f:
        f.write(reports["report_a"])
    with open(report_b_path, 'w') as f:
        f.write(reports["report_b"])
    
    print(f"\n📄 Report A saved: {report_a_path}")
    print(f"📄 Report B saved: {report_b_path}")
    
    return {
        "report_a_path": report_a_path,
        "report_b_path": report_b_path,
        "reports": reports
    }


def run_full(session_id: str, preset: str = "default", topic: str = None):
    """Full pipeline: scout → ingredients → scoring → tournament → gaps → reports"""
    sb = get_supabase()
    
    session = sb.table("arpt_sessions").select("*").eq("id", session_id).single().execute().data
    topic = topic or session["topic"]
    print(f"\n{'='*60}")
    print(f"🚀 ARPT Full Pipeline: {topic}")
    print(f"   Session: {session_id}")
    print(f"   Preset: {preset}")
    print(f"{'='*60}")
    
    # Phase 0: Scout (if no products yet)
    existing = sb.table("arpt_products").select("id", count="exact").eq("session_id", session_id).execute()
    if existing.count == 0:
        phase_scout(session_id, topic, sb)
    else:
        print(f"📦 {existing.count} products already scouted, skipping scout phase")
    
    # Phase 1: Ingredients
    phase_ingredients(session_id, sb)
    
    # Phase 2: Scoring
    phase_scoring(session_id, sb, preset)
    
    # Phase 3: Tournament
    champions = phase_tournament(session_id, sb)
    
    # Phase 4: Gaps
    gaps = phase_gaps(session_id, sb)
    
    # Phase 5: Reports
    report_result = phase_reports(session_id, sb)
    
    # Mark complete
    sb.table("arpt_sessions").update({
        "status": "completed",
        "completed_at": "now()"
    }).eq("id", session_id).execute()
    
    print("\n" + "="*60)
    print("✅ ARPT Pipeline Complete!")
    print("="*60)
    return {"champions": champions, "gaps": gaps, "reports": report_result}


def main():
    parser = argparse.ArgumentParser(description="ARPT Pipeline Runner")
    parser.add_argument("--topic", help="Topic for new session (creates session automatically)")
    parser.add_argument("--session-id", help="Existing session UUID (required if no --topic)")
    parser.add_argument("--preset", default="default", choices=["default", "trend", "stable", "innovation"])
    parser.add_argument("--phase", help="Run single phase: scout|ingredients|scoring|tournament|gaps|reports")
    parser.add_argument("--phases", help="Comma-separated phases to run")
    
    args = parser.parse_args()
    sb = get_supabase()
    
    # Create session if topic provided
    if args.topic and not args.session_id:
        args.session_id = create_session(args.topic, args.preset, sb)
    
    if not args.session_id:
        print("❌ Either --topic or --session-id is required")
        sys.exit(1)
    
    if args.phase:
        phases = [args.phase]
    elif args.phases:
        phases = [p.strip() for p in args.phases.split(",")]
    else:
        # Full run
        session = sb.table("arpt_sessions").select("topic").eq("id", args.session_id).single().execute().data
        run_full(args.session_id, args.preset, topic=args.topic or session["topic"])
        return
    
    for phase in phases:
        if phase == "scout":
            session = sb.table("arpt_sessions").select("topic").eq("id", args.session_id).single().execute().data
            phase_scout(args.session_id, args.topic or session["topic"], sb)
        elif phase == "ingredients":
            phase_ingredients(args.session_id, sb)
        elif phase == "scoring":
            phase_scoring(args.session_id, sb, args.preset)
        elif phase == "tournament":
            phase_tournament(args.session_id, sb)
        elif phase == "gaps":
            phase_gaps(args.session_id, sb)
        elif phase == "reports":
            phase_reports(args.session_id, sb)
        else:
            print(f"❌ Unknown phase: {phase}")
            sys.exit(1)
    
    print(f"\n📋 Session ID: {args.session_id}")


if __name__ == "__main__":
    main()
