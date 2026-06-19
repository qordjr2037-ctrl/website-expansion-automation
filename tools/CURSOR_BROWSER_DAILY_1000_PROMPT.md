# Cursor Browser — 백링크 1000건/일 bulk 실행

**전체 복사 → Cursor Browser**

```
## 목표
gangara.co.kr 백링크 **오늘 1000건** (profile+web2 bulk + P0 directory)
money_site: https://gangara.co.kr/

## 소스 (pull 후)
- tools/BACKLINK_EXECUTE_TODAY.json  ← 오늘 전체 배정
- core/backlink_deploy_queue_machine1.json  ← 이 PC 담당분
- core/BACKLINK_1000_DAY_PLAYBOOK.md

---

## 키워드 → URL
| 키워드 | money_url | anchor |
| 강남 가라오케 | https://gangara.co.kr/gangnam-garaoke.html | 강남 가라오케 |
| 강남 풀싸롱 | https://gangara.co.kr/gangnam-poolsalon.html | 강남 풀싸롱 |
| 강남 하이퍼블릭 | https://gangara.co.kr/gangnam-hyperbolic.html | 강남 하이퍼블릭 가이드 |

---

## 작업 순서 (허락 없이 끝까지)

### A. P0 — Tier S directory (~17건, SERP 우선)
1. roompang.com → **업소등록** UI만 (search?q= URL skip)
2. money_url + anchor 저장 → live href 확인 → status done

### B. P1 — profile bulk (~450건) ★1000/일 핵심
반복 (목표 건수까지):
1. https://www.clickn.co.kr/ → 무료 홈페이지 만들기
2. 서브도메인: gangnam-{키워드영문}-{순번}.clickn.co.kr
3. 소개/푸터에 `<a href="{money_url}">{anchor}</a>`
4. 저장 → gangara href 확인 → done
5. isweb.co.kr 동일 패턴 alternates

### C. P2 — web2 bulk (~350건)
1. tistory.com / velog.io / blog.naver.com 새 글
2. 키워드 가이드 300자+ 본문 + money_url dofollow 1~2개
3. 발행 → done

### D. Skip 규칙
- choicelounge.co.kr 등 **타인 guide_hub 편집 skip**
- roompang search?q= skip
- postheaven/blogspot skip
- 게시판 write.php skip

### E. 완료 처리
- done/failed → queue JSON status 갱신
- verified: curl deploy_url | grep gangara.co.kr

---

## 병렬
8 Browser 탭/창 — profile signup 병렬 (계정별 분리)

## 보고
done N / failed M / skip K
```
