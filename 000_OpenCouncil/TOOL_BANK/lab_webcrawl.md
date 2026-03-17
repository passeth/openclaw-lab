# 🌐 웹 크롤링 / 정보 수집 도구

## 개요
원료 정보, 트렌드 분석, 경쟁사 처방 연구에 사용하는 웹 수집 도구 모음.

## 등록 에이전트
- **LAB** (주 사용자)

## 포함 도구

### 1. defuddle (웹 본문 추출)
```bash
npx defuddle parse <url> --markdown
# 노이즈 없는 본문만 추출
```
- 문서: https://defuddle.md/docs
- 설치: `npm install defuddle`
- 활용: 논문 초록, 원료사 제품 설명 추출

### 2. Scrapling (스킬)
- 위치: `~/.openclaw/workspace/skills/scrapling-official/`
- 특징: anti-bot 우회 내장, Playwright 기반
- 활용: 동적 페이지 크롤링 (쇼핑몰, 성분 DB)

```python
# 예시
from scrapling import Fetcher
fetcher = Fetcher()
page = fetcher.fetch("https://example.com")
```

### 3. web_fetch / web_search (OpenClaw 기본)
```
web_search(query="Bakuchiol safety SCCS opinion 2025")
web_fetch(url="https://pubmed.ncbi.nlm.nih.gov/...")
```
- 빠른 정보 수집에 활용
- PDF 논문 초록 접근

### 4. ARPT 파이프라인 (고급)
- 위치: `/projects/arpt/`
- Playwright + Supabase 연동
- 대규모 성분/제품 데이터 수집 자동화

## 주요 크롤링 대상
| 소스 | 내용 | 도구 |
|---|---|---|
| PubMed | 성분 임상 논문 | web_fetch |
| CosIng EU | 규제 정보 | web_fetch / coslab |
| SCCS 공식 사이트 | Safety Opinions | web_fetch |
| 화장품 브랜드 사이트 | 처방 트렌드 | Scrapling |
| Mintel GNPD | 신제품 트렌드 | browser |

## 업데이트
- 2026-03-12: ARPT 파이프라인 구축 중
