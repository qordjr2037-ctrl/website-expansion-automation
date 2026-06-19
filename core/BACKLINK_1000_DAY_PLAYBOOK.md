# gangara.co.kr — 백링크 1000건/일 실행 플레이북

> Track B 전용. board-post-automation(Track A) 수정 금지.

## 현실 점검

| 현재 | 1000/일 목표 |
|------|-------------|
| pool ~99 placement | **≥2000** qualified pool 필요 |
| deploy_queue 17건 (수동 Browser) | **자동+병렬** 8브라우저×N대 |
| directory 6건 | bulk는 **profile+web2** |
| Phase 3 deploy 코드 없음 | 아래 **즉시 실행 경로** + Phase 3 로드맵 |

**1000/일 = 8시간 근무 기준 브라우저당 ~125건 → ClickN/isweb 3분/건이면 이론상 가능. PC 1대(8브라우저)만으론 ~640건/일 → 2대 또는 12h shift 권장.**

---

## 즉시 실행 (오늘부터)

### Step 0 — repo pull
```bash
git pull origin cursor/gangara-faeb
python3 core/run_backlink_daily_plan.py --target 1000
python3 core/run_backlink_prepare.py --machine-id 1
```

### Step 1 — P0 고품질 17건 (SERP용, 먼저)
`tools/CURSOR_BROWSER_DEPLOY_QUEUE_PROMPT.md`  
- roompang **업소등록** (search?q= URL은 편집 불가 → skip)  
- 본인 ClickN 사이트만 편집  
- choicelounge 등 **타인 site 편집 skip**

### Step 2 — P1 bulk profile 450건/일
**ClickN 무료 사이트 (가장 빠름)**

1. https://www.clickn.co.kr/ 로그인/가입  
2. 「무료 홈페이지」→ 서브도메인 `gangnam-{키워드}-{번호}.clickn.co.kr`  
3. 템플릿 선택 → **소개/푸터** HTML:
   ```html
   <a href="https://gangara.co.kr/gangnam-garaoke.html">강남 가라오케</a>
   ```
4. 저장 → URL 방문해 href 확인  
5. `status: done` 기록  

**isweb.co.kr** 동일 — 1페이지 LP + gangara 링크

### Step 3 — P2 web2 350건/일
| 플랫폼 | 가입 | 글 작성 |
|--------|------|---------|
| tistory.com | 카카오 | 키워드 가이드 300자+ + money_url |
| velog.io | GitHub/이메일 | 동일 |
| blog.naver.com | 네이버 | 동일 |

앵커: 키워드별 `gangnam-*.html` 하부 URL  
**postheaven/blogspot 스팸 금지** (learning loop purge 대상)

### Step 4 — P3 directory 80건/일
- roompang 업소등록 (키워드별 반복)  
- tripadvisor/korea.kr — 해당 UI 있을 때만  
- **search 결과 URL에 링크 삽입 시도 금지**

### Step 5 — 검증
```bash
# Phase 3 스텁 — href live 확인
python3 core/run_backlink_verify.py --sample 20
```

---

## Fleet (N대 PC)

| machines | browsers | workers | 1000/일 달성 |
|----------|----------|---------|--------------|
| 1 | 8 | 8 | ~640~800 (profile 위주) |
| 2 | 8 | 16 | **1000+** |
| 4 | 8 | 32 | 2000+ (여유) |

```bash
# PC 1
MACHINE_ID=1 python3 core/run_backlink_prepare.py
# PC 2
MACHINE_ID=2 python3 core/run_backlink_prepare.py --machines 2
```

---

## pool 확장 (수집)

```bash
python3 core/run_backlink_collect.py   # SERP+시드 → placements_master
```

`website 확장 수집/misc/data/backlink_volume_seeds.txt` — bulk signup 플랫폼 시드  
목표: pool **2000+** (profile/web2 위주)

---

## Phase 3 자동화 (다음 구현)

| 파일 | 역할 |
|------|------|
| `run_backlink_auto.py` | Playwright 큐 순회 |
| `adapters/profile_clickn.py` | ClickN signup+footer |
| `adapters/web2_post.py` | tistory/velog 글 |
| `verified_store.json` | done/failed + live href |
| `run_backlink_verify.py` | 배포 후 href fetch |

2captcha: `tools/secrets_loader.py` → TWOCAPTCHA_API_KEY

---

## 키워드 → money_url

| 키워드 | money_url | anchor 예 |
|--------|-----------|-----------|
| 강남 가라오케 | /gangnam-garaoke.html | 강남 가라오케 |
| 강남 풀싸롱 | /gangnam-poolsalon.html | 강남 풀싸롱 |
| 강남 하이퍼블릭 | /gangnam-hyperbolic.html | 강남 하이퍼블릭 가이드 |

---

## 금지

- 게시판 write.php 스팸 (board reject)  
- postheaven/web2 저품질 스팸 (purge 대상)  
- 타인 guide_hub 무단 편집  
- 비밀번호 commit/채팅

---

## 매일 루틴

```
06:00  run_backlink_daily_plan.py --target 1000
06:05  run_backlink_prepare.py (각 PC)
06:10  Browser bulk 시작 (8 parallel)
18:00  verify + done/failed 집계
18:05  run_learning_loop.py --until-top10 (SERP 재측정)
```

3시간 Gmail 학습 보고는 기존 스케줄 유지.
