# 🧪 coslab

## 개요
에바스 자체 개발 화장품 성분 분석 CLI. Supabase(Intel 프로젝트)에 저장된 1,320개 성분 DB + CosIng 규제 데이터를 활용하여 성분 안전성 조회, MoS 계산, 규제 체크를 수행한다.

## 등록 에이전트
- **LAB** (주 사용자)
- RISE (개발)

## 설치 경로
```bash
git clone https://github.com/passeth/coslab.git
cd coslab
npm install && npm link
export SUPABASE_INTEL_KEY="<intel_service_role_key>"
```

## 핵심 명령어

### 성분 안전성 조회
```bash
coslab analyze "Niacinamide"
# → 안전성 요약, 자극/감작 등급, EU/FDA/MFDS 규제, 최대 농도
```

### 제품 전성분 MoS 계산
```bash
coslab mos "Pro-moisture Creamy"
# → FRAIJOUR 크림 전성분 MoS 시뮬레이션
# → safe/review/no-data 분류
```

### 성분 규제 체크
```bash
coslab regulate "Retinol"
# → CosIng Annex II/III + EU/FDA/MFDS 멀티 규제
```

### JSON 출력 (프로그래밍용)
```bash
coslab analyze "Niacinamide" --json
coslab mos "크림명" --json > result.json
```

## MoS 계산 공식 (SCCS 11th revision)
```
MoS = PoDsys / SED
SED = Eproduct × C/100 × DA/100
PoDsys = NOAEL × oral_bioavailability (기본 50%)

MoS ≥ 100 → 안전
```
- Eproduct: 제품 유형별 일일 노출량 (face cream 24.53 mg/kg bw/day)
- C: 성분 농도 (%)
- DA: 피부흡수율 (%)

## 한계
- NOAEL 없는 성분 → TTC(Cramer Class) 적용 필요
- 약 4/13개 성분 no-data 예상

## 관련 링크
- GitHub: https://github.com/passeth/coslab
- CPSR 리서치 Gist: https://gist.github.com/passeth/b92005411d3748a809d8878fbfe36c47

## 업데이트
- 2026-03-12: RISE 개발, LAB 인수인계
