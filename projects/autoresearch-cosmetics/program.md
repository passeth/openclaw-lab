# program.md — Cosmetics AutoResearch Framework

> autoresearch (karpathy) 컨셉을 화장품 R&D에 적용한 자율 연구 프레임워크

## 컨셉

원본 autoresearch가 `train.py`를 반복 수정 → 학습 → 평가하듯,
화장품 연구에서는 **가설 → 문헌/데이터 조사 → 분석 → 평가 → 반복** 사이클을 돌린다.

## 연구 사이클 (1회 = 1 experiment)

```
1. 가설 설정 (Hypothesis)
   → 검증 가능한 구체적 질문 1개

2. 탐색 (Search)
   → 논문, 특허, 규제 DB, 제품 DB, 원료 DB 검색
   → 최소 3개 이상 소스

3. 분석 (Analyze)
   → 수집 데이터 구조화
   → 상충 정보 식별 및 교차 검증

4. 평가 (Evaluate)
   → 가설 지지/반박 판정
   → 신뢰도 스코어 (1-5)
   → 실무 적용 가능성 판정

5. 다음 가설 도출 (Next)
   → 이번 결과에서 파생된 새 질문
   → 반복
```

## 메트릭

- **신뢰도 (Confidence):** 1-5 (소스 수, 일관성, 최신성)
- **실무 적용도 (Actionability):** 즉시 적용 / 추가 검증 필요 / 참고만
- **커버리지 (Coverage):** 해당 주제의 탐색 완료도 (%)

## 출력

각 experiment → `experiments/EXP-{번호}.md`
최종 종합 → `report.md`

## 규칙

- 1 experiment = 1 가설, 1 결론
- 불확실한 건 불확실하다고 명시
- 출처 반드시 기록
- 실무 권장사항은 근거와 함께
