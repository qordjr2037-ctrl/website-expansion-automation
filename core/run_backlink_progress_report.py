#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백링크 live 숫자 10분 보고 — verified live 건수·증분·큐·SERP.

  python3 core/run_backlink_progress_report.py
  python3 core/run_backlink_progress_report.py --email
  python3 core/run_backlink_progress_report.py --daemon
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "core"))

from backlink_verified_store import load_store, stats_by_platform, success_count  # noqa: E402

CONFIG = REPO / "core/machine_config.json"
STATUS = REPO / "core/backlink_deploy_status.json"
QUEUE_M1 = REPO / "core/backlink_deploy_queue_machine1.json"
QUEUE = REPO / "core/backlink_deploy_queue.json"
SERP = REPO / "tools/serp_rank_probe_output.json"
STATE = REPO / "tools/backlink_progress_state.json"
LATEST_MD = REPO / "tools/BACKLINK_PROGRESS_LATEST.md"
LATEST_JSON = REPO / "tools/BACKLINK_PROGRESS_LATEST.json"
LOG = REPO / "tools/backlink_progress.log"
STOP = REPO / "tools/BACKLINK_PROGRESS_STOP"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_state() -> dict:
    return load_json(STATE, {"last_success_total": 0, "reports": 0})


def save_state(st: dict) -> None:
    st["updated_at"] = now_iso()
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def queue_stats() -> dict:
    qpath = QUEUE_M1 if QUEUE_M1.exists() else QUEUE
    data = load_json(qpath, {"rows": []})
    rows = data.get("rows") or []
    status = Counter(r.get("status", "?") for r in rows)
    return {
        "path": qpath.name,
        "total": len(rows),
        "queued": status.get("queued", 0),
        "done": status.get("done", 0),
        "failed": status.get("failed", 0),
        "new_signup": status.get("new_signup", 0),
        "skipped": status.get("skipped", 0),
    }


def serp_top10() -> tuple[int, int]:
    serp = load_json(SERP, {})
    if serp.get("in_top10_count") is not None:
        return int(serp["in_top10_count"]), 3
    results = serp.get("results") or []
    n = sum(1 for r in results if r.get("in_top10"))
    return n, max(3, len(results) or 3)


def daily_target() -> int:
    cfg = load_json(CONFIG, {})
    vol = cfg.get("backlink_volume") or {}
    return int(vol.get("daily_target") or cfg.get("daily_link_target") or 1000)


def build_report() -> dict:
    store = load_store()
    st = load_state()
    live = success_count(store)
    prev = int(st.get("last_success_total") or 0)
    delta = live - prev
    q = queue_stats()
    serp_n, serp_total = serp_top10()
    target = daily_target()
    by_pt = stats_by_platform(store)
    st_data = load_json(STATUS, {})
    ll = st_data.get("learning_loop") or {}

    report = {
        "at": now_iso(),
        "verified_live": live,
        "delta_10m": delta,
        "daily_target": target,
        "daily_pct": round(100 * live / target, 2) if target else 0,
        "failed_total": len(store.get("failures") or []),
        "platform_success": by_pt,
        "queue": q,
        "serp_in_top10": serp_n,
        "serp_keywords": serp_total,
        "milestone_next": ((live // 100) + 1) * 100,
        "hypothesis": ll.get("hypothesis"),
        "reports_total": int(st.get("reports") or 0) + 1,
    }
    return report


def render_markdown(r: dict) -> str:
    q = r["queue"]
    pt_lines = ", ".join(f"{k}={v}" for k, v in sorted((r.get("platform_success") or {}).items()))
    sign = "+" if r["delta_10m"] >= 0 else ""
    return f"""# gangara 백링크 10분 숫자 보고

생성: {r["at"]}

## 핵심 숫자
| 항목 | 값 |
|------|-----|
| **verified live (올라간 백링크)** | **{r["verified_live"]}건** |
| **지난 10분 증가** | **{sign}{r["delta_10m"]}건** |
| 일일 목표 | {r["daily_target"]}/일 ({r["daily_pct"]}%) |
| 다음 milestone | {r["milestone_next"]}건 |
| 실패 누적 | {r["failed_total"]}건 |
| SERP top10 | {r["serp_in_top10"]}/{r["serp_keywords"]} |

## 큐 ({q["path"]})
- 전체 {q["total"]} · queued {q["queued"]} · done {q["done"]} · failed {q["failed"]} · new_signup {q["new_signup"]}

## platform별 live 성공
{pt_lines or "(없음)"}

## 다음 실행
```bash
python3 tools/deploy_backlink_playwright.py --limit 10 --tier S --platform directory
python3 core/run_backlink_auto.py --batch 50
```

계정: `core/notify_secrets.json` → ROOMPANG_USER/PASS, CLICKN_USER/PASS
"""


def run_once(email: bool, quiet: bool) -> dict:
    report = build_report()
    md = render_markdown(report)
    LATEST_MD.write_text(md, encoding="utf-8")
    LATEST_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    st = load_state()
    st["last_success_total"] = report["verified_live"]
    st["reports"] = report["reports_total"]
    st["last_report_at"] = report["at"]
    save_state(st)

    if not quiet:
        print(md)

    if email:
        from run_learning_report import send_email  # noqa: WPS433

        sign = "+" if report["delta_10m"] >= 0 else ""
        subj = (
            f"[gangara 백링크] live {report['verified_live']}건 "
            f"({sign}{report['delta_10m']}/10분) · 목표 {report['daily_target']}/일"
        )
        ok = send_email(subj, md, report)
        log(f"EMAIL {'sent' if ok else 'skip'} live={report['verified_live']} delta={report['delta_10m']}")
    else:
        log(f"report live={report['verified_live']} delta={report['delta_10m']}")

    return report


def interval_sec() -> int:
    cfg = load_json(CONFIG, {})
    prog = cfg.get("backlink_progress") or {}
    return int(prog.get("report_interval_minutes", 10)) * 60


def main() -> int:
    ap = argparse.ArgumentParser(description="백링크 live 숫자 10분 보고")
    ap.add_argument("--email", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    args = ap.parse_args()

    if STOP.exists() and not args.daemon:
        log("STOPPED — tools/BACKLINK_PROGRESS_STOP")
        return 0

    if args.daemon:
        log(f"progress daemon interval={interval_sec()}s")
        while not STOP.exists():
            run_once(email=True, quiet=True)
            time.sleep(interval_sec())
        return 0

    run_once(email=args.email, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
