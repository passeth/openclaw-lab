"""개선 #3: InfraNodus 자동 Gap 분석
- REST API로 텍스트 네트워크 분석
- 구조적 공백(structural gaps) 자동 추출
- API 키 없으면 LLM 기반 fallback
"""
import json
import requests
import asyncio
import aiohttp
from typing import Optional

from .config import INFRANODUS_API_KEY, INFRANODUS_BASE_URL, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL


def _build_analysis_text(products: list[dict]) -> str:
    """Build text corpus from products for network analysis"""
    texts = []
    for p in products:
        parts = [
            f"Product: {p.get('product_name', '')}",
            f"Brand: {p.get('brand', '')}",
            f"Tier: {p.get('brand_tier', '')}",
            f"Price: {p.get('price', '')} {p.get('currency', 'KRW')}",
        ]
        
        # Add ingredients if available
        ingredients = p.get("full_ingredients", "")
        if ingredients:
            parts.append(f"Ingredients: {ingredients[:500]}")
        
        # Add ingredient analysis if available
        raw = p.get("raw_data", {}) or {}
        analysis = raw.get("ingredient_analysis", {})
        if analysis:
            actives = [a["name"] + " (" + a["role"] + ")" for a in analysis.get("actives", [])]
            if actives:
                parts.append(f"Active ingredients: {', '.join(actives)}")
            concerns = [c["name"] + " (" + c["risk"] + ")" for c in analysis.get("concerns", [])]
            if concerns:
                parts.append(f"Concerns: {', '.join(concerns)}")
        
        texts.append(". ".join(parts))
    
    return "\n\n".join(texts)


def analyze_with_infranodus(products: list[dict]) -> Optional[dict]:
    """Use InfraNodus API for text network analysis + gap detection"""
    if not INFRANODUS_API_KEY:
        print("  ⚠️ InfraNodus API key not set, using LLM fallback")
        return None
    
    text = _build_analysis_text(products)
    
    try:
        resp = requests.post(
            f"{INFRANODUS_BASE_URL}/graphAndStatements",
            params={
                "doNotSave": "true",
                "addStats": "true",
                "includeStatements": "true",
                "compactGraph": "false"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {INFRANODUS_API_KEY}"
            },
            json={
                "name": "arpt-gap-analysis",
                "text": text,
                "aiTopics": True
            },
            timeout=60
        )
        
        if resp.status_code != 200:
            print(f"  ❌ InfraNodus API error: {resp.status_code}")
            return None
        
        data = resp.json()
        
        # InfraNodus returns {entriesAndGraphOfContext: {statements, graph}}
        context = data.get("entriesAndGraphOfContext", data)
        graph_data = context.get("graph", {}).get("graphologyGraph", {})
        statements = context.get("statements", [])
        
        # Extract communities (clusters) from statements
        communities = {}
        for stmt in statements:
            hashtags = stmt.get("statementHashtags", [])
            comm_ids = stmt.get("statementCommunities", [])
            for tag, cid in zip(hashtags, comm_ids):
                cid = str(cid)
                if cid not in communities:
                    communities[cid] = set()
                communities[cid].add(tag)
        # Convert sets to lists
        communities = {k: list(v) for k, v in communities.items()}
        
        # Extract nodes from graph
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        result = {
            "graph_nodes": len(nodes) if isinstance(nodes, list) else len(graph_data.get("attributes", {}).get("nodes_to_statements_map", {})),
            "communities": {k: v[:10] for k, v in communities.items()},
            "community_count": len(communities),
            "topics": [],
            "gaps": [],
            "source": "infranodus_api"
        }
        
        # Build topics from communities
        for cid, keywords in communities.items():
            result["topics"].append({
                "community_id": cid,
                "keywords": keywords[:10],
                "size": len(keywords)
            })
        
        # Identify structural gaps: communities with low interconnection
        # (communities that don't share nodes = potential gaps)
        comm_keys = list(communities.keys())
        for i in range(len(comm_keys)):
            for j in range(i+1, len(comm_keys)):
                set_a = set(communities[comm_keys[i]])
                set_b = set(communities[comm_keys[j]])
                overlap = set_a & set_b
                overlap_ratio = len(overlap) / min(len(set_a), len(set_b)) if min(len(set_a), len(set_b)) > 0 else 0
                if overlap_ratio < 0.15:  # Less than 15% overlap = structural gap
                    result["gaps"].append({
                        "between": [comm_keys[i], comm_keys[j]],
                        "cluster_a_keywords": list(set_a)[:5],
                        "cluster_b_keywords": list(set_b)[:5],
                        "overlap": list(overlap),
                        "strength": max(0, 10 - len(overlap) * 5)
                    })
        
        node_count = result["graph_nodes"]
        print(f"  ✅ InfraNodus: {node_count} nodes, {len(result['topics'])} communities, {len(result['gaps'])} gaps")
        return result
        
    except Exception as e:
        print(f"  ❌ InfraNodus error: {e}")
        return None


def _gap_analysis_prompt(products: list[dict]) -> str:
    """Build prompt for LLM-based gap analysis"""
    product_summaries = []
    for p in products:
        raw = p.get("raw_data", {}) or {}
        analysis = raw.get("ingredient_analysis", {})
        actives = [a["name"] for a in analysis.get("actives", [])] if analysis else []
        
        summary = f"- {p['brand']} {p['product_name'][:50]}: ₩{p.get('price',0):,}, {p.get('volume','')}, 평점 {p.get('review_rating','N/A')}, 리뷰 {p.get('review_count','N/A')}건"
        if actives:
            summary += f", 활성성분: {', '.join(actives[:5])}"
        product_summaries.append(summary)
    
    return f"""You are a cosmetics R&D strategist. Analyze these {len(products)} products and identify structural gaps (opportunities not being addressed).

## Products:
{chr(10).join(product_summaries)}

## Task:
Identify 5 structural gaps as JSON array. Each gap:
1. gap_type: one of "ingredient_combo", "price_tier", "target_skin", "formulation", "claim"
2. gap_description: 한글로 작성. 구체적인 기회 설명
3. opportunity_score: 0-100 (높을수록 기회가 큼)
4. evidence: 근거 (어떤 데이터에서 이 공백을 발견했는지)
5. suggested_action: 구체적 R&D 또는 상품 기획 제안

Respond ONLY with JSON array:
[{{"gap_type": "", "gap_description": "", "opportunity_score": 0, "evidence": "", "suggested_action": ""}}]"""


