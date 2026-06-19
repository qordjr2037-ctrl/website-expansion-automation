#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자가 발전 학습 루프 — SERP 1페이지(in_top10) 달성까지 반복.

  python3 core/run_learning_loop.py                    # 1사이클
  python3 core/run_learning_loop.py --until-top10      # 3키워드 top10까지
  python3 core/run_learning_loop.py --until-top10 --max-cycles 5

루프: 측정(SERP+RD) → 가설 → 자동수정(시드·스팸·sync) → 재측정 → 성공 시 종료
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "tools/backlink_audit_output.json"
EXPERIMENT = REPO / "core/gangara_experiment.json"
STATUS = REPO / "core/backlink_deploy_status.json"
CONFIG = REPO / "core/machine_config.json"
SERP_PROBE = REPO / "tools/serp_rank_probe_output.json"
SEEDS_FILE = REPO / "website 확장 수집/misc/data/learning_seeds.json"
MASTER = REPO / "website 확장 수집/misc/data/placements_master.json"
SYNC = REPO / "core/backlink_targets_sync.json"
DEPLOY_QUEUE = REPO / "core/backlink_deploy_queue.json"

BENCHMARK_DOMAINS = [
    "choicelounge.co.kr",
    "gangnamdalto.co.kr",
    "classicsalong.com",
    "thesevensalon.com",
    "applegangnam.com",
    "gangnammirror.com",
]
TARGET = "gangara.co.kr"
KEYWORDS = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"]
SPAM_HOSTS = re.compile(r"postheaven\.net|blogspot\.com|bcbloggers\.com|ghostdeal", re.I)
CITATION_GAP_TYPES = ["directory_listing", "guide_hub", "sibling_domain"]


def _run_report(email: bool = False) -> None:
    cmd = [sys.executable, str(REPO / "core/run_learning_report.py"), "--quiet"]
    if email:
        cmd.append("--email")
    subprocess.call(cmd, cwd=str(REPO))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def serp_goal_met(serp: dict, min_keywords: int = 3) -> bool:
    results = serp.get("results") or []
    top10 = sum(1 for r in results if r.get("in_top10"))
    return top10 >= min_keywords


def measure_serp() -> dict:
    subprocess.call(
        [sys.executable, str(REPO / "tools/serp_rank_probe.py"), "--merge-experiment"],
        cwd=str(REPO),
    )
    return load_json(SERP_PROBE, {})


