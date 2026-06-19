# gangara 백링크 1000/일 — 오늘 실행 플랜

생성: 2026-06-19T03:53:22Z | 목표: **1000건/일**

---

## 1. 오늘 숫자

| 항목 | 값 |
|------|-----|
| pool 총 placement | 99 |
| 오늘 배정 | 1000건 |
| platform 분포 | {'profile': 464, 'web2': 517, 'directory': 6, 'guide_hub': 13} |
| fleet | 2대 × 8브라우저 = 16 workers |
| 브라우저당/일 | ~62건 (8h 근무 기준) |

---

## 2. 플랫폼별 일일 할당

| platform | 목표/일 | pool 보유 | 실행 방법 |
|----------|---------|-----------|-----------|
| profile (ClickN·isweb) | 450 | 13 | 무료 사이트 생성 → footer 링크 |
| web2 (tistory·velog·naver) | 350 | 67 | 새 글 + dofollow 링크 |
| directory (roompang) | 80 | 6 | 업소등록 (search URL 제외) |
| guide_hub | 40 | 13 | 편집 가능한 것만 |
| comment/QA | 80 | 0 | 댓글 (볼륨·nofollow OK) |

---

## 3. 바로 실행 (PC Cursor Browser)

```bash
git pull origin cursor/gangara-faeb
python3 core/run_backlink_prepare.py --machine-id 1
# → core/backlink_deploy_queue_machine1.json 생성
```

Browser 프롬프트: `tools/CURSOR_BROWSER_DAILY_1000_PROMPT.md` 전체 복사

**P0 오늘 (기존 큐 17건):** roompang 업소등록 + choicelounge skip  
**P1 bulk (983건):** ClickN 신규 사이트 → profile 링크 반복

---

## 4. 플랫폼별 실행 절차

### profile — ClickN / isweb 프로필·무료 사이트
- 소요: ~3분/건
- 자동화: Playwright: signup → site wizard → footer HTML paste (Phase 3)
   1) https://www.clickn.co.kr/ 회원가입 (또는 isweb.co.kr)
   2) 「무료 홈페이지 만들기」→ 서브도메인 생성 (예: gangnam-gara-{n}.clickn.co.kr)
   3) 페이지 편집 → 소개/푸터/연락처에 `<a href="{money_url}">{anchor}</a>` 삽입
   4) 저장 → deploy_url에서 gangara.co.kr href live 확인
   5) verified_store에 done 기록
### web2 — 티스토리·Velog·네이버 블로그 글
- 소요: ~5분/건
- 자동화: Playwright post editor + 2captcha (Phase 3)
   1) 플랫폼 회원가입 (tistory.com / velog.io / blog.naver.com)
   2) 새 글 작성 — 제목에 키워드, 본문 300자+ 가이드 요약
   3) 본문 중 `{anchor}` → `{money_url}` dofollow 링크 1~2개
   4) 발행 → deploy_url(글 URL)에서 href 확인
### directory — roompang 등 디렉터리 업소등록
- 소요: ~8분/건
- 자동화: Browser 수동 P0 — 자동화 전 Tier S 17건 먼저
   1) https://www.roompang.com/ 로그인
   2) 업소등록 / 가이드 편집 UI (search URL은 등록폼 아님 — /guide/ 또는 홈 등록)
   3) 업소명·소개·공식 URL에 money_url + anchor
   4) 저장 후 페이지에서 gangara href 확인
### guide_hub — 경쟁 guide_hub (편집 가능한 것만)
- 소요: ~10분/건
- 자동화: 대부분 skip — pool에서 editable_only 필터
   1) deploy_url 열기 — 본인 소유·편집 권한 있는 site만
   2) choicelounge/clicknn 등 **타인 사이트 편집 불가** → skip
   3) 본인 ClickN·isweb guide 페이지는 profile과 동일 처리
### comment — 댓글·QA (nofollow 허용, 볼륨용)
- 소요: ~4분/건
- 자동화: Playwright comment form (Phase 3)
   1) ntiming.co.kr/article 등 QA·댓글 가능 URL
   2) 키워드 관련 2~3문장 + money_url (nofollow OK)
   3) 스팸 필터 회피 — 키워드별 1회/도메인


---

## 5. 오늘 배정 샘플 (상위 25건)

| # | type | keyword | deploy_url | status |
|---|------|---------|------------|--------|
| 1 | profile | 강남 풀싸롱 | https://fulllssalon.clickn.co.kr/ | queued |
| 2 | profile | 강남 풀싸롱 | https://fullssalong.clickn.co.kr/boards/11/view | queued |
| 3 | profile | 강남 가라오케 | https://gangnamhigh.clickn.co.kr/ | queued |
| 4 | profile | 강남 하이퍼블릭 | https://gangnamhyperb.clickn.co.kr/ | queued |
| 5 | profile | 강남 풀싸롱 | https://jdwroom.clickn.co.kr/boards/21/view | queued |
| 6 | profile | 강남 가라오케 | https://karaokekr.clickn.co.kr/ | queued |
| 7 | profile | 강남 가라오케 | https://www.clickn.co.kr/ | queued |
| 8 | profile | 강남 가라오케 | https://gangnamgaraoke.clickn.co.kr/ | queued |
| 9 | profile | 강남 하이퍼블릭 | https://gangnamhapeo1.clickn.co.kr/ | queued |
| 10 | profile | 강남 하이퍼블릭 | https://gangnamharper.clickn.co.kr/ | queued |
| 11 | profile | 강남 가라오케 | https://garaoke.clickn.co.kr/ | queued |
| 12 | profile | 강남 하이퍼블릭 | https://harper.clickn.co.kr/ | queued |
| 13 | profile | 강남 풀싸롱 | https://pulssalong.clickn.co.kr/ | queued |
| 14 | web2 | 강남 하이퍼블릭 | http://ellite.co.kr/ | queued |
| 15 | web2 | 강남 클럽 | http://seoulnightclub.dothome.co.kr/2026-%EA%B0%95 | queued |
| 16 | web2 | 강남 클럽 | https://a.issuekurly.co.kr/61 | queued |
| 17 | web2 | 강남 풀싸롱 | https://applegangnam.com/ | queued |
| 18 | web2 | 강남 풀싸롱 | https://classicsalong.com/ | queued |
| 19 | web2 | 강남 하이퍼블릭 | https://domamins.co.kr/ | queued |
| 20 | web2 | 서울 가라오케 | https://galaxykaraoke.co.kr/ | queued |
| 21 | web2 | 강남 풀싸롱 | https://gangara.co.kr/ | queued |
| 22 | web2 | 강남 풀싸롱 | https://gangnam-fullssa.com/ | queued |
| 23 | web2 | 강남 가라오케 | https://gangnam-garaoke.com/ | queued |
| 24 | web2 | 강남 하이퍼블릭 | https://gangnam-highpublic.com/ | queued |
| 25 | web2 | 강남 하이퍼블릭 | https://gangnam-nightlife.co.kr/blog/0011.html | queued |

… 전체 1000건 → `tools/BACKLINK_EXECUTE_TODAY.json`

---

## 6. 명령어

```bash
# 수집 (pool 확장)
python3 core/run_backlink_collect.py

# 일일 플랜 재생성
python3 core/run_backlink_daily_plan.py --target 1000

# PC N번 머신 큐
python3 core/run_backlink_prepare.py --machine-id 1

# 배포 후 검증 (Phase 3)
python3 core/run_backlink_verify.py --today
```

상세: `core/BACKLINK_1000_DAY_PLAYBOOK.md`
