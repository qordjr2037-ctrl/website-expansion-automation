# -*- coding: utf-8 -*-
"""가설 → 실험 → 결과(일치/불일치) 학습 보고 포맷."""
from __future__ import annotations

from typing import Any

HYPOTHESIS_CATALOG: dict[str, dict[str, Any]] = {
    "backlink_quality_disavow_spam": {
        "title": "스팸 백링크 정리 + 고품질 citation 배포",
        "statement": (
            "RD {rd}개지만 샘플의 {spam:.0%}가 postheaven·web2 스팸이다. "
            "스팸을 pool에서 제거하고 directory·guide_hub(Tier S/A)를 PC Browser로 live 배포하면 "
            "SERP 노출이 시작될 것이다."
        ),
        "experiment_actions": [
            "placements_master 스팸 도메인 purge",
            "SERP 1페이지 URL → learning_seeds 주입",
            "directory·guide_hub sync·deploy_queue 갱신",
            "min_trait_score 상향으로 저품질 placement 제외",
        ],
        "success_signals": ["SERP top10 ≥1키워드", "deploy_queue live citation 반영", "스팸 비율 감소"],
    },
    "backlink_volume_and_type": {
        "title": "RD 격차 메우기 — directory·guide_hub 볼륨",
        "statement": (
            "경쟁사 중위 RD {rd_target} 대비 gap {rd_gap:+.0f}. "
            "directory·guide_hub 백링크를 {rd_target} RD 수준까지 늘리면 SERP 상승이 시작될 것이다."
        ),
        "experiment_actions": [
            "SERP 경쟁 URL 시드 수집",
            "sync pool 확장·키워드 coverage 균형",
            "Tier S/A deploy_queue 생성",
        ],
        "success_signals": ["pool·sync 증가", "RD gap 축소", "SERP rank 개선"],
    },
    "index_and_deploy_directory": {
        "title": "인덱스 + Tier S directory live 배포",
        "statement": (
            "SERP 0/3 — fusion은 live지만 citation·인덱스가 없다. "
            "GSC sitemap 제출 + roompang 등 Tier S PC Browser 배포 후 SERP 진입이 시작될 것이다."
        ),
        "experiment_actions": [
            "deploy_queue Tier S/A 18건 생성",
            "GSC sitemap·site: 검색 확인 권고",
            "fusion canonical·내부링크 유지",
        ],
        "success_signals": ["site: 인덱스 페이지 증가", "SERP rank 출현", "deploy live href 확인"],
    },
    "backlink_quality_and_type": {
        "title": "백링크 유형·품질 최적화",
        "statement": (
            "directory·guide_hub 중심 고품질 citation을 RD {rd_target}까지 쌓으면 "
            "3키워드 SERP 상승이 시작될 것이다."
        ),
        "experiment_actions": ["platform_type 필터·trait_score 기준 적용", "sync export·collect 1회"],
        "success_signals": ["고품질 pool 비율 상승", "SERP rank 개선"],
    },
    "maintain_and_expand": {
        "title": "top10 유지·확장",
        "statement": "이미 top10 {in_top10}/3 — citation 유지·추가 키워드 확장으로 순위를 방어·상승시킬 것이다.",
        "experiment_actions": ["기존 citation 유지", "미달 키워드 추가 배포"],
        "success_signals": ["top10 키워드 유지", "추가 키워드 top10 진입"],
    },
}


def _fmt_statement(hyp_id: str, cmp: dict, in_top10: int) -> str:
    meta = HYPOTHESIS_CATALOG.get(hyp_id, HYPOTHESIS_CATALOG["backlink_quality_and_type"])
    tpl = meta["statement"]
    you = cmp.get("you") or {}
    return tpl.format(
        rd=you.get("rd", "?"),
        spam=cmp.get("spam_sample_ratio", 0),
        rd_target=cmp.get("rd_target", "?"),
        rd_gap=cmp.get("rd_gap_to_median", 0),
        in_top10=in_top10,
    )


def _rank_delta(prev: dict | None, curr: dict) -> dict[str, str]:
    prev = prev or {}
    out: dict[str, str] = {}
    for kw, rank in (curr.get("ranks") or {}).items():
        pr = prev.get("ranks", {}).get(kw) if prev else None
        if rank is None and pr is None:
            out[kw] = "미노출 → 미노출"
        elif rank is None:
            out[kw] = f"rank {pr} → 미노출"
        elif pr is None:
            out[kw] = f"미노출 → rank {rank}"
        elif rank < pr:
            out[kw] = f"rank {pr} → {rank} (↑)"
        elif rank > pr:
            out[kw] = f"rank {pr} → {rank} (↓)"
        else:
            out[kw] = f"rank {rank} (유지)"
    return out


