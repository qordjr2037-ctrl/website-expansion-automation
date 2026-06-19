# gangara 학습 루프 보고 — 2026-06-19T00:32:27Z

## SERP (목표: 3키워드 top10)
**현재:** 0/3 | **goal_met:** False

| 키워드 | rank | top10 |
|--------|------|-------|
| 강남 가라오케 | 미노출 | ❌ |
| 강남 풀싸롱 | 미노출 | ❌ |
| 강남 하이퍼블릭 | 미노출 | ❌ |

## 가설 (cycle 5)
RD 46 but spam 100% — quality+deploy.

## 큐·풀
- sync: 30 / pool: 92
- **Browser 배포 대기:** 18건 (`core/backlink_deploy_queue.json`)
- fusion live: ✅
- PC deploy 필요: ⚠️ 예

## 다음 액션
- [cycle 5] PC Browser: core/backlink_deploy_queue.json 18건 배포
- [cycle 5] GSC sitemap + site:gangara.co.kr
- python3 core/run_learning_loop.py --until-top10 (SERP 0/3 top10)

## 재실행
```bash
python3 core/run_learning_loop.py --until-top10 --max-cycles 5
python3 core/run_learning_report.py --email
```

프롬프트: `tools/CURSOR_BROWSER_DEPLOY_QUEUE_PROMPT.md`
