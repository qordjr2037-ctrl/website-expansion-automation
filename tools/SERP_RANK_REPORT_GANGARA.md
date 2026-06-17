# gangara.co.kr SERP 순위 실측 — 2026-06-17

## 결론 (3키워드)

| 키워드 | gangara.co.kr 순위 | 비고 |
|--------|-------------------|------|
| 강남 가라오케 | **미노출** (30위 밖) | DDG lite 30건 스캔 |
| 강남 풀싸롱 | **미노출** (30위 밖) | DDG lite 30건 스캔 |
| 강남 하이퍼블릭 | **미노출** (30위 밖) | DDG lite 30건 스캔 |

**브랜드 검색 `gangara.co.kr`**, **site:gangara.co.kr** — Cloud Runner에서 DDG/Bing 봇 차단으로 재확인 불가.  
한국 IP·Google Search Console에서 `site:gangara.co.kr` 직접 확인 권장.

---

## 현재 1페이지에 뜨는 곳 (DDG sample top5)

### 강남 가라오케
1. karaokeplan.com
2. seoulafterdark.com/gangnam-karaoke-guide-2026/
3. karaokegangnam.net
4. seoulafterdark.com/gangnam-karaoke-first-time-guide/
5. theperfectkaraoke.com

### 강남 풀싸롱
1. gangnamfullssalong.com
2. gugudano.com (가격·시스템 가이드)
3. fullssawara.com
4. levelhotelsalon.com
5. classicnamu.com

### 강남 하이퍼블릭
1. gangnamkaraokeroom.com/gangnam-hyperpublic-guide/
2. gangnam-nightlife.co.kr/blog/0011.html
3. **roompang.com/guide/gangnam-hyperpublic**
4. roomhubs.com
5. gangnamhyperpublic.com

choicelounge·gangnamdalto·classicsalong 등 **SERP 벤치마크 10곳은 이 sample top5에 직접 안 보임** — 키워드·지역·엔진별 변동 큼.

---

## 라이브 gangara.co.kr 상태 (2026-06-17 fusion 배포 후)

| 항목 | live (배포 후) | fusion 목표 |
|------|----------------|-------------|
| H1 | `강남 가라오케 · 하이퍼블릭 · 풀싸롱 · 쩜오 2026 완벽 가이드` ✅ | ✅ |
| canonical | `https://gangara.co.kr/` ✅ | ✅ |
| robots sitemap | co.kr ✅ | ✅ |
| sitemap URL 수 | **5개** ✅ | 5 |
| fusion 배포 | **live 반영** ✅ | templates/gangara-hub/ |

→ **온페이지 fusion 완료.** SERP 미노출은 백링크·인덱스 단계 (Phase 3 PC 배포).

---

## 라이브 gangara.co.kr 상태 (배포 전 — 참고)

| 항목 | 라이브 (구버전) | fusion 템플릿 (repo) |
|------|-----------------|----------------------|
| H1 | `강남 가라오케 01025949736` ❌ | `{키워드} 2026 완벽 가이드` ✅ |
| canonical | gangara.**netlify.app** ❌ | gangara.co.kr ✅ |
| fusion 배포 | **미배포** | templates/gangara-hub/ |

---

## 백링크 실험 baseline

- DR 2 · RD 46 · BL 389 (SST)
- postheaven NF 스팸 링크 多 → directory 인용 거의 없음
- sync 큐 30건 (roompang P0 포함) — **배포 전**

---

## 다음 측정

```bash
python3 tools/serp_rank_probe.py --merge-experiment   # DDG (한국 IP PC 권장)
python3 tools/serp_rank_probe_deep.py --merge-experiment
```

Google 정확도: Search Console → Performance / `site:gangara.co.kr` 수동 검색
