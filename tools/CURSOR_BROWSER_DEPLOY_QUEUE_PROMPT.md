# Cursor Browser — 백링크 deploy_queue 배포 프롬프트

**전체 복사 → Cursor Browser 모드**

---

```
## 목표
학습 루프가 생성한 백링크 배포 큐를 live에 반영한다.
money_site: https://gangara.co.kr/
소스: repo `core/backlink_deploy_queue.json` (Tier S directory + A guide_hub)

## 배경
- SERP 3키워드 top10 = 0/3 — directory·guide_hub live citation이 병목
- Cloud 루프는 큐만 생성, **Browser로 placement URL에 링크 삽입**해야 SERP 변화 가능

---

## 큐 파일 (repo 최신 pull 후)
`core/backlink_deploy_queue.json`

각 row:
- deploy_url: 링크 넣을 페이지
- money_url: gangara.co.kr (키워드별 하부 URL)
- anchor_text: 앵커 텍스트
- platform_type: directory | guide_hub
- tier_hint: S | A

---

## Browser 작업 순序 (허락 없이 끝까지)

### P0 — Tier S directory (roompang 우선)
1. https://www.roompang.com/ 로그인 (계정 있으면)
2. 아래 URL 순서대로 gangara 링크 삽입 시도:
   - https://roompang.com/ → money: https://gangara.co.kr/gangnam-garaoke.html anchor: 강남 가라오케
   - https://roompang.com/search?q=강남+가라오케 (동일)
   - https://roompang.com/search?q=강남+풀싸롱 → money: gangnam-poolsalon.html anchor: 강남 풀싸롱
   - https://roompang.com/guide/gangnam-poolsalon
   - https://roompang.com/search?q=강남+하이퍼블릭 → gangnam-hyperbolic.html
   - https://www.roompang.com/guide/gangnam-hyperpublic
3. 업소 등록·프로필·가이드 편집 UI에서 URL+앵커 입력
4. 저장 후 해당 페이지에서 gangara.co.kr href live 확인

### P1 — Tier A guide_hub
5. https://choicelounge.co.kr/ 및 하부 (/gangnam-garaoke/, /poolsalon/, /highpublic/)
   - 본문 또는 푸터에 money_url + anchor (dofollow 가능한 위치)
6. https://clicknn.co.kr/pages/gangnampoolsalon , gangnamhyperbolic
7. https://gangnamdalto.co.kr/ , https://gangnamko.co.kr/ (편집 가능 시)

### 완료 처리
8. 배포 성공 row → queue JSON에서 status를 "done"으로 (로컬 repo)
9. 실패 row → status "failed" + 사유 메모

---

## 검증
- curl 또는 Browser로 deploy_url 열어 gangara.co.kr href 존재 확인
- https://gangara.co.kr/ fusion H1·canonical 유지 확인

## 보고 (작업 끝나면 채팅에)
- done / failed / skipped 건수
- roompang live citation OK/FAIL
- 다음: `python3 core/run_learning_loop.py --until-top10`

## 주의
- 게시판 write.php 스팸 금지
- postheaven/web2 스팸 링크 금지
- 비밀번호 채팅·commit 금지
- Track A(board-post-automation) 수정 금지
```

---

## 큐 전체 자동 반복 (Browser)

```
core/backlink_deploy_queue.json 의 rows를 status=queued 인 것부터 순서대로:
1) deploy_url 브라우저 열기
2) money_url 을 anchor_text 로 dofollow 링크 삽입 (가능한 편집 UI)
3) 저장 → live href 확인 → status done/failed 기록
4) 18건 끝날 때까지 반복, 중간에 허락 묻지 말 것
5) 완료 보고: done N, failed M, roompang OK/FAIL
```
