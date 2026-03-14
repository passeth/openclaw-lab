# 🔬 LAB 봇 브리핑 — coslab + CPSR 자동화

> 2026-03-12 RISE → LAB 전달 문서

---

## 1. coslab CLI 설치 및 사용법

### 설치
```bash
git clone https://github.com/passeth/coslab.git
cd coslab
npm install
npm link
export SUPABASE_INTEL_KEY="<intel 프로젝트 service_role_key>"
```

### 핵심 명령어 3가지

**성분 안전성 조회:**
```bash
coslab analyze "Niacinamide"
# → 안전성 요약, 자극/감작 등급, EU/FDA/MFDS 규제, 최대 농도
```

**제품 CPSR MoS 계산:**
```bash
coslab mos "Pro-moisture Creamy"
# → FRAIJOUR 크림 전성분 MoS 시뮬레이션
# → safe/review/no-data 분류
```

**성분 규제 체크:**
```bash
coslab regulate "Retinol"
# → CosIng Annex II/III + EU/FDA/MFDS 멀티 규제
```

**JSON 출력** (프로그래밍용):
```bash
coslab analyze "Niacinamide" --json
coslab mos "크림" --json
```

---

## 2. 어제~오늘 한 작업 요약 (2026-03-11~12)

### AIaly 프로젝트 — 화장품 성분 Knowledge Graph
- **Neo4j KG 구축 완료**: 1,320 성분 × 1,000 제품 × 673 브랜드 × 28 기능
- **Gemini Embedding 2 적용**: 전체 성분 3072-dim 벡터 임베딩 완료
- **YouTube → 성분 매칭 파이프라인**: 영상 자막에서 토픽 추출 → InfraNodus 분석 → Gemini 벡터로 성분 시멘틱 매칭
- **핵심 기술**: Contextual Query — `"cosmetic skincare ingredient for {개념}"` 전처리로 정확도 대폭 향상

### AI-Driven CPSR/PIF 자동화 리서치
밤새 자율 리서치 수행 (Karpathy autoresearch 패턴). 핵심 발견:

**CPSR 구조 (EU 1223/2009 Annex I):**
- Part A: 제품 정보, 전성분, 물리화학적 특성, 안정성, 미생물, 불순물, 포장, 노출평가, 독성 프로파일
- Part B: Safety Assessor의 MoS 계산 기반 안전성 판정 + 서명

**MoS 공식 (SCCS 11th revision):**
```
MoS = PoDsys / SED
SED = Eproduct × C/100 × DA/100
PoDsys = NOAEL × oral_bioavailability (기본 50%)

MoS ≥ 100 → 안전
```
- Eproduct: 제품 유형별 일일 노출량 (face cream 24.53 mg/kg bw/day)
- C: 성분 농도 (%)
- DA: 피부흡수율 (%)
- NOAEL: 무독성량 (mg/kg bw/day)

**PoC 결과 (FRAIJOUR Pro-moisture Creamy):**
- 13개 핵심 성분 중 9개(69%) 즉시 MoS 계산 가능
- 4개 NOAEL 부재 → TTC(Cramer Class) 적용 필요
- 모든 계산 성분 MoS ≥ 100 (안전)

**발견한 외부 도구/논문:**
| 도구 | 내용 |
|------|------|
| AutoPIF™ | LLM + Rules Engine으로 PIF 자동 생성 (ScienceDirect 2025) |
| TOXIN KG | RDF 기반 88개 성분 독성 Knowledge Graph (Oxford 2025) |
| Cosmedesk | SaaS — SED/MoS 자동 계산 |
| OECD QSAR Toolbox | 무료 — in silico 독성 예측 |
| COSMOS DB | 552개 화합물 TTC 데이터셋 |

### coslab CLI 탄생
위 리서치 결과를 CLI 도구로 구현. 에바스 자체 DB(1,320 성분 + CosIng 규제)를 활용하여 성분 분석, MoS 계산, 규제 체크를 터미널에서 수행.

---

## 3. LAB 봇 활용 시나리오

### 일상 업무
```bash
# 신규 원료 안전성 빠른 체크
coslab analyze "Bakuchiol"

# 신제품 개발 시 전성분 안전성 스크리닝
coslab mos "Heartleaf Blemish Cream" --json

# 수출 전 규제 확인
coslab regulate "Phenoxyethanol"
```

### CPSR 작업 보조
```bash
# 제품 전성분 MoS 일괄 계산
coslab mos "제품명" --json > mos_result.json

# 결과를 safety-oracle에게 전달하여 CPSR Part B 초안 생성
```

### 향후 연동 (Phase 2~3)
- `coslab graph "Retinol"` → Neo4j에서 연관 성분/제품/규제 조회
- `coslab trend "anti-aging serum"` → DEXTER COS 트렌드 분석
- `coslab formulate --target "brightening cream"` → 시지푸스 처방 추천

---

## 4. 참고 링크

- GitHub: https://github.com/passeth/coslab
- CPSR 리서치 Gist: https://gist.github.com/passeth/b92005411d3748a809d8878fbfe36c47
- AIaly 리서치 Gist: https://gist.github.com/passeth/d93a0cccd43cc3f3bda45670bcb6dcc3

---

*작성: RISE (2026-03-12)*
