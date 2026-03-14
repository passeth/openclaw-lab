"""ARPT Supabase 테이블 생성 스크립트"""
from supabase import create_client

SUPABASE_URL = "https://ejbbdtjoqapheqieoohs.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqYmJkdGpvcWFwaGVxaWVvb2hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzEwNDQ0MiwiZXhwIjoyMDg4NjgwNDQyfQ.AI9JRcDGC7DWknoEmBSxFEbXM5fMxNyO7dH3Mur774M"

sb = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

SQL = """
-- 1. 세션 마스터 테이블
CREATE TABLE IF NOT EXISTS arpt_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  keywords TEXT[],
  preset TEXT DEFAULT 'default',
  product_count INTEGER DEFAULT 50,
  status TEXT DEFAULT 'scouting',
  config JSONB,
  gist_url TEXT,
  gist_id TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  error_log JSONB
);

-- 2. 제품 원본 데이터
CREATE TABLE IF NOT EXISTS arpt_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  product_name TEXT NOT NULL,
  brand TEXT,
  brand_tier TEXT,
  price NUMERIC,
  discount_price NUMERIC,
  discount_rate NUMERIC,
  currency TEXT DEFAULT 'KRW',
  volume TEXT,
  review_count INTEGER,
  review_rating NUMERIC,
  full_ingredients TEXT,
  source_url TEXT,
  source_platform TEXT,
  image_url TEXT,
  external_id TEXT,
  raw_data JSONB,
  scraped_at TIMESTAMPTZ DEFAULT now()
);

-- 3. 스코어링 결과
CREATE TABLE IF NOT EXISTS arpt_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES arpt_products(id) ON DELETE CASCADE,
  efficacy_score NUMERIC,
  efficacy_evidence JSONB,
  formulation_score NUMERIC,
  formulation_notes JSONB,
  consumer_score NUMERIC,
  consumer_raw JSONB,
  value_score NUMERIC,
  value_calc JSONB,
  differentiation_score NUMERIC,
  diff_evidence JSONB,
  search_momentum NUMERIC,
  paper_trend NUMERIC,
  sns_buzz NUMERIC,
  launch_freshness NUMERIC,
  ingredient_trend NUMERIC,
  freshness_total NUMERIC,
  review_staleness NUMERIC,
  ingredient_staleness NUMERIC,
  no_renewal NUMERIC,
  staleness_total NUMERIC,
  base_weighted NUMERIC,
  final_score NUMERIC,
  preset_used TEXT,
  scored_at TIMESTAMPTZ DEFAULT now()
);

-- 4. 토너먼트 라운드 기록
CREATE TABLE IF NOT EXISTS arpt_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  round_number INT NOT NULL,
  product_id UUID NOT NULL REFERENCES arpt_products(id) ON DELETE CASCADE,
  round_score NUMERIC,
  rank_in_round INT,
  analysis JSONB,
  advanced BOOLEAN DEFAULT false,
  eliminated_reason TEXT,
  evaluated_at TIMESTAMPTZ DEFAULT now()
);

-- 5. 구조적 공백
CREATE TABLE IF NOT EXISTS arpt_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES arpt_sessions(id) ON DELETE CASCADE,
  gap_type TEXT,
  gap_description TEXT NOT NULL,
  opportunity_score NUMERIC,
  evidence JSONB,
  infranodus_data JSONB,
  related_products UUID[],
  discovered_at TIMESTAMPTZ DEFAULT now()
);
"""

# Supabase Python client uses rpc for raw SQL
# Try using the postgrest-py rpc or direct
try:
    result = sb.rpc('exec_sql', {'query': SQL}).execute()
    print("RPC exec_sql:", result)
except Exception as e:
    print(f"RPC failed (expected): {e}")
    print("\nTrying alternative: psql via pooler or REST...")

# Alternative: use individual table creation via REST test
print("\nTesting connection...")
try:
    # Just test if we can read tables
    result = sb.table('arpt_sessions').select('*').limit(1).execute()
    print(f"arpt_sessions exists: {result}")
except Exception as e:
    print(f"arpt_sessions not found (expected): {e}")

print("\n✅ Script complete. If tables don't exist yet, run supabase-init.sql in the SQL Editor.")
