-- ARPT (Auto Research Product Tournament) 스키마 v1.1
-- Supabase SQL Editor에서 실행

-- 1. 세션 마스터 테이블
CREATE TABLE arpt_sessions (
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
CREATE TABLE arpt_products (
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
CREATE TABLE arpt_scores (
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
CREATE TABLE arpt_rounds (
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

-- 5. 구조적 공백 (기회 영역)
CREATE TABLE arpt_gaps (
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

-- 인덱스
CREATE INDEX idx_products_session ON arpt_products(session_id);
CREATE INDEX idx_scores_product ON arpt_scores(product_id);
CREATE INDEX idx_rounds_session ON arpt_rounds(session_id);
CREATE INDEX idx_rounds_product ON arpt_rounds(product_id);
CREATE INDEX idx_gaps_session ON arpt_gaps(session_id);
CREATE INDEX idx_sessions_topic ON arpt_sessions(topic);
CREATE INDEX idx_sessions_status ON arpt_sessions(status);

-- RLS 비활성화 (service_role로 접근)
ALTER TABLE arpt_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE arpt_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE arpt_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE arpt_rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE arpt_gaps ENABLE ROW LEVEL SECURITY;

-- service_role은 RLS 무시하므로 별도 policy 불필요
-- 필요시 anon용 read-only policy 추가 가능

-- 확인
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'arpt_%'
ORDER BY table_name;
