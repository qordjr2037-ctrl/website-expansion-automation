#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ClickN profile · roompang directory — Playwright 배포 배치."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))

from backlink_verified_store import (  # noqa: E402
    load_store,
    record_failure,
    record_success,
    save_store,
    url_already_success,
)
from failure_hypotheses import classify_failure  # noqa: E402

QUEUE_PATHS = [
    REPO / "core/backlink_deploy_queue_machine1.json",
    REPO / "core/backlink_deploy_queue.json",
]
SECRETS = REPO / "core/notify_secrets.json"
TARGET = re.compile(r"gangara\.co\.kr", re.I)
CLICKN_HOST = re.compile(r"\.clickn\.co\.kr", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_secrets() -> dict:
    data = load_json(SECRETS, {})
    for key in ("CLICKN_USER", "CLICKN_PASS", "ROOMPANG_USER", "ROOMPANG_PASS"):
        env = os.environ.get(key) or os.environ.get(key.lower())
        if env:
            data[key] = env
    return data


def load_queue() -> tuple[Path, dict]:
    for p in QUEUE_PATHS:
        if p.exists():
            return p, load_json(p, {})
    return QUEUE_PATHS[0], {"rows": []}


def save_queue(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def link_html(money_url: str, anchor: str) -> str:
    return f'<a href="{money_url}" rel="dofollow">{anchor}</a>'


def page_has_target(page) -> bool:
    try:
        html = page.content()
        return bool(TARGET.search(html))
    except Exception:
        return False


def clickn_login(page, user: str, password: str) -> bool:
    page.goto("https://www.clickn.co.kr/member/login", timeout=45000)
    page.wait_for_timeout(1500)
    if page.locator('input[type="password"]').count() == 0:
        return "login" not in page.url.lower()
    page.locator('input[type="text"], input[type="email"], input[name="id"]').first.fill(user)
    page.locator('input[type="password"]').first.fill(password)
    for sel in ('button[type="submit"]', 'input[type="submit"]', 'text=로그인', 'text=Login'):
        try:
            page.locator(sel).first.click(timeout=3000)
            break
        except Exception:
            continue
    page.wait_for_timeout(3500)
    return "login" not in page.url.lower() or page.locator('text=로그아웃').count() > 0


def clickn_edit_site_footer(page, deploy_url: str, money_url: str, anchor: str) -> tuple[bool, str]:
    """ClickN 대시보드 → 사이트 편집 → footer HTML 삽입."""
    page.goto(deploy_url, timeout=45000)
    page.wait_for_timeout(2000)
    if page_has_target(page):
        return True, "already_live"

    # 사이트 관리 / 편집 진입 시도
    for sel in (
        'text=관리',
        'text=편집',
        'text=수정',
        'a[href*="admin"]',
        'a[href*="edit"]',
        'text=디자인',
    ):
        try:
            if page.locator(sel).count():
                page.locator(sel).first.click(timeout=4000)
                page.wait_for_timeout(2000)
                break
        except Exception:
            continue

    html_snippet = link_html(money_url, anchor)
    injected = False
    for sel in (
        'textarea',
        '[contenteditable="true"]',
        'iframe',
    ):
        try:
            loc = page.locator(sel)
            if loc.count() == 0:
                continue
            if sel == "iframe":
                frame = loc.first.content_frame()
                if frame and frame.locator("body").count():
                    frame.locator("body").evaluate(
                        f'(el) => {{ el.insertAdjacentHTML("beforeend", `{html_snippet}`); }}'
                    )
                    injected = True
                    break
            else:
                loc.first.fill(html_snippet)
                injected = True
                break
        except Exception:
            continue

    if not injected:
        return False, "deploy_not_saved: no editable footer field found"

    for sel in ('text=저장', 'text=Save', 'button[type="submit"]', 'text=적용'):
        try:
            if page.locator(sel).count():
                page.locator(sel).first.click(timeout=4000)
                page.wait_for_timeout(2500)
                break
        except Exception:
            continue

    page.goto(deploy_url, timeout=45000)
    page.wait_for_timeout(2000)
    if page_has_target(page):
        return True, "deploy_saved"
    return False, "deploy_not_saved: href not visible after save"


def deploy_row(page, row: dict, secrets: dict) -> tuple[bool, str]:
    url = row.get("deploy_url") or ""
    money = row.get("money_url", "https://gangara.co.kr/")
    anchor = row.get("anchor_text", "gangara.co.kr")
    pt = row.get("platform_type", "")
    skip = re.compile(r"search\?q=|choicelounge|seoulafterdark|postheaven|blogspot", re.I)

    if skip.search(url):
        return False, "not_editable: search or third-party URL"

    if CLICKN_HOST.search(url) or pt == "profile":
        user = secrets.get("CLICKN_USER") or secrets.get("clickn_user")
        pw = secrets.get("CLICKN_PASS") or secrets.get("clickn_pass")
        if not user or not pw:
            return False, "login_required: CLICKN_USER/PASS not in notify_secrets"
        if not clickn_login(page, user, pw):
            return False, "login_required: ClickN login failed"
        return clickn_edit_site_footer(page, url, money, anchor)

    if pt == "guide_hub":
        return False, "not_editable: third-party guide_hub — skip"

    if pt == "directory" and "roompang" in url:
        user = secrets.get("ROOMPANG_USER") or secrets.get("roompang_user")
        pw = secrets.get("ROOMPANG_PASS") or secrets.get("roompang_pass")
        if not user or not pw:
            return False, "login_required: ROOMPANG_USER/PASS not in notify_secrets"
        page.goto("https://www.roompang.com/member/login", timeout=45000)
        page.wait_for_timeout(1500)
        try:
            page.locator('input[type="text"], input[name="id"], input[name="email"]').first.fill(user)
            page.locator('input[type="password"]').first.fill(pw)
            page.locator('button[type="submit"], input[type="submit"]').first.click(timeout=5000)
            page.wait_for_timeout(3000)
        except Exception as e:
            return False, f"login_required: roompang login UI: {e}"[:120]
        page.goto(url, timeout=45000)
        page.wait_for_timeout(2000)
        if page_has_target(page):
            return True, "already_live"
        return False, "deploy_not_saved: roompang manual listing edit required"

    return False, "not_editable: no deploy adapter for this URL"


def pick_rows(rows: list[dict], limit: int, tier: str | None, platform: str | None = None) -> list[tuple[int, dict]]:
    picked: list[tuple[int, dict]] = []
    for i, row in enumerate(rows):
        if row.get("status") not in (None, "queued", "failed", "new_signup"):
            continue
        url = row.get("deploy_url") or ""
        if not url.startswith("http"):
            continue
        if tier and row.get("tier_hint") != tier:
            continue
        if platform and row.get("platform_type") != platform:
            continue
        picked.append((i, row))
        if len(picked) >= limit:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="배포 시도 row 수")
    ap.add_argument("--tier", default="", help="tier_hint 필터 (S, A, 빈=전체)")
    ap.add_argument("--platform", default="", help="platform_type 필터 (profile, directory, …)")
    ap.add_argument("--headless", action="store_true", default=True)
    ap.add_argument("--no-headless", dest="headless", action="store_false")
    args = ap.parse_args()

    secrets = load_secrets()
    qpath, queue = load_queue()
    rows = queue.get("rows") or []
    store = load_store()
    tier = args.tier if args.tier else None
    platform = args.platform if args.platform else None
    batch = pick_rows(rows, args.limit, tier, platform)

    if not batch:
        print("No deployable rows in queue")
        return 0

    from playwright.sync_api import sync_playwright

    stats = {"success": 0, "failed": 0, "skipped": 0}
    headless = args.headless and os.environ.get("HEADLESS", "1") != "0"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 TrackB-Deploy/1.0"})

        for idx, row in batch:
            url = row.get("deploy_url", "")
            if url_already_success(store, url):
                rows[idx]["status"] = "done"
                stats["skipped"] += 1
                continue

            ok, reason = deploy_row(page, row, secrets)
            if ok:
                record_success(store, row, verified_url=url)
                rows[idx]["status"] = "done"
                rows[idx]["deploy_result"] = reason
                stats["success"] += 1
                print(f"OK {url} — {reason}")
            else:
                code = classify_failure(reason, row)
                record_failure(store, row, code, reason)
                rows[idx]["status"] = "failed"
                rows[idx]["fail_reason"] = reason
                stats["failed"] += 1
                print(f"FAIL {url} — {reason}")

        browser.close()

    queue["rows"] = rows
    save_queue(qpath, queue)
    save_store(store)

    summary = {"at": now_iso(), "processed": len(batch), **stats}
    out = REPO / "tools/backlink_deploy_last.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if stats["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
