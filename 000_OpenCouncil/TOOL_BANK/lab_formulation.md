# ⚗️ Formulation Tools

## 개요
화장품 제형 개발에 사용하는 도구 모음. HLB 계산, pH 예측, 에멀전 설계, 처방 스케일링 등을 지원.

## 등록 에이전트
- **LAB** (주 사용자)

## 포함 도구

### 1. OpenClaw 스킬: formulation-calculator
```bash
# 로드
qmd search "formulation-calculator" -c skills
```
- HLB 계산 (HLB = Σ(성분 HLB × 비율))
- 에멀전 타입 예측 (O/W vs W/O)
- pH 완충액 계산

### 2. OpenClaw 스킬: batch-calculator
```bash
qmd search "batch-calculator" -c skills
```
- 배합 스케일 변환 (% → gram → kg)
- 생산 배치 크기 계산
- 원가 계산 연동

### 3. OpenClaw 스킬: formulation-strategy
```bash
qmd search "formulation-strategy" -c skills
```
- 제형 개발 전략 수립
- 베이스 시스템 선택 (에멀전/겔/앰플)
- 스킨케어 카테고리별 최적 제형

### 4. OpenClaw 스킬: ingredient-compatibility
```bash
qmd search "ingredient-compatibility" -c skills
```
- 성분 간 호환성/비호환성 분석
- 불안정화 리스크 평가
- 대체 성분 추천

## 실제 프로젝트 적용 사례
- `/projects/formulations/` - 처방 개발 작업
- `/projects/2026-03-09_sebum-control-shampoo/` - 피지 조절 샴푸 처방

## 주요 계산 공식

### HLB 계산
```
HLB_blend = Σ(HLB_i × w_i)
목표: O/W 에멀전 = 8~16
```

### 전하 중화 (양이온-음이온)
```
비호환: Carbomer(음이온) + Quaternium(양이온) → 침전
대안: Carbomer + Guar Hydroxypropyl Trimonium Chloride
```

## 업데이트
- 2026-03-09: 샴푸 처방 프로젝트 시작
