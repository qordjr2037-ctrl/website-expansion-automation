# 백링크 인텔 보고 — cycle 6 (2026-06-19T23:07:21Z)

> **A. 원론적 방식** (SEO·Track B 코드 원리) | **B. 경쟁자 추적** (SERP·RD·페이지 분석)

---

## A. 원론적 방식 (백링크 올리는 원리)

### Track B 파이프라인
- SERP+seed → classify(reject board) → qualify(trait) → placements_master
- → pick_keyword_balanced_batch → backlink_targets_sync → deploy_queue
- → auto verify / Browser deploy → verified_store → milestone 100

### 핵심 원칙

**편집 가능 surface만 placement**
- 이론: 백링크는 '링크를 넣을 수 있는 UI'가 있는 URL만 자산. search 결과·타인 site 열람 URL은 RD에 기여 안 함.
- 코드: `placement_classifier.is_board_url → reject; run_backlink_auto SKIP_URL`

**platform_type × tier_hint**
- 이론: directory(S) > guide_hub/profile(A) > web2(B). SERP 1페이지는 roompang directory + 허브 내부링크 패턴.
- 코드: `placement_classifier PLATFORM_RULES; qualifier trait +25 directory`

**trait_score 적격 (dofollow·无captcha·SERP proximity)**
- 이론: dofollow +10, no captcha +10, SERP top10 URL +10. 40+ qualified, experiment는 70+.
- 코드: `placement_qualifier.qualify_placement()`

**키워드 균형 batch export**
- 이론: 3키워드 실험 — 부족한 키워드 placement 우선 sync 30건.
- 코드: `backlink_pool_rank.pick_keyword_balanced_batch()`

**anchor rotation**
- 이론: money_url 키워드별 landing + anchor_for_index로 앵커 분산.
- 코드: `anchor_builder.anchor_for_index() in export_sync`

**postheaven/web2 스팸 purge**
- 이론: RD 숫자만 키우면 안 됨 — 스팸 RD는 SERP 무기여. purge 후 directory/profile.
- 코드: `run_learning_loop.purge_spam_master(); SPAM_DOMAINS`

**live href 검증 = 성공 정의**
- 이론: queue done ≠ 성공. deploy_url HTML에 money domain href 존재해야 verified.
- 코드: `run_backlink_auto.process_row(); backlink_verified_store`

**1000/일 = profile farm + web2 (이론)**
- 이론: ClickN/isweb 3분/건 × 8브라우저 × 2PC ≈ 1000. directory는 볼륨小·품질大.
- 코드: `run_backlink_daily_plan DEFAULT_DAILY_QUOTA`

### 코드 모듈 (이번 스캔)

