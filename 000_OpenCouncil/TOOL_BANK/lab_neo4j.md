# 🕸️ Neo4j Knowledge Graph (AIaly)

## 개요
화장품 성분 Knowledge Graph. 성분-제품-브랜드-기능 관계를 그래프 구조로 저장. Gemini Embedding 2 기반 벡터 검색 + 관계 탐색으로 심층 성분 인사이트 제공.

## 등록 에이전트
- **LAB** (조회/분석)
- RISE (구축/관리)

## 그래프 구조
```
(Ingredient) -[HAS_FUNCTION]-> (Function)
(Ingredient) -[FOUND_IN]-> (Product)
(Product) -[MADE_BY]-> (Brand)
(Ingredient) -[SIMILAR_TO]-> (Ingredient)  # 벡터 유사도
(Ingredient) -[INCOMPATIBLE_WITH]-> (Ingredient)
```

## 데이터 규모 (2026-03-12 기준)
- 성분 노드: 1,320개
- 제품 노드: 1,000개
- 브랜드 노드: 673개
- 기능 노드: 28개
- 벡터 임베딩: 전 성분 (3072-dim, Gemini Embedding 2)

## 접근 방법

### Cypher 쿼리 (직접)
```cypher
// 특정 성분의 연관 성분 찾기
MATCH (i:Ingredient {name: "Niacinamide"})-[:SIMILAR_TO]->(j:Ingredient)
RETURN j.name, j.similarity_score
ORDER BY j.similarity_score DESC LIMIT 10

// 특정 기능 성분 목록
MATCH (i:Ingredient)-[:HAS_FUNCTION]->(f:Function {name: "Brightening"})
RETURN i.name, i.max_concentration
```

### coslab (향후 연동 예정)
```bash
# Phase 2
coslab graph "Retinol"
# → 연관 성분, 제품, 규제 그래프 조회
```

## YouTube → 성분 매칭 파이프라인
```
YouTube 영상 자막
→ InfraNodus 토픽 추출
→ Contextual Query: "cosmetic skincare ingredient for {개념}"
→ Gemini Embedding 2 벡터 매칭
→ Neo4j 성분 노드 연결
```

## 관련 링크
- AIaly 리서치 Gist: https://gist.github.com/passeth/d93a0cccd43cc3f3bda45670bcb6dcc3

## 업데이트
- 2026-03-12: 초기 구축 완료 (RISE)
- Phase 2 예정: coslab graph 명령어 연동