def evaluate_experiment(
    hyp_id: str,
    hyp: dict,
    cmp: dict,
    cycle_rec: dict,
    prev_cycle: dict | None,
    *,
    deploy_queue_pending: int,
    fusion_live: bool,
    pool_total: int | None,
    sync_count: int | None,
) -> dict[str, Any]:
    meta = HYPOTHESIS_CATALOG.get(hyp_id, HYPOTHESIS_CATALOG["backlink_quality_and_type"])
    in_top10 = int(cycle_rec.get("serp_in_top10") or 0)
    statement = hyp.get("statement_ko") or _fmt_statement(hyp_id, cmp, in_top10)
    statement_full = _fmt_statement(hyp_id, cmp, in_top10)

    rank_changes = _rank_delta(prev_cycle, cycle_rec)
    seeds_added = int(cycle_rec.get("seeds_added") or 0)
    patches = cycle_rec.get("patches") or []
    deploy_queue = int(cycle_rec.get("deploy_queue") or deploy_queue_pending)

    matched: list[str] = []
    diverged: list[str] = []
    blockers: list[str] = []

    # SERP
    if hyp_id == "maintain_and_expand":
        if in_top10 >= 1:
            matched.append(f"SERP top10 {in_top10}/3 — top10 구간 유지·확장 가설과 일치")
        else:
            diverged.append(f"SERP top10 {in_top10}/3 — top10 이탈, 가설과 다름")
    else:
        if in_top10 >= 1:
            matched.append(f"SERP top10 {in_top10}/3 — 가설대로 순위 진입 시작")
        else:
            diverged.append(f"SERP top10 {in_top10}/3 — 가설 예측(≥1키워드 top10) 미달")

    # Deploy queue
    if deploy_queue_pending >= 10 and hyp_id in (
        "backlink_quality_disavow_spam",
        "index_and_deploy_directory",
        "backlink_volume_and_type",
    ):
        blockers.append(
            f"Browser deploy_queue {deploy_queue_pending}건 미배포 — live citation 미반영으로 SERP 변화 지연"
        )
        diverged.append("deploy live citation — queue만 쌓이고 PC Browser 배포 미실행")
    elif deploy_queue_pending < deploy_queue:
        matched.append(f"deploy_queue {deploy_queue}→{deploy_queue_pending}건 감소 — 배포 진행")

    # Pool / collect
    if seeds_added > 0:
        matched.append(f"SERP 시드 {seeds_added}건 주입 — 경쟁 URL 기반 수집 확장")
    if "placements_master purged" in " ".join(patches):
        matched.append("스팸 placement purge 실행 — pool 품질 개선")
    if sync_count and pool_total:
        matched.append(f"sync {sync_count} / pool {pool_total} — 수집·export 파이프라인 동작")

    if fusion_live and hyp_id == "index_and_deploy_directory":
        matched.append("fusion live ✅ — 온페이지 기반은 가설대로 준비됨")
    elif not fusion_live:
        blockers.append("fusion 미배포 — 온페이지 기반 부재")

    # Verdict
    if in_top10 >= 1 and not blockers:
        verdict = "confirmed"
        verdict_ko = "가설대로"
        summary_ko = (
            f"cycle {cycle_rec.get('cycle', '?')}에서 「{meta['title']}」 가설을 실험했고, "
            f"**가설대로** SERP top10 {in_top10}/3 결과가 나왔습니다."
        )
    elif blockers and in_top10 == 0:
        verdict = "blocked"
        verdict_ko = "가설 검증 불가(실행 병목)"
        summary_ko = (
            f"cycle {cycle_rec.get('cycle', '?')}에서 「{meta['title']}」 가설을 실험했지만, "
            f"**가설과 다르게** SERP는 여전히 0/3입니다. "
            f"수집·purge는 진행됐으나 **{blockers[0]}** 때문에 citation live 반영이 없어 가설 검증이 지연됐습니다."
        )
    elif in_top10 == 0 and not rank_changes_improved(rank_changes):
        verdict = "rejected"
        verdict_ko = "가설과 다르게"
        summary_ko = (
            f"cycle {cycle_rec.get('cycle', '?')}에서 「{meta['title']}」 가설을 실험했지만, "
            f"**가설과 다르게** SERP·순위 변화가 없었습니다. "
            f"다음 cycle에서 가설 수정 또는 실험 조건(배포·인덱스) 보완이 필요합니다."
        )
    else:
        verdict = "partial"
        verdict_ko = "부분 일치"
        summary_ko = (
            f"cycle {cycle_rec.get('cycle', '?')}에서 「{meta['title']}」 가설을 실험했고, "
            f"일부 지표는 가설대로(수집·pool) 움직였지만 SERP 목표는 아직 미달입니다."
        )

    return {
        "hypothesis_id": hyp_id,
        "hypothesis_title": meta["title"],
        "hypothesis_statement": statement,
        "hypothesis_statement_full": statement_full,
        "experiment_actions": meta["experiment_actions"],
        "cycle_actions": {
            "seeds_added": seeds_added,
            "deploy_queue": deploy_queue,
            "patches": patches,
        },
        "success_signals": meta["success_signals"],
        "matched": matched,
        "diverged": diverged,
        "blockers": blockers,
        "rank_changes": rank_changes,
        "verdict": verdict,
        "verdict_ko": verdict_ko,
        "summary_ko": summary_ko,
    }


