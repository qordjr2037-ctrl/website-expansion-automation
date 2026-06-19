#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백링크 자동 배포·검증 1배치.

  python3 core/run_backlink_auto.py --batch 50
  python3 core/run_backlink_auto.py --daemon --batch 30
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "core"))

from backlink_verified_store import (  # noqa: E402
    load_store,
    mark_milestone_reported,
    pending_milestone,
    record_failure,
    record_success,
    save_store,
    stats_by_platform,
    success_count,
    url_already_success,
)
from failure_hypotheses import classify_failure, get_next_hypothesis, render_failure_report  # noqa: E402

CONFIG = REPO / "core/machine_config.json"
QUEUE_PATHS = [
    REPO / "core/backlink_deploy_queue_machine1.json",
    REPO / "core/backlink_deploy_queue.json",
]
TARGET = re.compile(r"gangara\.co\.kr", re.I)
SKIP_URL = re.compile(
    r"search\?q=|choicelounge\.co\.kr|seoulafterdark\.com|postheaven|blogspot",
    re.I,
)
CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; TrackB-Auto/1.0)"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_queue() -> tuple[Path, dict]:
    for p in QUEUE_PATHS:
        if p.exists():
            return p, load_json(p, {})
    return QUEUE_PATHS[-1], {"rows": []}


