-- ============================================================
-- Content 조합 뷰 — 임베딩 생성 시 이 뷰에서 content를 가져옴
-- 실제 컬럼명은 테이블 스키마에 맞게 조정 필요!
-- ============================================================

-- incidecoder_ingredients: INCI명 + 설명 + 기능 조합
-- TODO: 실제 컬럼명 확인 후 수정
CREATE OR REPLACE VIEW v_incidecoder_for_embedding AS
SELECT
  id::TEXT AS ingredient_id,
  CONCAT_WS(' | ',
    COALESCE(inci_name, ''),
    COALESCE(description, ''),
    COALESCE(functions, ''),
    COALESCE(also_known_as, '')
  ) AS content
FROM incidecoder_ingredients
WHERE inci_name IS NOT NULL;

-- evas_research_tech_reports_v2: 제목 + 요약 + 핵심 내용
-- TODO: 실제 컬럼명 확인 후 수정
CREATE OR REPLACE VIEW v_tech_reports_for_embedding AS
SELECT
  id::TEXT AS report_id,
  CONCAT_WS(' | ',
    COALESCE(title, ''),
    COALESCE(summary, ''),
    COALESCE(key_findings, ''),
    COALESCE(category, '')
  ) AS content
FROM evas_research_tech_reports_v2
WHERE title IS NOT NULL;

-- evas_product_compositions: 제품명 + 성분 리스트 + 카테고리
-- TODO: 실제 컬럼명 확인 후 수정
CREATE OR REPLACE VIEW v_product_compositions_for_embedding AS
SELECT
  id::TEXT AS composition_id,
  CONCAT_WS(' | ',
    COALESCE(product_name, ''),
    COALESCE(ingredient_list, ''),
    COALESCE(category, ''),
    COALESCE(brand, '')
  ) AS content
FROM evas_product_compositions
WHERE product_name IS NOT NULL;
