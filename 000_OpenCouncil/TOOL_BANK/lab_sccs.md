# 📋 SCCS (Scientific Committee on Consumer Safety)

## 개요
EU 소비자 안전 과학위원회. 화장품 성분의 인체 안전성을 평가하는 EU 공식 기관. SCCS Opinion(의견서)은 CPSR 작성 시 핵심 근거 자료로 활용됨.

## 등록 에이전트
- **LAB** (주 사용자)

## 접근 방법

### 1. 공식 웹사이트
- URL: https://health.ec.europa.eu/scientific-committees/scientific-committee-consumer-safety-sccs_en
- Opinion 검색: 성분명으로 전체 텍스트 검색 가능

### 2. SCCS Notes of Guidance (NoG)
- 현행 버전: **11th revision (2021)**
- 내용: MoS 계산 방법론, 독성 평가 프레임워크, TTC 적용 기준
- LAB가 coslab MoS 계산에 적용 중인 공식 기준서

### 3. 주요 NOAEL 데이터 조회
```bash
coslab analyze "성분명" --json
# → NOAEL, LOAEL, 독성 등급 포함
```

## MoS 기준값 (NoG 11th revision)
```
MoS = PoDsys / SED

안전 기준:
- 일반 화장품: MoS ≥ 100
- 어린이/민감군 제품: MoS ≥ 200 (권장)
```

## 자주 참조하는 SCCS Opinions
| 성분 | Opinion 번호 | 내용 |
|---|---|---|
| Retinol | SCCS/1575/16 | 0.05% 비린오프 권장 |
| Phenoxyethanol | SCCS/1575/16 | 1% 제한 |
| Titanium Dioxide | SCCS/1617/20 | 흡입 주의, 피부 허용 |

## 주요 활용 사례
- CPSR Part A 독성 프로파일 작성
- 신규 성분 안전성 사전 평가
- 규제 당국 질의 대응 근거 자료

## 업데이트
- NoG: 수년 단위로 개정 (현재 11th revision)
- Opinions: 개별 성분별로 수시 발행