def rank_changes_improved(rank_changes: dict[str, str]) -> bool:
    for v in rank_changes.values():
        if "(↑)" in v or ("미노출 → rank" in v):
            return True
    return False


def render_experiment_markdown(d: dict) -> str:
    exp = d.get("experiment") or {}
    rank_lines = "\n".join(
        f"| {kw} | {r if r else '미노출'} | {'✅' if r and r <= 10 else '❌'} |"
        for kw, r in d.get("serp_ranks", {}).items()
    )
    rank_delta_lines = "\n".join(f"- **{kw}**: {chg}" for kw, chg in (exp.get("rank_changes") or {}).items())
    matched_lines = "\n".join(f"- ✅ {m}" for m in exp.get("matched") or []) or "- (없음)"
    diverged_lines = "\n".join(f"- ❌ {x}" for x in exp.get("diverged") or []) or "- (없음)"
    blocker_lines = "\n".join(f"- ⚠️ {b}" for b in exp.get("blockers") or []) or "- (없음)"
    action_lines = "\n".join(f"- {a}" for a in exp.get("experiment_actions") or [])
    cycle_patch = exp.get("cycle_actions") or {}
    patch_lines = "\n".join(f"- {p}" for p in cycle_patch.get("patches") or []) or "- —"
    next_actions = "\n".join(f"- {a}" for a in d.get("next_actions", []))

    return f"""# gangara 학습 실험 보고 — {d['generated_at']}

## 한 줄 요약
{exp.get('summary_ko', '—')}

**판정:** {exp.get('verdict_ko', '—')} | SERP top10: **{d['serp_top10']}** | cycle **{d.get('learning_cycle', '?')}**

---

## 1. 실험한 가설
**「{exp.get('hypothesis_title', '—')}」** (신뢰도 {d.get('hypothesis_confidence', '?')})

{exp.get('hypothesis_statement_full') or exp.get('hypothesis_statement') or d.get('hypothesis_ko', '—')}

---

## 2. 이번 cycle에서 한 실험 (cycle {d.get('learning_cycle', '?')})
{action_lines}

**실행 내역:**
- SERP 시드 주입: {cycle_patch.get('seeds_added', 0)}건
- deploy_queue: {cycle_patch.get('deploy_queue', d.get('deploy_queue_pending', 0))}건
- 코드·설정 패치:
{patch_lines}

---

## 3. 결과 — 가설과 비교

### 가설대로 나온 것
{matched_lines}

### 가설과 다르게 나온 것
{diverged_lines}

### 병목 (가설 검증 지연)
{blocker_lines}

### SERP 순위
| 키워드 | rank | top10 |
|--------|------|-------|
{rank_lines}

**전 cycle 대비:**
{rank_delta_lines or '- (이전 cycle 없음)'}

---

## 4. 다음 실험 방향
{next_actions or '- —'}

sync {d.get('sync_count')} / pool {d.get('pool_total')} · Browser 배포 대기 **{d.get('deploy_queue_pending')}건**
fusion live: {'✅' if d.get('fusion_live') else '❌'}

---
프롬프트: `tools/CURSOR_BROWSER_DEPLOY_QUEUE_PROMPT.md`
"""
