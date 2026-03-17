# 🗄️ Supabase (Intel 프로젝트)

## 개요
에바스 R&D 데이터 인프라. 1,320개 화장품 성분 데이터, 제품 정보, 브랜드 데이터, 규제 정보 등을 PostgreSQL + Vector DB로 관리. LAB의 모든 분석 작업의 데이터 소스.

## 등록 에이전트
- **LAB** (주 사용자)
- RISE (데이터 관리)

## 환경 설정
```bash
export SUPABASE_INTEL_KEY="<intel_service_role_key>"
# coslab CLI가 자동으로 이 키를 사용
```

## 주요 데이터셋
| 테이블/컬렉션 | 규모 | 내용 |
|---|---|---|
| ingredients | 1,320개 | 성분명, 안전성, CosIng 규제, NOAEL |
| products | 1,000개 | 제품 전성분, 브랜드, 카테고리 |
| brands | 673개 | 브랜드 정보 |
| functions | 28개 | 성분 기능 분류 |
| embeddings | 전 성분 | Gemini Embedding 2, 3072-dim 벡터 |

## Python 직접 접근
```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_INTEL_KEY")
)

# 성분 조회
result = supabase.table("ingredients").select("*").eq("name", "Niacinamide").execute()
```

## 벡터 검색 (Semantic)
```python
# Gemini Embedding 2 기반 시멘틱 검색
# Contextual Query: "cosmetic skincare ingredient for {개념}"
```

## 주요 활용 사례
- coslab analyze/mos/regulate의 데이터 소스
- AIaly Knowledge Graph의 데이터 원천
- 신규 원료 연구 시 유사 성분 탐색

## 관련 프로젝트
- `/projects/arpt` - 자동화 파이프라인
- coslab CLI

## 업데이트
- 2026-03-12: Neo4j KG 구축 완료
- 수시: RISE가 신규 성분/제품 데이터 추가
