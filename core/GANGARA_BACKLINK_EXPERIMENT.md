# gangara.co.kr 백링크 집중 실험 — 프로토콜

## 가설

**gangara.co.kr 단일 사이트**에 directory(P0) + guide_hub(P1) + profile(P2) 백링크를 몰아 넣으면,
3키워드(강남 가라오케·풀싸롱·하이퍼블릭) SERP 순위가 상승한다.

DR 50+ 필수 아님. choicelounge·gangnamdalto 격차는 **고품질 RD·디렉터리 인용** 쪽.

---

## 실험 설정

| 항목 | 값 |
|------|-----|
| money_url | `https://gangara.co.kr/` |
| 키워드 | 강남 가라오케 · 강남 풀싸롱 · 강남 하이퍼블릭 |
| 앵커 | exact 40% · partial 30% · brand 20% · naked 10% |
| landing | 키워드별 하부 URL (garaoke / poolsalon / hyperbolic) |
| platform 우선 | directory > guide_hub > profile (web2 후순위) |
| 게시판 | **0건** (Track A 금지) |

---

## 실행 순서

```bash
# 1 Run = 베이스라인 + 수집 + sync
python3 core/run_gangara_experiment.py

# 순위만 주 1회
python3 tools/serp_rank_probe.py --merge-experiment

# RD 실측 (env 있으면)
python3 tools/backlink_live_collect.py --domain gangara.co.kr
```

PC 배포 워커: `core/backlink_targets_sync.json` pull → placement URL에 money_url·anchor_text 삽입.

---

## 측정 (전·후)

| 지표 | baseline (2026-06-17) | 목표 |
|------|----------------------|------|
| DR | 2 | 유지~소폭↑ |
| RD | 46 | +5~20 (directory 위주) |
| SERP (DDG) | 프로브 후 기록 | 3키워드 중 1+ top10 |
| roompang | 404 UUID | live 200 |

결과: `core/gangara_experiment.json` · `tools/serp_rank_probe_output.json`

---

## 주의

- postheaven NF 스팸 링크량 추종 **금지** — directory·guide_hub 품질 우선
- Netlify 미러는 301 → co.kr (중복 콘텐츠 방지)
- 실험 기간 동안 **다른 money URL 분산 금지** — gangara.co.kr only
