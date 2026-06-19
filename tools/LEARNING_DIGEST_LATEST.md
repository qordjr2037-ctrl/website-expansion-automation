# gangara 학습 실험 보고 — 2026-06-19T00:46:48Z

## 한 줄 요약
cycle 13에서 「스팸 백링크 정리 + 고품질 citation 배포」 가설을 실험했지만, **가설과 다르게** SERP는 여전히 0/3입니다. 수집·purge는 진행됐으나 **Browser deploy_queue 18건 미배포 — live citation 미반영으로 SERP 변화 지연** 때문에 citation live 반영이 없어 가설 검증이 지연됐습니다.

**판정:** 가설 검증 불가(실행 병목) | SERP top10: **0/3** | cycle **13**

---

## 1. 실험한 가설
**「스팸 백링크 정리 + 고품질 citation 배포」** (신뢰도 85%)

RD 46개지만 샘플의 100%가 postheaven·web2 스팸이다. 스팸을 pool에서 제거하고 directory·guide_hub(Tier S/A)를 PC Browser로 live 배포하면 SERP 노출이 시작될 것이다.

---

## 2. 이번 cycle에서 한 실험 (cycle 13)
- placements_master 스팸 도메인 purge
- SERP 1페이지 URL → learning_seeds 주입
- directory·guide_hub sync·deploy_queue 갱신
- min_trait_score 상향으로 저품질 placement 제외

**실행 내역:**
- SERP 시드 주입: 0건
- deploy_queue: 18건
- 코드·설정 패치:
- gangara_experiment learning_loop
- machine_config min_trait escalation

---

## 3. 결과 — 가설과 비교

### 가설대로 나온 것
- ✅ sync 30 / pool 93 — 수집·export 파이프라인 동작

### 가설과 다르게 나온 것
- ❌ SERP top10 0/3 — 가설 예측(≥1키워드 top10) 미달
- ❌ deploy live citation — queue만 쌓이고 PC Browser 배포 미실행

### 병목 (가설 검증 지연)
- ⚠️ Browser deploy_queue 18건 미배포 — live citation 미반영으로 SERP 변화 지연

### SERP 순위
| 키워드 | rank | top10 |
|--------|------|-------|
| 강남 가라오케 | 미노출 | ❌ |
| 강남 풀싸롱 | 미노출 | ❌ |
| 강남 하이퍼블릭 | 미노출 | ❌ |

**전 cycle 대비:**
- **강남 가라오케**: 미노출 → 미노출
- **강남 풀싸롱**: 미노출 → 미노출
- **강남 하이퍼블릭**: 미노출 → 미노출

---

## 4. 다음 실험 방향
- [cycle 13] PC Browser: core/backlink_deploy_queue.json 18건 배포
- [cycle 13] GSC sitemap + site:gangara.co.kr
- python3 core/run_learning_loop.py --until-top10 (SERP 0/3 top10)

sync 30 / pool 93 · Browser 배포 대기 **18건**
fusion live: ✅

---
프롬프트: `tools/CURSOR_BROWSER_DEPLOY_QUEUE_PROMPT.md`
