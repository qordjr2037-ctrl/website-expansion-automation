#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백링크 완전자동화 오케스트레이터 — 수집·플랜·auto·학습루프.

  python3 core/run_backlink_automation.py --once
  python3 core/run_backlink_automation.py --daemon
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "tools/backlink_automation.log"
CONFIG = REPO / "core/machine_config.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], name: str) -> int:
    log(f"START {name}: {' '.join(cmd)}")
    rc = subprocess.call(cmd, cwd=str(REPO))
    log(f"END {name} exit={rc}")
    return rc


def cycle_once() -> int:
    py = sys.executable
    steps = [
        ([py, "core/run_backlink_collect.py"], "collect"),
        ([py, "core/run_backlink_daily_plan.py", "--target", "1000", "--quiet"], "daily_plan"),
        ([py, "core/run_backlink_prepare.py", "--machine-id", "1"], "prepare_m1"),
        ([py, "core/run_backlink_auto.py", "--batch", "50", "--pause", "0.3"], "auto_batch"),
    ]
    secrets_path = REPO / "core/notify_secrets.json"
    if secrets_path.exists() or os.environ.get("CLICKN_USER") or os.environ.get("ROOMPANG_USER"):
        steps.append(
            ([py, "tools/deploy_backlink_playwright.py", "--limit", "10", "--tier", "S", "--platform", "directory"], "playwright_deploy"),
        )
    steps.extend([
        ([py, "core/run_learning_loop.py", "--max-cycles", "1"], "learning_1cycle"),
        ([py, "core/run_learning_report.py", "--quiet"], "digest"),
    ])
    for cmd, name in steps:
        run(cmd, name)
    # learning_loop가 experiment.json 덮어쓴 뒤 실패→다음 가설 재기록
    try:
        sys.path.insert(0, str(REPO / "core"))
        from backlink_verified_store import load_store  # noqa: E402
        from run_backlink_auto import apply_failure_patches  # noqa: E402

        apply_failure_patches(load_store())
        log("reapplied failure→next_hypothesis patches")
    except Exception as e:
        log(f"patch reapply skip: {e}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    args = ap.parse_args()

    if args.daemon:
        log("automation daemon start")
        while True:
            cycle_once()
            log(f"sleep {args.interval}s")
            time.sleep(args.interval)
    cycle_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