def sst_map(audit: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in audit.get("live_sst_summary") or []:
        if row.get("domain"):
            out[row["domain"]] = row
    for row in audit.get("reports") or []:
        d = row.get("domain")
        if d and d not in out and row.get("sst_referring_domains") is not None:
            out[d] = {
                "domain": d,
                "dr": row.get("sst_dr"),
                "referring_domains": row.get("sst_referring_domains"),
                "backlinks_total": row.get("sst_backlinks_total"),
                "sample_backlinks": row.get("sst_sample_backlinks") or [],
            }
    return out


def measure_backlinks() -> dict[str, dict]:
    return sst_map(load_json(AUDIT, {}))


def compare(you: dict, peers: dict[str, dict]) -> dict:
    peer_rds = [p["referring_domains"] for p in peers.values() if p.get("referring_domains")]
    peer_drs = [p["dr"] for p in peers.values() if p.get("dr") is not None]
    peer_bls = [p["backlinks_total"] for p in peers.values() if p.get("backlinks_total")]
    your_rd = you.get("referring_domains") or 0
    med_rd = median(peer_rds) if peer_rds else 0
    med_dr = median(peer_drs) if peer_drs else 0
    samples = you.get("sample_backlinks") or []
    spam_ratio = sum(1 for s in samples if SPAM_HOSTS.search(s)) / max(len(samples), 1)
    return {
        "you": {"dr": you.get("dr"), "rd": your_rd, "bl": you.get("backlinks_total") or 0, "samples": samples},
        "peers_median": {"dr": med_dr, "rd": med_rd, "bl": median(peer_bls) if peer_bls else 0},
        "peers": {
            d: {"dr": p.get("dr"), "rd": p.get("referring_domains"), "bl": p.get("backlinks_total")}
            for d, p in peers.items()
        },
        "rd_gap_to_median": round(med_rd - your_rd, 1),
        "rd_target": int(max(med_rd, 48)),
        "spam_sample_ratio": round(spam_ratio, 2),
    }


def form_hypothesis(cmp: dict, serp: dict, cycle: int) -> dict:
    in_top10 = serp.get("in_top10_count", 0) if isinstance(serp, dict) else 0
    spam = cmp["spam_sample_ratio"]
    rd_gap = cmp["rd_gap_to_median"]

    if in_top10 > 0:
        primary = "maintain_and_expand"
        confidence = 0.9
    elif spam >= 0.5:
        primary = "backlink_quality_disavow_spam"
        confidence = 0.85
    elif rd_gap > 30:
        primary = "backlink_volume_and_type"
        confidence = 0.78
    elif cycle >= 3:
        primary = "index_and_deploy_directory"
        confidence = 0.7
    else:
        primary = "backlink_quality_and_type"
        confidence = 0.72

    return {
        "primary": primary,
        "confidence": confidence,
        "cycle": cycle,
        "statement_ko": _hypothesis_text(primary, cmp, in_top10),
        "citation_gaps": CITATION_GAP_TYPES,
    }


def _hypothesis_text(primary: str, cmp: dict, in_top10: int) -> str:
    texts = {
        "maintain_and_expand": f"top10 {in_top10}/3 달성 구간 — citation 유지·확장.",
        "backlink_quality_disavow_spam": f"RD {cmp['you']['rd']} but spam {cmp['spam_sample_ratio']:.0%} — quality+deploy.",
        "backlink_volume_and_type": f"RD gap {cmp['rd_gap_to_median']:+.0f} — directory/guide_hub until {cmp['rd_target']}.",
        "index_and_deploy_directory": "SERP 0 — sync Tier S PC Browser 배포 + GSC index P0.",
        "backlink_quality_and_type": f"directory/guide_hub until RD {cmp['rd_target']}.",
    }
    return texts.get(primary, texts["backlink_quality_and_type"])


def inject_serp_seeds(serp: dict) -> int:
    """SERP 1페이지 URL → learning_seeds.json (collector가 읽음)."""
    data = load_json(SEEDS_FILE, {"seeds": [], "updated_at": None})
    existing = {(s["keyword"], s["url"]) for s in data.get("seeds", [])}
    added = 0
    for row in serp.get("results") or []:
        kw = row.get("keyword", "")
        for url in row.get("sample_urls") or []:
            if TARGET in url.lower():
                continue
            if (kw, url) not in existing:
                data.setdefault("seeds", []).append(
                    {"keyword": kw, "url": url, "source": "serp_top5", "added_at": now_iso()}
                )
                existing.add((kw, url))
                added += 1
    data["updated_at"] = now_iso()
    save_json(SEEDS_FILE, data)
    return added


def purge_spam_master() -> int:
    master = load_json(MASTER, {"placements": []})
    before = len(master.get("placements", []))
    kept = []
    for p in master.get("placements", []):
        url = p.get("deploy_url") or p.get("url") or ""
        if SPAM_HOSTS.search(url):
            continue
        kept.append(p)
    master["placements"] = kept
    master["updated_at"] = now_iso()
    save_json(MASTER, master)
    return before - len(kept)


def export_deploy_queue() -> int:
    """Tier S/A directory·guide_hub → PC Browser 배포 큐."""
    sync = load_json(SYNC, {})
    rows = sync.get("table_rows") or []
    priority = []
    for r in rows:
        pt = r.get("platform_type", "")
        tier = r.get("tier_hint", "B")
        if pt in ("directory", "guide_hub") and tier in ("S", "A"):
            priority.append(
                {
                    "target_keyword": r.get("target_keyword"),
                    "platform_type": pt,
                    "tier_hint": tier,
                    "deploy_url": r.get("deploy_url"),
                    "money_url": r.get("money_url"),
                    "anchor_text": r.get("anchor_text"),
                    "status": "queued",
                }
            )
    queue = {
        "updated_at": now_iso(),
        "money_site": sync.get("money_site", "https://gangara.co.kr/"),
        "count": len(priority),
        "note": "PC Cursor Browser — placement URL에 money_url·anchor 삽입",
        "rows": priority[:20],
    }
    save_json(DEPLOY_QUEUE, queue)
    return len(priority)


def apply_patches(hyp: dict, cycle: int) -> list[str]:
    changes: list[str] = []
    exp = load_json(EXPERIMENT, {})
    ll = exp.setdefault("learning_loop", {})
    ll.update(
        {
            "cycle": cycle,
            "last_hypothesis": hyp["primary"],
            "exclude_spam_domains": ["postheaven.net", "blogspot.com", "bcbloggers.com"],
            "stop_when": "all_keywords_top10",
        }
    )
    save_json(EXPERIMENT, exp)
    changes.append("gangara_experiment learning_loop")

    cfg = load_json(CONFIG, {})
    llc = cfg.setdefault("learning_loop", {})
    llc["prioritize_platforms"] = ["directory", "guide_hub"]
    llc["active_cycle"] = cycle
    if hyp["primary"] in ("backlink_quality_disavow_spam", "backlink_volume_and_type"):
        llc["min_trait_score"] = 55 + min(cycle * 2, 15)
    save_json(CONFIG, cfg)
    changes.append("machine_config min_trait escalation")

    removed = purge_spam_master()
    if removed:
        changes.append(f"placements_master purged {removed} spam")

    return changes


def run_collect() -> int:
    return subprocess.call([sys.executable, str(REPO / "core/run_backlink_collect.py")], cwd=str(REPO))


def run_single_cycle(cycle: int) -> dict:
    print(f"\n{'='*60}\nLearning Loop — cycle {cycle}\n{'='*60}")
    serp = measure_serp()
    in_top10 = serp.get("in_top10_count", 0)
    print(f"SERP in_top10: {in_top10}/3")

    seeds_added = inject_serp_seeds(serp)
    print(f"SERP seeds added: {seeds_added}")

    sst = measure_backlinks()
    you = sst.get(TARGET, {"referring_domains": 0})
    peers = {d: sst[d] for d in BENCHMARK_DOMAINS if d in sst}
    cmp = compare(you, peers)
    hyp = form_hypothesis(cmp, serp, cycle)
    patches = apply_patches(hyp, cycle)

    run_collect()
    queue_n = export_deploy_queue()

    exp = load_json(EXPERIMENT, {})
    exp.setdefault("learning_cycles", []).append(
        {
            "cycle": cycle,
            "at": now_iso(),
            "hypothesis_id": hyp["primary"],
            "serp_in_top10": in_top10,
            "rd_gap": cmp["rd_gap_to_median"],
            "seeds_added": seeds_added,
            "deploy_queue": queue_n,
            "patches": patches,
            "ranks": {r["keyword"]: r.get("rank") for r in serp.get("results", [])},
        }
    )
    exp["learning_loop"] = {
        "updated_at": now_iso(),
        "cycle": cycle,
        "hypothesis": hyp,
        "comparison": cmp,
        "goal_met": serp_goal_met(serp),
    }
    save_json(EXPERIMENT, exp)

    st = load_json(STATUS, {})
    st["learning_loop"] = {
        "cycle": cycle,
        "hypothesis": hyp["primary"],
        "serp_in_top10": in_top10,
        "goal_met": serp_goal_met(serp),
        "rd_target": cmp["rd_target"],
    }
    st["next_actions"] = [
        f"[cycle {cycle}] PC Browser: core/backlink_deploy_queue.json {queue_n}건 배포",
        f"[cycle {cycle}] GSC sitemap + site:gangara.co.kr",
        f"python3 core/run_learning_loop.py --until-top10 (SERP {in_top10}/3 top10)",
    ]
    st["updated_at"] = now_iso()
    save_json(STATUS, st)

    _run_report(email=os.environ.get("GANGARA_AUTO_EMAIL", "") == "1")
    return {
        "cycle": cycle,
        "serp": serp,
        "hypothesis": hyp,
        "comparison": cmp,
        "goal_met": serp_goal_met(serp),
        "deploy_queue": queue_n,
        "patches": patches,
    }


def run_until_top10(
    max_cycles: int,
    min_keywords: int,
    pause_sec: float,
    start_cycle: int = 1,
) -> dict:
    summary = {"cycles_run": 0, "goal_met": False, "final_serp": None, "start_cycle": start_cycle}
    for i in range(max_cycles):
        cycle = start_cycle + i
        result = run_single_cycle(cycle)
        summary["cycles_run"] = i + 1
        summary["final_cycle"] = cycle
        summary["final_serp"] = result["serp"]
        summary["goal_met"] = serp_goal_met(result["serp"], min_keywords)

        report = _render_multi_report(cycle, result, summary["goal_met"])
        (REPO / "tools/LEARNING_LOOP_REPORT.md").write_text(report, encoding="utf-8")

        if summary["goal_met"]:
            print(f"\n*** GOAL MET: {min_keywords}+ keywords in top10 after cycle {cycle} ***")
            exp = load_json(EXPERIMENT, {})
            exp["status"] = "goal_reached"
            exp["goal_reached_at"] = now_iso()
            save_json(EXPERIMENT, exp)
            break

        if i < max_cycles - 1:
            print(f"Goal not met — next cycle in {pause_sec}s...")
            time.sleep(pause_sec)

    if not summary["goal_met"]:
        exp = load_json(EXPERIMENT, {})
        exp.setdefault("learning_loop", {})["awaiting_pc_deploy"] = True
        exp["learning_loop"]["last_cycle"] = summary.get("final_cycle", start_cycle)
        save_json(EXPERIMENT, exp)

    _run_report(email=os.environ.get("GANGARA_AUTO_EMAIL", "") == "1")
    return summary


def run_continuous(
    batch_cycles: int = 5,
    max_batches: int = 200,
    batch_pause: float = 30.0,
    cycle_pause: float = 2.0,
    min_keywords: int = 1,
) -> dict:
    """유의미한 SERP(top10) 나올 때까지 배치 반복. min_keywords=1 이면 1키워드 top10도 성공."""
    print(f"=== CONTINUOUS until top10 (min_keywords={min_keywords}, max_batches={max_batches}) ===")
    exp = load_json(EXPERIMENT, {})
    start = int((exp.get("learning_loop") or {}).get("last_cycle", 0)) + 1
    overall = {"batches": 0, "goal_met": False, "total_cycles": 0}

    for batch in range(1, max_batches + 1):
        print(f"\n>>> Batch {batch}/{max_batches} (cycle from {start})")
        summary = run_until_top10(batch_cycles, min_keywords, cycle_pause, start_cycle=start)
        overall["batches"] = batch
        overall["goal_met"] = summary["goal_met"]
        overall["total_cycles"] = start + summary["cycles_run"] - 1
        overall["final_serp"] = summary.get("final_serp")

        _git_push_artifacts(batch)

        if summary["goal_met"]:
            print(f"\n*** CONTINUOUS STOP: goal met after batch {batch} ***")
            break

        start = overall["total_cycles"] + 1
        if batch < max_batches:
            print(f"Batch {batch} done — pause {batch_pause}s...")
            time.sleep(batch_pause)

    exp = load_json(EXPERIMENT, {})
    exp.setdefault("learning_loop", {})["continuous"] = {
        "updated_at": now_iso(),
        "batches_run": overall["batches"],
        "total_cycles": overall["total_cycles"],
        "goal_met": overall["goal_met"],
    }
    save_json(EXPERIMENT, exp)
    _run_report(email=True)
    return overall


def _git_push_artifacts(batch: int) -> None:
    paths = [
        "tools/LEARNING_DIGEST_LATEST.md",
        "tools/LEARNING_DIGEST_LATEST.json",
        "tools/LEARNING_LOOP_REPORT.md",
        "core/gangara_experiment.json",
        "core/backlink_deploy_status.json",
        "core/backlink_deploy_queue.json",
        "core/backlink_targets_sync.json",
        "website 확장 수집/misc/data/learning_seeds.json",
        "website 확장 수집/misc/data/placements_master.json",
    ]
    subprocess.call(["git", "add"] + paths, cwd=str(REPO))
    subprocess.call(
        ["git", "commit", "-m", f"chore(learning): continuous batch {batch}"],
        cwd=str(REPO),
    )
    subprocess.call(["git", "push", "-u", "origin", "cursor/gangara-faeb"], cwd=str(REPO))


def _render_multi_report(cycle: int, result: dict, goal_met: bool) -> str:
    h, c, serp = result["hypothesis"], result["comparison"], result["serp"]
    lines = [
        f"# 자가 발전 학습 루프 — cycle {cycle} ({now_iso()})",
        "",
        f"**SERP top10:** {serp.get('in_top10_count', 0)}/3 | **goal_met:** {goal_met}",
        "",
        f"## 가설 ({h['confidence']:.0%})",
        h["statement_ko"],
        "",
        "| 키워드 | rank | top10 |",
        "|--------|------|-------|",
    ]
    for r in serp.get("results", []):
        rank = r.get("rank") if r.get("rank") else "—"
        lines.append(f"| {r['keyword']} | {rank} | {'✅' if r.get('in_top10') else '❌'} |")
    lines += [
        "",
        f"RD: gangara {c['you']['rd']} / target {c['rd_target']}",
        f"Deploy queue: {result['deploy_queue']}건 → `core/backlink_deploy_queue.json`",
        "",
        "## 재실행",
        "```bash",
        "python3 core/run_learning_loop.py --until-top10 --max-cycles 20",
        "```",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="gangara SERP 1페이지 자가 학습 루프")
    ap.add_argument("--until-top10", action="store_true", help="top10 달성까지 배치 내 반복")
    ap.add_argument("--continuous", action="store_true", help="유의미한 SERP 나올 때까지 배치 무한 반복")
    ap.add_argument("--max-cycles", type=int, default=5, help="배치당 최대 사이클")
    ap.add_argument("--max-batches", type=int, default=200, help="continuous 최대 배치")
    ap.add_argument("--min-keywords", type=int, default=1, help="성공 top10 키워드 수 (1=유의미 결과)")
    ap.add_argument("--pause", type=float, default=2.0, help="사이클 간 대기(초)")
    ap.add_argument("--batch-pause", type=float, default=30.0, help="배치 간 대기(초)")
    args = ap.parse_args()

    if args.continuous:
        overall = run_continuous(
            batch_cycles=args.max_cycles,
            max_batches=args.max_batches,
            batch_pause=args.batch_pause,
            cycle_pause=args.pause,
            min_keywords=args.min_keywords,
        )
        print(json.dumps(overall, ensure_ascii=False, indent=2, default=str))
        return 0 if overall["goal_met"] else 2

    if args.until_top10:
        exp = load_json(EXPERIMENT, {})
        start = int((exp.get("learning_loop") or {}).get("last_cycle", 0)) + 1
        summary = run_until_top10(args.max_cycles, args.min_keywords, args.pause, start_cycle=start)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0 if summary["goal_met"] else 2

    exp = load_json(EXPERIMENT, {})
    start = int((exp.get("learning_loop") or {}).get("last_cycle", 0)) + 1
    result = run_single_cycle(start)
    print(json.dumps(result["hypothesis"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