def save_queue(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_html(url: str, timeout: int = 15) -> tuple[str | None, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            return resp.read(80000).decode("utf-8", errors="replace"), "ok"
    except Exception as e:
        return None, str(e)[:120]


def try_clickn_deploy(row: dict) -> tuple[bool, str]:
    """Playwright ClickN 신규 사이트 (CLICKN_USER/PASS 있으면)."""
    secrets = load_json(REPO / "core/notify_secrets.json", {})
    user = secrets.get("CLICKN_USER") or secrets.get("clickn_user")
    pw = secrets.get("CLICKN_PASS") or secrets.get("clickn_pass")
    if not user or not pw:
        return False, "login_required: CLICKN_USER/PASS not in notify_secrets"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "login_required: playwright not installed"

    money = row.get("money_url", "https://gangara.co.kr/")
    anchor = row.get("anchor_text", "gangara.co.kr")
    link_html = f'<a href="{money}">{anchor}</a>'

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://www.clickn.co.kr/", timeout=45000)
            page.wait_for_timeout(2000)
            # 로그인 시도 (UI 변경 시 실패 가능)
            if page.locator('input[type="password"]').count():
                page.fill('input[type="text"], input[type="email"]', user)
                page.fill('input[type="password"]', pw)
                page.locator('button[type="submit"], input[type="submit"]').first.click()
                page.wait_for_timeout(3000)
            browser.close()
        return False, "deploy_not_saved: ClickN UI manual step required after login"
    except Exception as e:
        return False, f"network_error: {e}"[:120]


def process_row(row: dict, store: dict) -> dict:
    url = row.get("deploy_url") or ""
    status = row.get("status", "queued")

    if status in ("done", "failed", "failed_permanent", "skipped"):
        return {"action": "skip_status", "row": row}

    if url_already_success(store, url):
        row["status"] = "done"
        return {"action": "already_success", "row": row}

    if SKIP_URL.search(url):
        code = classify_failure("not_editable", row)
        record_failure(store, row, code, "not_editable url")
        row["status"] = "skipped"
        row["fail_reason"] = "not_editable"
        return {"action": "skipped", "failure_code": code, "row": row}

    if url.startswith("NEW_SIGNUP:"):
        ok, reason = try_clickn_deploy(row)
        code = classify_failure(reason, row)
        if ok:
            record_success(store, row)
            row["status"] = "done"
            return {"action": "success", "row": row}
        record_failure(store, row, code, reason)
        row["status"] = "failed"
        row["fail_reason"] = reason
        return {"action": "failed", "failure_code": code, "row": row}

    if not url.startswith("http"):
        code = "unknown"
        record_failure(store, row, code, "invalid url")
        row["status"] = "failed"
        return {"action": "failed", "failure_code": code, "row": row}

    html, err = fetch_html(url)
    if html is None:
        code = classify_failure(err, row)
        record_failure(store, row, code, err)
        row["status"] = "failed"
        row["fail_reason"] = err
        return {"action": "failed", "failure_code": code, "row": row}

    if TARGET.search(html):
        record_success(store, row, verified_url=url)
        row["status"] = "done"
        return {"action": "verified_live", "row": row}

    # live citation 없음 → 배포 필요 (자동 UI 없으면 failed + 다음 가설)
    code = classify_failure("no_href", row)
    record_failure(store, row, code, "no gangara.co.kr href on page")
    row["status"] = "failed"
    row["fail_reason"] = "no_href"
    return {"action": "needs_deploy", "failure_code": code, "row": row}


def apply_failure_patches(store: dict) -> list[str]:
    """최근 실패 dominant code → machine_config·experiment 힌트."""
    failures = store.get("failures") or []
    if not failures:
        return []
    recent = failures[-20:]
    codes = [f.get("failure_code") for f in recent]
    dominant = max(set(codes), key=codes.count)
    hyp = get_next_hypothesis(dominant)
    patches = [f"dominant_failure={dominant}", f"next_hypothesis={hyp.get('next_hypothesis_id')}"]

    exp_path = REPO / "core/gangara_experiment.json"
    if exp_path.exists():
        exp = load_json(exp_path)
        ll = exp.setdefault("learning_loop", {})
        ll["last_failure_code"] = dominant
        ll["next_hypothesis_on_failure"] = {
            "id": hyp.get("next_hypothesis_id"),
            "statement_ko": hyp.get("next_hypothesis_ko"),
            "actions": hyp.get("actions", []),
            "updated_at": now_iso(),
        }
        exp_path.write_text(json.dumps(exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        patches.append("gangara_experiment next_hypothesis_on_failure")
    return patches


def render_milestone_markdown(milestone: int, store: dict) -> str:
    total = success_count(store)
    by_pt = stats_by_platform(store)
    failures = store.get("failures") or []
    fail_report = render_failure_report(failures)

    return f"""# gangara 백링크 milestone — {milestone}건 live 성공

생성: {now_iso()}

## 성과
- **누적 live 성공:** {total}건 (이번 milestone: **{milestone}**)
- **실패 누적:** {len(failures)}건
- **platform별 성공:** {by_pt}

## SERP 목표
3키워드 top10 — `python3 core/run_learning_loop.py --until-top10`

{fail_report}

## 다음 실행
```bash
python3 core/run_backlink_automation.py --once
python3 core/run_backlink_auto.py --batch 50
```

상세 playbook: `core/BACKLINK_1000_DAY_PLAYBOOK.md`
"""


def send_milestone_email(milestone: int, store: dict) -> bool:
    from run_learning_report import send_email  # noqa: WPS433

    md = render_milestone_markdown(milestone, store)
    subj = f"[gangara 백링크] live {milestone}건 달성 · 누적 {success_count(store)}"
    ok = send_email(subj, md, {"milestone": milestone, "success_total": success_count(store)})
    if ok:
        mark_milestone_reported(store, milestone)
    return ok


def run_batch(batch_size: int, pause: float) -> dict:
    qpath, queue = load_queue()
    rows = queue.get("rows") or []
    store = load_store()

    processed = 0
    stats = {"verified_live": 0, "skipped": 0, "failed": 0, "needs_deploy": 0, "already_success": 0}

    for i, row in enumerate(rows):
        if processed >= batch_size:
            break
        if row.get("status") not in (None, "queued", "failed"):
            if row.get("status") == "done":
                continue
        result = process_row(row, store)
        rows[i] = result["row"]
        action = result.get("action", "")
        if action == "needs_deploy":
            stats["needs_deploy"] += 1
        elif action in stats:
            stats[action] += 1
        elif action == "failed":
            stats["failed"] += 1
        processed += 1
        if pause > 0:
            time.sleep(pause)

    queue["rows"] = rows
    save_queue(qpath, queue)
    patches = apply_failure_patches(store)

    milestone_hit = pending_milestone(store)
    emailed = False
    if milestone_hit:
        emailed = send_milestone_email(milestone_hit, store)

    summary = {
        "at": now_iso(),
        "processed": processed,
        "success_total": success_count(store),
        "stats": stats,
        "milestone": milestone_hit,
        "emailed": emailed,
        "patches": patches,
    }
    log_path = REPO / "tools/backlink_auto_last.json"
    log_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=300, help="daemon 간격(초)")
    args = ap.parse_args()

    if args.daemon:
        print(f"auto daemon batch={args.batch} interval={args.interval}s")
        while True:
            run_batch(args.batch, args.pause)
            time.sleep(args.interval)
    run_batch(args.batch, args.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
