"""토너먼트 엔진 — 3라운드 실행"""

def run_tournament(session_id: str, supabase_client, rounds_config=None):
    """Execute tournament rounds and save results.
    
    rounds_config: list of (cutoff_count, round_name) tuples
    Default for 50 products: [(20, "Top 20"), (10, "Top 10"), (5, "Champions")]
    For pilot 10 products: [(5, "Top 5")]
    """
    # Get all scores for this session
    products = supabase_client.table("arpt_products") \
        .select("id, product_name, brand") \
        .eq("session_id", session_id).execute().data
    
    product_ids = [p["id"] for p in products]
    product_map = {p["id"]: p for p in products}
    
    # Get scores, filtered to our products
    all_scores = supabase_client.table("arpt_scores") \
        .select("product_id, final_score") \
        .in_("product_id", product_ids) \
        .order("final_score", desc=True).execute().data
    
    # Deduplicate: keep highest score per product
    seen = set()
    scores = []
    for s in all_scores:
        if s["product_id"] not in seen:
            seen.add(s["product_id"])
            scores.append(s)
    
    if not rounds_config:
        n = len(scores)
        if n <= 15:
            rounds_config = [(max(3, n // 2), "Top Half")]
        else:
            rounds_config = [(20, "Top 20"), (10, "Top 10"), (5, "Champions")]
    
    current_pool = scores
    
    for round_num, (cutoff, label) in enumerate(rounds_config, 1):
        print(f"\n🏆 Round {round_num}: {label} (cutoff: {cutoff})")
        
        for rank, s in enumerate(current_pool, 1):
            pid = s["product_id"]
            p = product_map.get(pid, {})
            advanced = rank <= cutoff
            
            round_row = {
                "session_id": session_id,
                "round_number": round_num,
                "product_id": pid,
                "round_score": s["final_score"],
                "rank_in_round": rank,
                "analysis": {
                    "label": label,
                    "total_in_round": len(current_pool)
                },
                "advanced": advanced,
                "eliminated_reason": None if advanced else f"Rank {rank}/{len(current_pool)} - below {label} cutoff"
            }
            
            supabase_client.table("arpt_rounds").insert(round_row).execute()
            
            status = "✅" if advanced else "❌"
            brand = p.get("brand", "?")
            print(f"  #{rank:2d} {brand:20s} {s['final_score']:6.1f} {status}")
        
        # Next round pool
        current_pool = current_pool[:cutoff]
    
    # Return champions
    champions = current_pool
    print(f"\n🏅 Champions: {len(champions)} products")
    return champions
