#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가설 → 측정 → 비교 → 수정 → 재실험 (Track B 자동 학습 루프)

목표: gangara.co.kr 3키워드 SERP 1페이지 진입
현재 병목 가설: 백링크 유형·품질 (directory/guide_hub) + 인덱스

1 Run = 1 사이클. 측정 → gap 분석 → config/qualifier 자동 패치 → 실험 로그.
"""
from __future__ import annotations

import json
import subprocess
import sys
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

BENCHMARK_DOMAINS = [
    "choicelounge.co.kr",
    "gangnamdalto.co.kr",
    "classicsalong.com",
    "thesevensalon.com",
    "applegangnam.com",
    "gangnammirror.com",
]

TARGET = "gangara.co.kr"
CITATION_GAP_TYPES = ["directory_listing", "guide_hub", "sibling_domain"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def measure_serp() -> dict:
    subprocess.call(
        [sys.executable, str(REPO / "tools/serp_rank_probe.py"), "--merge-experiment"],
        cwd=str(REPO),
    )
    return load_json(SERP_PROBE, {})


def measure_backlinks() -> dict[str, dict]:
    audit = load_json(AUDIT, {})
    if not audit.get("live_sst_summary"):
        subprocess.call([sys.executable, str(REPO / "tools/backlink_audit.py"), "--all"], cwd=str(REPO))
        audit = load_json(AUDIT, {})
    return sst_map(audit)


def compare(you: dict, peers: dict[str, dict]) -> dict:
    peer_rds = [p["referring_domains"] for p in peers.values() if p.get("referring_domains")]
    peer_drs = [p["dr"] for p in peers.values() if p.get("dr") is not None]
    peer_bls = [p["backlinks_total"] for p in peers.values() if p.get("backlinks_total")]

    your_rd = you.get("referring_domains") or 0
    your_dr = you.get("dr")
    your_bl = you.get("backlinks_total") or 0
    med_rd = median(peer_rds) if peer_rds else 0
    med_dr = median(peer_drs) if peer_drs else 0

    samples = you.get("sample_backlinks") or []
    spam_ratio = sum(1 for s in samples if "postheaven" in s or "blogspot" in s) / max(len(samples), 1)

    return {
        "you": {"dr": your_dr, "rd": your_rd, "bl": your_bl, "samples": samples},
        "peers_median": {"dr": med_dr, "rd": med_rd, "bl": median(peer_bls) if peer_bls else 0},
        "peers": {
            d: {"dr": p.get("dr"), "rd": p.get("referring_domains"), "bl": p.get("backlinks_total")}
            for d, p in peers.items()
        },
        "rd_gap_to_median": round(med_rd - your_rd, 1),
        "dr_gap_to_median": round(med_dr - (your_dr or 0), 1),
        "rd_target": int(max(med_rd, 48)),
        "spam_sample_ratio": round(spam_ratio, 2),
    }


def form_hypothesis(cmp: dict, serp: dict) -> dict:
    in_top10 = serp.get("in_top10_count", 0) if isinstance(serp, dict) else 0
    rd_gap = cmp["rd_gap_to_median"]
    spam = cmp["spam_sample_ratio"]

    if spam >= 0.5:
        primary = "backlink_quality_disavow_spam"
        confidence = 0.85
    elif rd_gap > 30:
        primary = "backlink_volume_and_type"
        confidence = 0.78
    elif in_top10 == 0 and cmp["you"]["rd"] >= cmp["peers_median"]["rd"] * 0.8:
        primary = "index_and_citation_type"
        confidence = 0.65
    else:
        primary = "backlink_quality_and_type"
        confidence = 0.72

    return {
        "primary": primary,
        "confidence": confidence,
        "statement_ko": _hypothesis_text(primary, cmp, in_top10),
        "falsifiable_if": [
            "directory 10건 live 배포 후 14일 내 site:gangara.co.kr 여전히 0",
            "quality RD 80+ 후에도 3키워드 top30 미노출",
        ],
        "citation_gaps": CITATION_GAP_TYPES,
    }


def _hypothesis_text(primary: str, cmp: dict, in_top10: int) -> str:
    if primary == "backlink_volume_and_type":
        return (
            f"RD {cmp['you']['rd']} vs 경쟁 중위 {cmp['peers_median']['rd']:.0f} — "
            f"directory·guide_hub 부족. RD 목표 {cmp['rd_target']}."
        )
    if primary == "backlink_quality_disavow_spam":
        return (
            f"RD {cmp['you']['rd']}이나 샘플 {cmp['spam_sample_ratio']:.0%}가 postheaven/web2 스팸 — "
            "숫자보다 유형·품질이 병목."
        )
    if primary == "index_and_citation_type":
        return f"SERP {in_top10}/3 — 인덱스·directory live citation 미등록이 병목."
    return (
        "온페이지 fusion 후 top30 0 — 백링크 유형(directory/guide_hub) 확보가 1순위, "
        f"RD 목표 {cmp['rd_target']} (classicsalong~choicelounge 밴드)."
    )


def plan_experiments(cmp: dict) -> list[dict]:
    return [
        {
            "id": "exp-directory-p0",
            "action": "sync Tier S directory → PC Browser 배포 (roompang 우선)",
            "metric": "verified_live_citations >= 3",
            "priority": "P0",
        },
        {
            "id": "exp-guide-hub-p1",
            "action": "guide_hub A tier dofollow 5건 배포",
            "metric": "guide_hub live link to gangara.co.kr",
            "priority": "P1",
        },
        {
            "id": "exp-spam-filter",
            "action": "postheaven/web2 스팸 placement export 제외",
            "metric": "sync spam domain 0건",
            "priority": "P0",
        },
        {
            "id": "exp-rd-target",
            "action": f"quality RD {cmp['rd_target']}+ (directory+guide_hub만)",
            "metric": f"SST RD >= {cmp['rd_target']}",
            "priority": "P1",
        },
        {
            "id": "exp-index",
            "action": "GSC sitemap + site:gangara.co.kr 인덱스",
            "metric": "indexed_pages >= 5",
            "priority": "P0",
        },
    ]


def apply_patches() -> list[str]:
    changes: list[str] = []

    exp = load_json(EXPERIMENT, {})
    exp.setdefault("learning_loop", {})["exclude_spam_domains"] = [
        "postheaven.net",
        "blogspot.com",
        "bcbloggers.com",
    ]
    exp["updated_at"] = now_iso()
    save_json(EXPERIMENT, exp)
    changes.append("gangara_experiment.json learning_loop")

    cfg = load_json(CONFIG, {})
    cfg.setdefault("learning_loop", {})["prioritize_platforms"] = ["directory", "guide_hub"]
    save_json(CONFIG, cfg)
    changes.append("machine_config.json prioritize_platforms")

    qual_path = REPO / "website 확장 수집/misc/_program/placement_qualifier.py"
    text = qual_path.read_text(encoding="utf-8")
    if "postheaven" not in text:
        text = text.replace(
            'SPAM_DOMAINS = re.compile(r"(news\\.|naver\\.com/news|daum\\.net/v/)", re.I)',
            'SPAM_DOMAINS = re.compile(\n'
            '    r"(news\\.|naver\\.com/news|daum\\.net/v/|postheaven\\.net|bcbloggers\\.com)",\n'
            "    re.I,\n"
            ")",
        )
        text = text.replace(
            "    if SPAM_DOMAINS.search(url):",
            "    if SPAM_DOMAINS.search(url) or re.search(r\"postheaven\\.net|blogspot\\.com\", url, re.I):",
        )
        qual_path.write_text(text, encoding="utf-8")
        changes.append("placement_qualifier.py spam reject")

    return changes


def run_cycle() -> dict:
    print("=== Learning Loop Cycle ===")
    serp = measure_serp()
    sst = measure_backlinks()

    you = sst.get(TARGET, {"domain": TARGET, "referring_domains": 0})
    peers = {d: sst[d] for d in BENCHMARK_DOMAINS if d in sst}
    cmp = compare(you, peers)
    hyp = form_hypothesis(cmp, serp if isinstance(serp, dict) else {})
    experiments = plan_experiments(cmp)
    patches = apply_patches()

    exp = load_json(EXPERIMENT, {})
    exp["learning_loop"] = {
        "updated_at": now_iso(),
        "hypothesis": hyp,
        "comparison": cmp,
        "experiments": experiments,
        "patches_applied": patches,
    }
    exp.setdefault("learning_cycles", []).append(
        {
            "at": now_iso(),
            "hypothesis_id": hyp["primary"],
            "confidence": hyp["confidence"],
            "rd_gap": cmp["rd_gap_to_median"],
            "serp_in_top10": serp.get("in_top10_count") if isinstance(serp, dict) else None,
        }
    )
    save_json(EXPERIMENT, exp)

    st = load_json(STATUS, {})
    st["learning_loop"] = {"hypothesis": hyp["primary"], "confidence": hyp["confidence"], "rd_target": cmp["rd_target"]}
    st["next_actions"] = [
        f"[학습] {experiments[0]['action']}",
        f"[학습] {experiments[2]['action']}",
        f"RD 목표 {cmp['rd_target']} (현재 {cmp['you']['rd']}, 중위 {cmp['peers_median']['rd']:.0f})",
        "python3 core/run_learning_loop.py 주 1회",
    ]
    st["updated_at"] = now_iso()
    save_json(STATUS, st)

    subprocess.call([sys.executable, str(REPO / "core/run_backlink_collect.py")], cwd=str(REPO))

    cycle = {"at": now_iso(), "hypothesis": hyp, "comparison": cmp, "experiments": experiments, "patches_applied": patches}
    (REPO / "tools/LEARNING_LOOP_REPORT.md").write_text(_render_report(cycle), encoding="utf-8")
    return cycle


def _render_report(cycle: dict) -> str:
    h, c = cycle["hypothesis"], cycle["comparison"]
    lines = [
        f"# 자동 학습 루프 — {cycle['at']}",
        "",
        f"## 가설 ({h['confidence']:.0%})",
        h["statement_ko"],
        "",
        "| 도메인 | DR | RD | BL |",
        "|--------|----|----|-----|",
        f"| **gangara.co.kr** | {c['you']['dr']} | {c['you']['rd']} | {c['you']['bl']} |",
    ]
    for d, p in sorted(c["peers"].items(), key=lambda x: -(x[1].get("rd") or 0)):
        lines.append(f"| {d} | {p.get('dr')} | {p.get('rd')} | {p.get('bl')} |")
    lines.append(f"\nRD 목표: **{c['rd_target']}** (격차 {c['rd_gap_to_median']:+.0f})\n")
    for e in cycle["experiments"]:
        lines.append(f"- [{e['priority']}] {e['action']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    cycle = run_cycle()
    print(json.dumps(cycle["hypothesis"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
