#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gangara.co.kr SERP 순위 딥 프로브 — 후순위까지 탐색.
DDG lite/html · Bing · site: 인덱스 확인.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "tools/serp_rank_probe_output.json"
DEEP_OUT = REPO / "tools/serp_rank_deep_output.json"
EXPERIMENT = REPO / "core/gangara_experiment.json"
CTX = ssl.create_default_context()
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_KEYWORDS = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"]
TARGET_DOMAINS = ["gangara.co.kr", "gangara.netlify.app"]
DDG_UDDG = re.compile(r'uddg=([^&"]+)')
BING_LINK = re.compile(r'<li class="b_algo".*?<a href="(https?://[^"]+)"', re.S)
GENERIC_HREF = re.compile(r'href="(https?://[^"]+)"')


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_ddg_urls(html: str, limit: int = 100) -> list[str]:
    urls: list[str] = []
    for m in DDG_UDDG.finditer(html):
        u = urllib.parse.unquote(m.group(1))
        if u.startswith("http") and u not in urls:
            urls.append(u)
        if len(urls) >= limit:
            break
    if len(urls) < 5:
        for m in GENERIC_HREF.finditer(html):
            u = m.group(1)
            if "duckduckgo" not in u and u not in urls:
                urls.append(u)
            if len(urls) >= limit:
                break
    return urls


def ddg_lite(keyword: str, limit: int = 50) -> list[str]:
    q = urllib.parse.quote_plus(keyword)
    try:
        return extract_ddg_urls(fetch(f"https://lite.duckduckgo.com/lite/?q={q}"), limit)
    except Exception:
        return []


def ddg_html(keyword: str, pages: int = 3) -> list[str]:
    urls: list[str] = []
    for page in range(pages):
        q = urllib.parse.quote_plus(keyword)
        offset = page * 30
        url = f"https://html.duckduckgo.com/html/?q={q}&s={offset}"
        try:
            html = fetch(url)
        except Exception:
            break
        batch = extract_ddg_urls(html, 40)
        for u in batch:
            if u not in urls:
                urls.append(u)
        if not batch:
            break
        time.sleep(0.8)
    return urls


def bing_search(keyword: str, pages: int = 5) -> list[str]:
    urls: list[str] = []
    for page in range(pages):
        first = page * 10 + 1
        q = urllib.parse.quote_plus(keyword)
        url = f"https://www.bing.com/search?q={q}&count=10&first={first}"
        try:
            html = fetch(url)
        except Exception:
            break
        batch: list[str] = []
        for m in BING_LINK.finditer(html):
            u = m.group(1)
            if u.startswith("http") and "bing.com" not in u:
                batch.append(u)
        if not batch:
            for m in GENERIC_HREF.finditer(html):
                u = m.group(1)
                if u.startswith("http") and "bing.com" not in u and "microsoft" not in u:
                    batch.append(u)
        added = 0
        for u in batch:
            if u not in urls:
                urls.append(u)
                added += 1
        if added == 0:
            break
        time.sleep(0.8)
    return urls


def site_index(keyword: str, domain: str = "gangara.co.kr") -> dict:
    q = urllib.parse.quote_plus(f"site:{domain} {keyword}")
    urls: list[str] = []
    for provider, fn in [
        ("ddg_lite", lambda: ddg_lite(f"site:{domain} {keyword}", 20)),
        ("bing", lambda: bing_search(f"site:{domain} {keyword}", 2)),
    ]:
        try:
            found = fn()
            for u in found:
                if domain in u and u not in urls:
                    urls.append(u)
        except Exception:
            pass
    return {
        "query": f"site:{domain} {keyword}",
        "indexed_urls": urls,
        "indexed_count": len(urls),
    }


def find_rank(urls: list[str], domains: list[str] | None = None) -> dict:
    domains = domains or TARGET_DOMAINS
    for i, u in enumerate(urls, start=1):
        low = u.lower()
        for d in domains:
            if d in low:
                return {"rank": i, "matched_url": u, "matched_domain": d}
    return {"rank": None, "matched_url": None, "matched_domain": None}


def probe_keyword_deep(keyword: str) -> dict:
    providers = {}

    ddg_l = ddg_lite(keyword, 50)
    providers["ddg_lite"] = {
        "result_count": len(ddg_l),
        **find_rank(ddg_l),
        "top10": ddg_l[:10],
    }
    time.sleep(1)

    ddg_h = ddg_html(keyword, pages=4)
    providers["ddg_html"] = {
        "result_count": len(ddg_h),
        **find_rank(ddg_h),
        "top10": ddg_h[:10],
    }
    time.sleep(1)

    bing = bing_search(keyword, pages=5)
    providers["bing"] = {
        "result_count": len(bing),
        **find_rank(bing),
        "top10": bing[:10],
    }
    time.sleep(1)

    idx = site_index(keyword)

    # best rank across providers
    ranks = [p["rank"] for p in providers.values() if p.get("rank")]
    best = min(ranks) if ranks else None
    best_provider = None
    best_url = None
    for name, p in providers.items():
        if p.get("rank") == best:
            best_provider = name
            best_url = p.get("matched_url")
            break

    return {
        "keyword": keyword,
        "best_rank": best,
        "best_provider": best_provider,
        "best_matched_url": best_url,
        "indexed": idx,
        "providers": providers,
    }


def run_deep(keywords: list[str]) -> dict:
    results = []
    for kw in keywords:
        results.append(probe_keyword_deep(kw))
        time.sleep(1.5)

    found_any = [r for r in results if r["best_rank"] is not None]
    return {
        "probed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "deep",
        "target_domains": TARGET_DOMAINS,
        "keywords_probed": len(keywords),
        "found_in_serp_count": len(found_any),
        "results": results,
    }


def merge_experiment(probe: dict) -> None:
    exp = {}
    if EXPERIMENT.exists():
        exp = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    exp.setdefault("rank_history", []).append(probe)
    exp["last_deep_probe"] = probe
    exp["updated_at"] = probe["probed_at"]
    EXPERIMENT.write_text(json.dumps(exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
    parser.add_argument("--merge-experiment", action="store_true")
    args = parser.parse_args()

    probe = run_deep(args.keywords)
    DEEP_OUT.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.merge_experiment:
        merge_experiment(probe)

    print(json.dumps(probe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
