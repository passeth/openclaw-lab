# 📄 CPSR / PIF 자동화 도구

## 개요
EU 화장품 규정(EC 1223/2009) 준수를 위한 CPSR(Cosmetic Product Safety Report) 및 PIF(Product Information File) 작성 지원 도구 모음.

## 등록 에이전트
- **LAB** (주 사용자)

## CPSR 구조 (Annex I 기준)

### Part A: 제품 안전 정보
1. 제품 설명 및 용도
2. 전성분 (INCI명, 농도, CAS)
3. 물리화학적 특성
4. 미생물학적 품질
5. 불순물/미량성분
6. 포장 정보
7. 노출 평가 (SED 계산)
8. 독성 프로파일 (성분별 MoS)

### Part B: 안전성 평가
- Safety Assessor의 MoS 계산 기반 판정
- 서명 + 자격 증명 필요

## coslab을 활용한 CPSR 초안 워크플로우
```bash
# 1. 전성분 MoS 일괄 계산
coslab mos "제품명" --json > mos_result.json

# 2. 결과 분류
# - safe: MoS ≥ 100
# - review: NOAEL 부족, TTC 적용 필요
# - no-data: 추가 조사 필요

# 3. Part A 독성 프로파일 작성에 활용
```

## 외부 CPSR 보조 도구
| 도구 | 유형 | 특징 |
|---|---|---|
| AutoPIF™ | SaaS (유료) | LLM + Rules Engine, PIF 자동 생성 |
| Cosmedesk | SaaS | SED/MoS 자동 계산 |
| OECD QSAR Toolbox | 무료 | in silico 독성 예측 |
| COSMOS DB | 무료 | TTC 데이터셋 552개 화합물 |

## TTC (Threshold of Toxicological Concern)
NOAEL 데이터 없을 때 적용:
```
Cramer Class I: TTC = 1800 μg/day
Cramer Class II: TTC = 540 μg/day  
Cramer Class III: TTC = 90 μg/day
```

## 주요 Eproduct 값 (SCCS NoG 11th)
| 제품 유형 | 일일 노출량 |
|---|---|
| Face cream | 24.53 mg/kg bw/day |
| Body lotion | 69.0 mg/kg bw/day |
| Shampoo | 10.7 mg/kg bw/day |
| Lipstick | 5.24 mg/kg bw/day |

## 업데이트
- 2026-03-12: CPSR 자동화 리서치 완료 (RISE → LAB 이관)
