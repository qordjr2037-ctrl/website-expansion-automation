#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백링크 인텔 10분 보고 — 원론 vs 경쟁자 추적.

  python3 core/run_backlink_intel_report.py
  python3 core/run_backlink_intel_report.py --email
  python3 core/run_backlink_intel_report.py --daemon   # 10분 루프 (그만 하라고 할 때까지)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "core"))

from backlink_intel_engine import render_intel_markdown, run_intel_cycle  # noqa: E402

CONFIG = REPO / "core/machine_config.json"
LATEST_MD = REPO / "tools/BACKLINK_INTEL_LATEST.md"
LATEST_JSON = REPO / "tools/BACKLINK_INTEL_LATEST.json"
STOP_FILE = REPO / "tools/BACKLINK_INTEL_STOP"
LOG = REPO / "tools/backlink_intel.log"


def log(msg: str) -> None:
    from datetime import datetime, timezone

    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_stopped() -> bool:
    if STOP_FILE.exists():
        return True
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        intel = cfg.get("backlink_intel") or {}
        return not intel.get("enabled", True)
    except Exception:
        return False


def interval_sec() -> int:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        return int((cfg.get("backlink_intel") or {}).get("report_interval_minutes", 10)) * 60
    except Exception:
        return 600


def run_once(email: bool, quiet: bool) -> dict:
    report = run_intel_cycle()
    md = render_intel_markdown(report)
    LATEST_MD.write_text(md, encoding="utf-8")
    LATEST_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not quiet:
        print(md)
    if email:
        from run_learning_report import send_email  # noqa: WPS433

        cycle = report.get("cycle", "?")
        subj = f"[gangara 인텔] cycle {cycle} · 원론+경쟁자 추적 (10분)"
        send_email(subj, md, report)
        log(f"EMAIL sent cycle={cycle}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="백링크 인텔 10분 보고")
    ap.add_argument("--email", action="store_true", help="Gmail 발송")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--daemon", action="store_true", help="10분마다 until STOP")
    ap.add_argument("--force", action="store_true", help="STOP 파일 있어도 1회 실행")
    args = ap.parse_args()

    if is_stopped() and not args.force:
        log("STOPPED — tools/BACKLINK_INTEL_STOP or backlink_intel.enabled=false")
        return 0

    if args.daemon:
        log(f"intel daemon start interval={interval_sec()}s")
        while not is_stopped():
            run_once(email=True, quiet=True)
            log(f"sleep {interval_sec()}s")
            time.sleep(interval_sec())
        log("intel daemon stopped by user")
        return 0

    run_once(email=args.email, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
