-- ============================================================
-- 2. evas_research_tech_reports_v2 — 기술 리포트 시맨틱 검색
-- ============================================================

-- 2-1. Embeddings 테이블
CREATE TABLE IF NOT EXISTS evas_research_tech_reports_v2_embeddings (
  id         BIGSERIAL PRIMARY KEY,
  report_id  TEXT      NOT NULL UNIQUE,   -- evas_research_tech_reports_v2 PK
  content    TEXT      NOT NULL,           -- 검색 대상 텍스트 (title + summary + key_findings 등)
  embedding  vector(1536) NOT NULL,        -- text-embedding-3-small
  created_at TIMESTAMPTZ  DEFAULT now(),
  updated_at TIMESTAMPTZ  DEFAULT now()
);

-- 2-2. HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_tech_reports_embeddings_hnsw
  ON evas_research_tech_reports_v2_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 2-3. Semantic search 함수
CREATE OR REPLACE FUNCTION search_tech_reports_semantic(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.5,
  match_count     INT   DEFAULT 20
)
RETURNS TABLE (
  report_id  TEXT,
  content    TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.report_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM evas_research_tech_reports_v2_embeddings e
  WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 2-4. Hybrid search 함수
CREATE OR REPLACE FUNCTION search_tech_reports_hybrid(
  query_text      TEXT,
  query_embedding vector(1536),
  match_count     INT   DEFAULT 20,
  fts_weight      FLOAT DEFAULT 0.3,
  vec_weight      FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  report_id      TEXT,
  content        TEXT,
  fts_rank       FLOAT,
  vec_similarity FLOAT,
  hybrid_score   FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH fts AS (
    SELECT
      e.report_id,
      e.content,
      ts_rank_cd(to_tsvector('english', e.content), plainto_tsquery('english', query_text)) AS rank
    FROM evas_research_tech_reports_v2_embeddings e
    WHERE to_tsvector('english', e.content) @@ plainto_tsquery('english', query_text)
  ),
  vec AS (
    SELECT
      e.report_id,
      e.content,
      1 - (e.embedding <=> query_embedding) AS similarity
    FROM evas_research_tech_reports_v2_embeddings e
  ),
  combined AS (
    SELECT
      COALESCE(f.report_id, v.report_id) AS report_id,
      COALESCE(f.content, v.content) AS content,
      COALESCE(f.rank, 0.0) AS fts_rank,
      COALESCE(v.similarity, 0.0) AS vec_similarity,
      (fts_weight * COALESCE(f.rank, 0.0)) + (vec_weight * COALESCE(v.similarity, 0.0)) AS hybrid_score
    FROM fts f
    FULL OUTER JOIN vec v ON f.report_id = v.report_id
  )
  SELECT
    c.report_id,
    c.content,
    c.fts_rank,
    c.vec_similarity,
    c.hybrid_score
  FROM combined c
  WHERE c.hybrid_score > 0
  ORDER BY c.hybrid_score DESC
  LIMIT match_count;
END;
$$;