| 모듈 | doc | 핵심 함수 |
|------|-----|-----------|
| serp_backlink_collector | SERP → URL 후보 수집 (게시판 제외). DuckDuckGo li | load_volume_seeds, load_learni |
| placement_classifier | URL → platform_type 분류 (게시판 REJECT). | registrable_domain, is_board_u |
| placement_qualifier | placement 적격 판정 — dofollow·captcha hint· | _fetch_head, qualify_placement |
| export_backlink_bridge | placements_master → core/backlink_target | load_json, save_json, merge_ma |
| backlink_pool_rank | placement 풀 랭킹 — experiment 모드: S/A dire | pick_keyword_balanced_batch, s |
| run_backlink_collect | Track B 백링크 수집 1사이클 — SERP → qualify → m | load_keywords, load_json, save |
| run_backlink_auto | 백링크 자동 배포·검증 1배치. | now_iso, load_json, load_queue |
| failure_hypotheses | 실패 유형 → 다음 실험 가설 (자동 학습·보고용). | classify_failure, get_next_hyp |
| backlink_live_collect | SmallSEOTools 백링크 체커 + 2captcha(Turnstil | solve_turnstile, extract_csrf, |

---

## B. 경쟁자 추적

### RD·백링크 실측 + 홈페이지 링크 구조

| domain | RD | BL | internal | external types |
|--------|-----|-----|----------|----------------|
| choicelounge.co.kr | 101 | 14494 | 1 | {'external_other': 30, 'internal': 2} |
| gangnamdalto.co.kr | 556 | 6194 | 2 | {'external_other': 13, 'internal': 12} |
| classicsalong.com | 48 | 463 | 0 | {'external_other': 14} |
| thesevensalon.com | 93 | 386 | 0 | {'external_other': 17} |
| applegangnam.com | 113 | 264 | 0 | {'external_other': 16} |
| gangnammirror.com | 96 | 208 | 0 | {'external_other': 14} |
| gangnamko.co.kr | 404 | 3560 | 0 | {} |
| gangara.co.kr | 46 | 389 | 2 | {'external_other': 14} |

### SERP top5 surface (키워드별)

- **강남 가라오케** gangara=미노출 → top: ['seoulafterdark.com', 'karaokeplan.com', 'www.theperfectkaraoke.com', 'www.karaokegangnam.net', 'www.roompang.com']
- **강남 풀싸롱** gangara=미노출 → top: ['www.classicnamu.com', 'www.jdwroom.com', 'www.thekingmission.com', 'www.gnfull.net', 'www.sevensalong.com']
- **강남 하이퍼블릭** gangara=미노출 → top: ['gangnamkaraokeroom.com', 'gangnam-nightlife.co.kr', 'roomhubs.com', 'gangnamhyperpublic.com', 'gangnamhub.club']

### 경쟁 패턴 → gangara 적용

- **gangnamdalto.co.kr** (single_landing + roompang directory + sibling_domain 상호링크)
  → roompang 업소등록 + .co.kr 형제도메인 네트워크 (장기)
- **choicelounge.co.kr** (guide_hub 8매장 카드 → 내부 PageRank 24+ 하부 URL)
  → gangara fusion 허브 내부링크 5 URL (이미 live) + 외부 citation
- **thesevensalon.com** (중위 RD — directory+profile mix)
  → RD 98 중위 목표 — profile bulk로 수량, roompang으로 품질
- **gangara.co.kr** (postheaven 스팸 RD 100% — SERP 0/3)
  → 스팸 purge + live citation 100건 milestone

### gangara 격차

- choicelounge.co.kr RD 101 vs gangara 46 (+55)
- gangnamdalto.co.kr RD 556 vs gangara 46 (+510)
- classicsalong.com RD 48 vs gangara 46 (+2)
- thesevensalon.com RD 93 vs gangara 46 (+47)
- applegangnam.com RD 113 vs gangara 46 (+67)
- gangnammirror.com RD 96 vs gangara 46 (+50)

---

## 이번 cycle 신규 intel

- choicelounge.co.kr 외부링크 유형: {'external_other': 30, 'internal': 2}
- gangnamdalto.co.kr 외부링크 유형: {'external_other': 13, 'internal': 12}
- classicsalong.com 외부링크 유형: {'external_other': 14}
- thesevensalon.com 외부링크 유형: {'external_other': 17}
- applegangnam.com 외부링크 유형: {'external_other': 16}
- gangnammirror.com 외부링크 유형: {'external_other': 14}
- gangara.co.kr 외부링크 유형: {'external_other': 14}
- [원론] 편집 가능 surface만 placement: 백링크는 '링크를 넣을 수 있는 UI'가 있는 URL만 자산. search 결과·타인 site 열람 URL은 RD에 기여 안 함.
- [원론] platform_type × tier_hint: directory(S) > guide_hub/profile(A) > web2(B). SERP 1페이지는 roompang directory + 허브 내부링크 패턴.
- [경쟁] single_landing + roompang directory + sibling_domain 상호링크 → gangara: roompang 업소등록 + .co.kr 형제도메인 네트워크 (장기)
- [경쟁] guide_hub 8매장 카드 → 내부 PageRank 24+ 하부 URL → gangara: gangara fusion 허브 내부링크 5 URL (이미 live) + 외부 citation
- [경쟁] 중위 RD — directory+profile mix → gangara: RD 98 중위 목표 — profile bulk로 수량, roompang으로 품질

---
누적 cycle: 6 | 중지: `touch tools/BACKLINK_INTEL_STOP`
누적 파일: `tools/BACKLINK_INTEL_ACCUMULATED.json`
