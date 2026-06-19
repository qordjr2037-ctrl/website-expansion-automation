#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
일일 플랜 → PC 머신별 deploy 큐 분할.

  MACHINE_ID=1 python3 core/run_backlink_prepare.py
  python3 core/run_backlink_prepare.py --machine-id 2 --machines 4
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NON_EDITABLE = re.compile(
    r"search\?q=|choicelounge\.co\.kr|seoulafterdark\.com|postheaven|blogspot",
    re.I,
)
PLAN = REPO / "core/backlink_daily_plan.json"
CONFIG = REPO / "core/machine_config.json"
QUEUE_DIR = REPO / "core"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_editable(row: dict) -> bool:
    """Browser 배포 가능 URL만 — search?q=·타인 guide_hub 등 제외."""
    url = row.get("deploy_url") or ""
    if NON_EDITABLE.search(url):
        return False
    action = (row.get("action") or "").strip()
    if action.startswith("SKIP"):
        return False
    return True


def shard_rows(rows: list[dict], machine_id: int, machines: int) -> list[dict]:
    """machine_id 1..N — rows를 균등 분할."""
    if machines < 1:
        machines = 1
    mid = max(1, min(machine_id, machines))
    return [r for i, r in enumerate(rows) if i % machines == (mid - 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine-id", type=int, default=int(os.environ.get("MACHINE_ID", "1")))
    ap.add_argument("--machines", type=int, default=0, help="0=config machines_in_fleet")
    ap.add_argument("--browser-id", type=int, default=0, help="1..8 추가 분할 (0=머신 전체)")
    ap.add_argument("--browsers", type=int, default=0)
    args = ap.parse_args()

    cfg = load_json(CONFIG, {})
    machines = args.machines or int(cfg.get("machines_in_fleet", 1))
    browsers = args.browsers or int(cfg.get("browsers_per_machine", 8))

    plan = load_json(PLAN, {})
    if not plan.get("rows"):
        print("ERROR: core/backlink_daily_plan.json 없음 — 먼저 run_backlink_daily_plan.py 실행")
        return 1

    all_rows = plan["rows"]
    editable = [r for r in all_rows if is_editable(r)]
    excluded = len(all_rows) - len(editable)
    machine_rows = shard_rows(editable, args.machine_id, machines)

    if args.browser_id > 0:
        machine_rows = shard_rows(machine_rows, args.browser_id, browsers)

    queue = {
        "updated_at": now_iso(),
        "money_site": plan.get("money_site", "https://gangara.co.kr/"),
        "machine_id": args.machine_id,
        "machines_total": machines,
        "browser_id": args.browser_id or None,
        "count": len(machine_rows),
        "excluded_not_editable": excluded,
        "daily_target": plan.get("daily_target", 1000),
        "note": f"PC machine {args.machine_id}/{machines} — editable only (excluded {excluded})",
        "rows": machine_rows,
    }

    suffix = f"_machine{args.machine_id}"
    if args.browser_id:
        suffix += f"_browser{args.browser_id}"
    out = QUEUE_DIR / f"backlink_deploy_queue{suffix}.json"
    out.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 기본 큐도 machine1이면 갱신 (기존 Browser prompt 호환)
    if args.machine_id == 1 and not args.browser_id:
        default_q = REPO / "core/backlink_deploy_queue.json"
        default_q.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK {out.name} — {len(machine_rows)} rows (machine {args.machine_id}/{machines})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
