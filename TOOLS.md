# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Slack Channels

| 채널 ID | 용도 |
|---|---|
| C0ACJBJ156F | 대표님 (Sk Ji) 전용 |
| C0AJ55NFT8A | 연구팀장님 비공개 |
| C0AHPSNJJH5 | 연구팀 전체 (공개) |
| C0AKC33P7SB | 최규성 연구원 비공개 |

## 자주 쓰는 스킬 (qmd로 207개 전체 검색 가능)

> 시스템이 65개만 로딩하므로, 아래 목록 외 스킬은 `qmd search "[키워드]" -c skills`로 찾아서 읽기

### 🧪 화장품 R&D
| 스킬 | 용도 |
|---|---|
| `batch-calculator` | 배합 스케일링, 생산량 계산 |
| `cir-safety` | CIR 안전성 평가 조회 |
| `claim-substantiation` | 효능 클레임 입증 전략 |
| `clinical-evidence-aggregator` | 성분 임상 근거 수집/평가 |
| `concentration-converter` | 농도 단위 변환 (%, ppm, 몰) |
| `consumer-insight` | 소비자 니즈 분석 |
| `cosing-database` | EU CosIng DB 검색 |
| `formulation-calculator` | HLB, pH, 에멀전 계산 |
| `formulation-strategy` | 제형 개발 전략, 베이스 선택 |
| `ingredient-compatibility` | 성분 호환성/비호환성 분석 |
| `ingredient-deep-dive` | Hero 성분 심층 분석 |
| `irritation-predictor` | 피부/안 자극 예측 |

### 📋 PM / 제품 관리
| 스킬 | 용도 |
|---|---|
| `create-prd` | PRD 8섹션 템플릿 |
| `feature-spec` | 기능 스펙 문서 |
| `brainstorm-okrs` | OKR 설정 |
| `sprint-plan` | 스프린트 계획 |
| `outcome-roadmap` | 아웃컴 기반 로드맵 |
| `analyze-feature-requests` | 기능 요청 분석/우선순위 |
| `job-stories` | Job Story 작성 |
| `pre-mortem` | 사전 실패 분석 |
| `release-notes` | 릴리즈 노트 생성 |

### 🎯 전략 / 시장
| 스킬 | 용도 |
|---|---|
| `competitive-analysis` | 경쟁사 분석 매트릭스 |
| `competitive-battlecard` | 세일즈 배틀카드 |
| `gtm-strategy` | GTM 전략 수립 |
| `beachhead-segment` | 첫 시장 세그먼트 선정 |
| `ideal-customer-profile` | ICP 정의 |
| `business-model` | 비즈니스 모델 캔버스 |
| `ansoff-matrix` | 성장 전략 매트릭스 |

### 📊 데이터 / 분석
| 스킬 | 용도 |
|---|---|
| `ab-test-analysis` | A/B 테스트 결과 분석 |
| `cohort-analysis` | 코호트 분석 |
| `data-exploration` | 데이터셋 프로파일링 |
| `data-visualization` | 시각화 (matplotlib/plotly) |
| `dummy-dataset` | 테스트 더미 데이터 생성 |

## 웹 크롤링 / 파싱

| 도구 | 용도 |
|---|---|
| `defuddle` | 웹페이지 본문 추출 (노이즈 제거). CLI/Node/브라우저. `npx defuddle parse <url> --markdown` |

- 문서: https://defuddle.md/docs
- 설치: `npm install defuddle` (Node는 jsdom 추가)

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