async def analyze_with_llm_fallback(products: list[dict]) -> list[dict]:
    """LLM-based gap analysis when InfraNodus is unavailable"""
    prompt = _gap_analysis_prompt(products)
    
    payload = {
        "model": XAI_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 3000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                XAI_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                data = await resp.json()
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for c in item.get("content", []):
                            if c.get("type") == "output_text":
                                text = c["text"]
                                import re
                                # Try markdown code block first
                                md_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
                                raw = md_match.group(1) if md_match else None
                                if not raw:
                                    arr_match = re.search(r'\[.*\]', text, re.DOTALL)
                                    raw = arr_match.group() if arr_match else None
                                if raw:
                                    # Try multiple parse strategies
                                    for attempt_raw in [raw, re.sub(r',\s*]', ']', re.sub(r',\s*}', '}', raw))]:
                                        try:
                                            gaps = json.loads(attempt_raw)
                                            print(f"  ✅ LLM gap analysis: {len(gaps)} gaps found")
                                            return gaps
                                        except json.JSONDecodeError:
                                            continue
                                    # Last resort: extract individual objects
                                    try:
                                        objs = re.findall(r'\{[^{}]+\}', raw)
                                        gaps = []
                                        for obj_str in objs:
                                            try:
                                                gaps.append(json.loads(obj_str))
                                            except:
                                                continue
                                        if gaps:
                                            print(f"  ✅ LLM gap analysis (object-by-object): {len(gaps)} gaps found")
                                            return gaps
                                    except:
                                        pass
                                    print(f"  ⚠️ JSON parse failed, raw[:200]: {raw[:200]}")
    except Exception as e:
        print(f"  ❌ LLM gap analysis error: {e}")
    
    return []


def run_gap_analysis(products: list[dict], session_id: str, supabase_client) -> list[dict]:
    """Run gap analysis (InfraNodus → LLM fallback) and save to Supabase"""
    print("\n📐 Running gap analysis...")
    
    # Try InfraNodus first
    infranodus_result = analyze_with_infranodus(products)
    
    if infranodus_result and infranodus_result.get("gaps"):
        # Convert InfraNodus gaps to our format
        gaps = []
        for g in infranodus_result["gaps"]:
            kw_a = g.get("cluster_a_keywords", [])
            kw_b = g.get("cluster_b_keywords", [])
            desc = f"성분 네트워크 Gap: [{', '.join(kw_a[:3])}] ↔ [{', '.join(kw_b[:3])}] 클러스터 간 연결 약함 — 이 조합이 미탐색 영역"
            gaps.append({
                "session_id": session_id,
                "gap_type": "network_gap",
                "gap_description": desc,
                "opportunity_score": min(100, g.get("strength", 5) * 15),
                "evidence": {
                    "source": "infranodus",
                    "between_communities": g.get("between", []),
                    "cluster_a": kw_a,
                    "cluster_b": kw_b,
                    "overlap": g.get("overlap", [])
                },
                "infranodus_data": {
                    "total_nodes": infranodus_result.get("graph_nodes", 0),
                    "community_count": infranodus_result.get("community_count", 0),
                    "all_communities": infranodus_result.get("communities", {})
                }
            })
        
        for gap in gaps:
            supabase_client.table("arpt_gaps").insert(gap).execute()
        
        # Also run LLM for richer Korean descriptions
        print("  📝 Adding LLM-enriched gaps...")
        llm_gaps = asyncio.run(analyze_with_llm_fallback(products))
        for g in llm_gaps:
            gap_row = {
                "session_id": session_id,
                "gap_type": g.get("gap_type", "unknown"),
                "gap_description": g.get("gap_description", ""),
                "opportunity_score": g.get("opportunity_score", 50),
                "evidence": {
                    "source": "llm_enriched",
                    "model": XAI_MODEL,
                    "evidence_text": g.get("evidence", ""),
                    "suggested_action": g.get("suggested_action", "")
                },
                "infranodus_data": {
                    "enrichment_source": "infranodus+llm",
                    "infranodus_nodes": infranodus_result.get("graph_nodes", 0)
                }
            }
            supabase_client.table("arpt_gaps").insert(gap_row).execute()
            gaps.append(gap_row)
        
        return gaps
    
    # Fallback to LLM
    print("  🔄 Using LLM fallback for gap analysis...")
    llm_gaps = asyncio.run(analyze_with_llm_fallback(products))
    
    saved_gaps = []
    for g in llm_gaps:
        gap_row = {
            "session_id": session_id,
            "gap_type": g.get("gap_type", "unknown"),
            "gap_description": g.get("gap_description", ""),
            "opportunity_score": g.get("opportunity_score", 50),
            "evidence": {
                "source": "llm_fallback",
                "model": XAI_MODEL,
                "evidence_text": g.get("evidence", ""),
                "suggested_action": g.get("suggested_action", "")
            }
        }
        supabase_client.table("arpt_gaps").insert(gap_row).execute()
        saved_gaps.append(gap_row)
    
    return saved_gaps
