#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포 후 live href 검증 (Phase 3 스텁)."""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUEUE = REPO / "core/backlink_deploy_queue.json"
TARGET = re.compile(r"gangara\.co\.kr", re.I)
CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; TrackB-Verify/1.0)"


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read(50000).decode("utf-8", errors="replace")


def verify_row(row: dict) -> dict:
    url = row.get("deploy_url", "")
    if not url.startswith("http") or url.startswith("NEW_SIGNUP:"):
        return {"url": url, "live": False, "reason": "not_deployed_yet"}
    try:
        html = fetch(url)
        live = bool(TARGET.search(html))
        return {"url": url, "live": live, "reason": "ok" if live else "no_href"}
    except Exception as e:
        return {"url": url, "live": False, "reason": str(e)[:80]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--today", action="store_true")
    args = ap.parse_args()

    path = QUEUE
    if not path.exists():
        print("queue not found")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [r for r in data.get("rows", []) if r.get("status") == "done"]
    if not rows:
        rows = data.get("rows", [])[: args.sample]

    results = [verify_row(r) for r in rows[: args.sample]]
    live_n = sum(1 for r in results if r["live"])
    print(json.dumps({"checked": len(results), "live": live_n, "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
