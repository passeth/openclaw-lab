-- ============================================================
-- 3. evas_product_compositions — 제품 조성 유사도 검색
-- ============================================================

-- 3-1. Embeddings 테이블
CREATE TABLE IF NOT EXISTS evas_product_compositions_embeddings (
  id             BIGSERIAL PRIMARY KEY,
  composition_id TEXT      NOT NULL UNIQUE,   -- evas_product_compositions PK
  content        TEXT      NOT NULL,           -- 검색 대상 텍스트 (product_name + ingredient_list + category 등)
  embedding      vector(1536) NOT NULL,        -- text-embedding-3-small
  created_at     TIMESTAMPTZ  DEFAULT now(),
  updated_at     TIMESTAMPTZ  DEFAULT now()
);

-- 3-2. HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_product_compositions_embeddings_hnsw
  ON evas_product_compositions_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 3-3. Semantic search 함수
CREATE OR REPLACE FUNCTION search_product_compositions_semantic(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.5,
  match_count     INT   DEFAULT 20
)
RETURNS TABLE (
  composition_id TEXT,
  content        TEXT,
  similarity     FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.composition_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM evas_product_compositions_embeddings e
  WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 3-4. Hybrid search 함수
CREATE OR REPLACE FUNCTION search_product_compositions_hybrid(
  query_text      TEXT,
  query_embedding vector(1536),
  match_count     INT   DEFAULT 20,
  fts_weight      FLOAT DEFAULT 0.3,
  vec_weight      FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  composition_id TEXT,
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
      e.composition_id,
      e.content,
      ts_rank_cd(to_tsvector('english', e.content), plainto_tsquery('english', query_text)) AS rank
    FROM evas_product_compositions_embeddings e
    WHERE to_tsvector('english', e.content) @@ plainto_tsquery('english', query_text)
  ),
  vec AS (
    SELECT
      e.composition_id,
      e.content,
      1 - (e.embedding <=> query_embedding) AS similarity
    FROM evas_product_compositions_embeddings e
  ),
  combined AS (
    SELECT
      COALESCE(f.composition_id, v.composition_id) AS composition_id,
      COALESCE(f.content, v.content) AS content,
      COALESCE(f.rank, 0.0) AS fts_rank,
      COALESCE(v.similarity, 0.0) AS vec_similarity,
      (fts_weight * COALESCE(f.rank, 0.0)) + (vec_weight * COALESCE(v.similarity, 0.0)) AS hybrid_score
    FROM fts f
    FULL OUTER JOIN vec v ON f.composition_id = v.composition_id
  )
  SELECT
    c.composition_id,
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
