#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gangara.co.kr 백링크 집중 실험 — 1 Run 오케스트레이터.

1) SERP 베이스라인 프로브
2) placement 수집·sync (money_url= gangara.co.kr)
3) 실험 상태 갱신
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPERIMENT = REPO / "core/gangara_experiment.json"
PROBE = REPO / "tools/serp_rank_probe.py"
COLLECT = REPO / "core/run_backlink_collect.py"


def run_cmd(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(REPO))


def main() -> None:
    steps = []

    # 1) baseline / weekly probe
    rc = run_cmd([sys.executable, str(PROBE), "--merge-experiment"])
    steps.append({"step": "serp_probe", "exit_code": rc})

    # 2) collect + export sync
    rc2 = run_cmd([sys.executable, str(COLLECT)])
    steps.append({"step": "backlink_collect", "exit_code": rc2})

    # 3) update experiment log
    exp = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    exp["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    exp.setdefault("run_log", []).append(
        {
            "at": exp["updated_at"],
            "steps": steps,
        }
    )
    sync = json.loads((REPO / "core/backlink_targets_sync.json").read_text(encoding="utf-8"))
    exp["last_sync"] = {
        "count": sync.get("count"),
        "pool_total": sync.get("pool_total"),
        "money_site": sync.get("money_site"),
        "tier_distribution": sync.get("tier_distribution"),
    }
    EXPERIMENT.write_text(json.dumps(exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n=== gangara experiment run complete ===")
    print(json.dumps(exp.get("last_probe", {}), ensure_ascii=False, indent=2))
    print(json.dumps(exp.get("last_sync", {}), ensure_ascii=False, indent=2))
    sys.exit(max(rc, rc2))


if __name__ == "__main__":
    main()
