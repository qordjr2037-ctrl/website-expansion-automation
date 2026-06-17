# GANGARA Fusion Spec — 2026-06-17 Run

SERP 1페이지 벤치마크 10곳 **장점만** fusion → `gangara.co.kr` 허브 + Track B 백링크 무한 수집.

---

## 1. 10곳 장점 → fusion 매핑

| # | 벤치마크 | 가져온 장점 | fusion 반영 위치 |
|---|----------|-------------|------------------|
| 1 | choicelounge.co.kr | guide_hub · 8매장 카드 · 하부URL · 비교표 · FAQ · 타임라인 | `index.html` + 4 subpages |
| 2 | gangnamdalto.co.kr | NAP HTML표 · 통계·신뢰 숫자 · FAQ · 가격표 | `index.html` |
| 3 | classicsalong.com | 실장 스토리 · 매직미러/업종 용어 · 롱폼 신뢰 | `gangnam-poolsalon.html` |
| 4 | thesevensalon.com | footer #해시태그 · 지역 롱테일 | 전 페이지 footer |
| 5 | applegangnam.com | 룸타입·시설 섹션 구조 | `gangnam-poolsalon.html` |
| 6 | gangnammirror.com | 문자/카톡 예약 CTA 퍼널 | subpages CTA |
| 7 | gangnamko.co.kr | Q&A·매거진형 → FAQ+하부링크 허브 | 전 페이지 FAQ+nav |
| 8 | garaoke.clickn.co.kr | 다점포 → co.kr 하부 URL (SaaS 대신 자체 HTML) | 4 subpages |
| 9 | richhuang.co.kr | **장점 없음 — 복사 금지** | — |
| 10 | roompang.com | 업소 디렉터리 인용 표면 (사이트 밖 P0) | Track B 등록 |

**복사 금지:** richhuang 키워드 과밀 · Pepyaka 1MB+ · H1=전화 · clickn 빈템플릿 · netlify sitemap · postheaven NF 스팸

---

## 2. 페이지별 Fusion 스펙

| 페이지 | title | H1 | 섹션 | 내부링크 | Schema | CTA |
|--------|-------|-----|------|----------|--------|-----|
| `/` index | 강남 가라오케·하이퍼블릭·풀싸롱·쩜오 2026 완벽 가이드 | `{키워드} 2026 완벽 가이드` 문장형 | 허브카드·통계·비교표·가격표·NAP·타임라인·스토리·FAQ·tags | nav 5 + 카드 4 | LocalBusiness + FAQPage 8Q | hero 1 + 하단 1 |
| gangnam-garaoke | 강남 가라오케 2026 가격·예약 | 강남 가라오케 완벽 가이드 2026 | 가격·NAP·FAQ 8 | hub+3 sub | FAQPage | 1 |
| gangnam-hyperbolic | 강남 하이퍼블릭 2026 가격·초이스 | 강남 하이퍼블릭 완벽 가이드 2026 | 비교표·가격·FAQ 8 | hub+3 sub | FAQPage | 1 |
| gangnam-poolsalon | 강남 풀싸롱 2026 룸타입 | 강남 풀싸롱 룸타입별 가이드 2026 | 룸타입표·스토리·가격·NAP·FAQ 8 | hub+2 sub | FAQPage | 1 |
| gangnam-jjom | 강남 쩜오 2026 | 강남 쩜오 이용 안내 2026 | 비교표·FAQ 8 | hub+3 sub | FAQPage | 1 |

**내부링크 합계:** index↔sub 4 + sub↔sub ≥5 (요구 ≥5 충족)

---

## 3. Fusion gap 보완 체크리스트 (10/10)

| # | gap | 보완 | 상태 |
|---|-----|------|------|
| 1 | NAP 없음 | HTML 표 14행 (nap 신호 ≥15) | ✅ |
| 2 | FAQ 2개 | 아코디언 FAQ 8개+ + FAQ Schema | ✅ |
| 3 | 가격 텍스트만 | 1부/2부·TC·RT HTML 비교표 | ✅ |
| 4 | 내부링크 1 | index + 4 sub 상호링크 ≥5 | ✅ |
| 5 | roompang 미등록 | P0 directory 시드 + live 404 재등록 안내 | ⚠️ Track B 배포 대기 |
| 6 | robots/sitemap | canonical·sitemap·robots → gangara.co.kr only | ✅ |
| 7 | H1=전화번호 | H1 = `{키워드} 가이드·2026` 문장형 | ✅ |
| 8 | CTA 과밀 | 페이지당 CTA 2~3회, 하단 집중 | ✅ |
| 9 | HTML 무거움 | 정적 CSS ~3KB, lazy 이미지(미사용) | ✅ |
| 10 | DR/RD·디렉터리 | Track B directory+guide_hub 수집·sync | 🔄 Phase 2 진행 |

**fusion 체크: 8/10 통과** (roompang live·RD는 배포/인용 후 완료)

---

## 4. gangara RD 추이 (실측 2026-06-17)

| domain | DR | RD | BL |
|--------|----|----|-----|
| gangara.co.kr | 2 | 46 | 389 |
| choicelounge | 2 | 101 | 14494 |
| gangnamdalto | 5 | 556 | 6194 |
| gangnamko | 2 | 404 | 3560 |

출처: `tools/backlink_live_output.json`

---

## 5. 수정 파일

- `website 확장 수집/templates/gangara-hub/*.html`
- `website 확장 수집/templates/gangara-hub/robots.txt`
- `website 확장 수집/templates/gangara-hub/sitemap.xml`
- `website 확장 수집/misc/_program/*.py`
- `core/run_backlink_collect.py`
- `core/backlink_targets_sync.json`
- `core/backlink_deploy_status.json`
