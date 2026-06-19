#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gangara 실험 통합 supervisor — tmux 1개로 전부 유지 (죽지 않음).

  python3 core/run_gangara_supervisor.py
  python3 core/run_gangara_supervisor.py --daemon

중지: touch tools/GANGARA_SUPERVISOR_STOP
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STOP = REPO / "tools/GANGARA_SUPERVISOR_STOP"
LOG = REPO / "tools/gangara_supervisor.log"
STATE = REPO / "tools/gangara_supervisor_state.json"
PY = sys.executable


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def stopped() -> bool:
    return STOP.exists()


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(st: dict) -> None:
    st["updated_at"] = now_iso()
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(args: list[str], name: str, timeout: int | None = None) -> int:
    log(f"START {name}")
    try:
        rc = subprocess.call(args, cwd=str(REPO), timeout=timeout)
        log(f"END {name} exit={rc}")
        return rc
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT {name} after {timeout}s")
        return 124
    except Exception as e:
        log(f"ERROR {name}: {e}")
        return 1


def due(st: dict, key: str, interval_sec: int) -> bool:
    last = st.get(key)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last_dt).total_seconds() >= interval_sec
    except Exception:
        return True


def tick(st: dict) -> None:
    # 10분 — 배포+검증 (auto + Playwright roompang/ClickN)
    if due(st, "last_deploy", 600):
        run_cmd([PY, "core/run_backlink_auto.py", "--batch", "50", "--pause", "0.2"], "auto_batch", timeout=600)
        run_cmd(
            [PY, "tools/deploy_backlink_playwright.py", "--limit", "8", "--tier", "S", "--platform", "directory"],
            "deploy_directory",
            timeout=600,
        )
        run_cmd(
            [PY, "tools/deploy_backlink_playwright.py", "--limit", "15", "--platform", "profile"],
            "deploy_profile",
            timeout=600,
        )
        st["last_deploy"] = now_iso()

    # 10분 — 백링크 live 숫자 Gmail 보고 (배포 직후)
    if due(st, "last_progress", 600):
        run_cmd([PY, "core/run_backlink_progress_report.py", "--email", "--quiet"], "progress_10m", timeout=120)
        st["last_progress"] = now_iso()

    # 10분 — 인텔 Gmail (원론+경쟁자)
    if due(st, "last_intel", 600):
        run_cmd([PY, "core/run_backlink_intel_report.py", "--email", "--quiet"], "intel_10m", timeout=300)
        st["last_intel"] = now_iso()

    # 15분 — 수집+플랜 (가벼운 automation cycle)
    if due(st, "last_collect", 900):
        run_cmd([PY, "core/run_backlink_collect.py"], "collect", timeout=300)
        run_cmd([PY, "core/run_backlink_daily_plan.py", "--target", "1000", "--quiet"], "daily_plan", timeout=120)
        run_cmd([PY, "core/run_backlink_prepare.py", "--machine-id", "1"], "prepare", timeout=60)
        st["last_collect"] = now_iso()

    # 20분 — 학습 1 cycle
    if due(st, "last_learning", 1200):
        run_cmd([PY, "core/run_learning_loop.py", "--max-cycles", "1"], "learning_1cycle", timeout=600)
        run_cmd([PY, "core/run_learning_report.py", "--quiet"], "digest", timeout=120)
        st["last_learning"] = now_iso()

    # 3시간 — 학습 Gmail
    if due(st, "last_report_3h", 10800):
        run_cmd(
            [PY, "core/run_backlink_intel_report.py", "--email", "--force", "--quiet"],
            "intel_force",
            timeout=300,
        )
        run_cmd(
            [PY, "core/run_learning_report.py", "--email", "--scheduled", "--force", "--quiet"],
            "report_3h",
            timeout=120,
        )
        st["last_report_3h"] = now_iso()

    st["ticks"] = int(st.get("ticks") or 0) + 1
    save_state(st)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true", help="무한 루프 (기본)")
    ap.add_argument("--once", action="store_true", help="1 tick만")
    args = ap.parse_args()

    if STOP.exists():
        STOP.unlink()
        log("removed stale STOP file — resuming")

    st = load_state()
    log("supervisor start")

    if args.once:
        tick(st)
        return 0

    while not stopped():
        try:
            tick(st)
        except Exception:
            log(f"tick crash: {traceback.format_exc()[:500]}")
        log("sleep 60s")
        time.sleep(60)

    log("supervisor stopped by GANGARA_SUPERVISOR_STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
