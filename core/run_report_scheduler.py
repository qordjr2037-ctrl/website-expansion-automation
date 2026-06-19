#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3시간마다 학습 digest Gmail 자동 발송 (기본 보고 스케줄러).

  python3 core/run_report_scheduler.py --once          # 1회 (due면 발송)
  python3 core/run_report_scheduler.py --daemon      # 3h 루프 (tmux용)
  python3 core/run_report_scheduler.py --daemon --force-now  # 즉시 1회 후 3h 루프
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "core/machine_config.json"
REPORT_SCRIPT = REPO / "core/run_learning_report.py"
LOG = REPO / "tools/report_scheduler.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_interval_hours() -> int:
    if not CONFIG.is_file():
        return 3
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return int((cfg.get("learning_loop") or {}).get("report_interval_hours", 3))


def run_scheduled_report(force: bool = False) -> int:
    cmd = [sys.executable, str(REPORT_SCRIPT), "--quiet", "--email", "--scheduled"]
    if force:
        cmd.append("--force")
    return subprocess.call(cmd, cwd=str(REPO))


def daemon_loop(interval_hours: int, force_now: bool) -> int:
    interval_sec = max(1, interval_hours) * 3600
    log(f"daemon start interval={interval_hours}h")
    if force_now:
        log("force-now: immediate report")
        run_scheduled_report(force=True)
    while True:
        log("sleep until next scheduled report")
        time.sleep(interval_sec)
        log("scheduled tick")
        rc = run_scheduled_report(force=False)
        log(f"report exit={rc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="gangara 3h Gmail report scheduler")
    ap.add_argument("--once", action="store_true", help="1회 실행 (due일 때만 발송)")
    ap.add_argument("--daemon", action="store_true", help="3시간 간격 무한 루프")
    ap.add_argument("--force-now", action="store_true", help="daemon 시작 시 즉시 1회 발송")
    ap.add_argument("--force", action="store_true", help="--once 시 due 무시하고 발송")
    args = ap.parse_args()

    hours = load_interval_hours()

    if args.daemon:
        try:
            daemon_loop(hours, force_now=args.force_now)
        except KeyboardInterrupt:
            log("daemon stopped")
        return 0

    if args.once or not (args.daemon):
        rc = run_scheduled_report(force=args.force)
        return 0 if rc == 0 else rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
