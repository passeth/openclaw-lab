# 🌿 CosIng (EU Cosmetic Ingredients Database)

## 개요
EU 화장품 규정(EC 1223/2009)에 따라 화장품 성분을 관리하는 공식 EU 데이터베이스. 성분 명칭, INCI명, 기능, Annex 분류(제한/금지/허용 조건) 조회에 사용.

## 등록 에이전트
- **LAB** (주 사용자)

## 접근 방법

### 1. 직접 웹 조회
- URL: https://ec.europa.eu/growth/tools-databases/cosing/

### 2. coslab CLI via Supabase
```bash
coslab regulate "성분명"
# → Annex II(금지), III(제한), IV(착색제), V(방부제), VI(UV필터) 분류 반환
```

### 3. OpenClaw 스킬: cosing-database
```
qmd search "cosing" -c skills
# → ~/.openclaw/skills/cosing-database/SKILL.md 참조
```

## Annex 분류 요약
| Annex | 의미 |
|---|---|
| Annex II | 금지 성분 |
| Annex III | 조건부 허용 (농도 제한 등) |
| Annex IV | 허용 착색제 목록 |
| Annex V | 허용 방부제 목록 |
| Annex VI | 허용 UV 필터 목록 |

## 주요 활용 사례
- 신원료 EU 수출 전 규제 확인
- CPSR 작성 시 Annex 근거 제시
- 성분 대체재 탐색 (금지 성분 → 허용 대안)

## 업데이트
- 수시 (EU 규정 개정 시 자동 반영)
