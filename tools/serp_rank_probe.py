#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gangara.co.kr SERP 순위 프로브 — 실험 전·후 비교용.
DuckDuckGo lite HTML에서 키워드 검색 후 gangara.co.kr 노출 순위 기록.
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
EXPERIMENT = REPO / "core/gangara_experiment.json"
CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; GangaraRankProbe/1.0)"

DEFAULT_KEYWORDS = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"]
TARGET_DOMAIN = "gangara.co.kr"
RESULT_LINK = re.compile(r'uddg=([^&"]+)')


def ddg_search(keyword: str, max_results: int = 30) -> list[str]:
    q = urllib.parse.quote_plus(keyword)
    url = f"https://lite.duckduckgo.com/lite/?q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    urls: list[str] = []
    for m in RESULT_LINK.finditer(html):
        decoded = urllib.parse.unquote(m.group(1))
        if decoded.startswith("http") and decoded not in urls:
            urls.append(decoded)
        if len(urls) >= max_results:
            break
    return urls


def find_rank(urls: list[str], domain: str = TARGET_DOMAIN) -> int | None:
    for i, u in enumerate(urls, start=1):
        if domain in u.lower():
            return i
    return None


def probe_keywords(keywords: list[str]) -> dict:
    results = []
    for kw in keywords:
        urls = ddg_search(kw)
        rank = find_rank(urls)
        results.append(
            {
                "keyword": kw,
                "rank": rank,
                "in_top10": rank is not None and rank <= 10,
                "in_top30": rank is not None and rank <= 30,
                "sample_urls": urls[:5],
            }
        )
        time.sleep(1.2)

    in_top10 = sum(1 for r in results if r["in_top10"])
    return {
        "probed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_domain": TARGET_DOMAIN,
        "provider": "duckduckgo_lite",
        "keywords_probed": len(keywords),
        "in_top10_count": in_top10,
        "results": results,
    }


def merge_experiment(probe: dict) -> None:
    exp = {}
    if EXPERIMENT.exists():
        exp = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    history = exp.setdefault("rank_history", [])
    history.append(probe)
    exp["last_probe"] = probe
    exp["updated_at"] = probe["probed_at"]
    EXPERIMENT.parent.mkdir(parents=True, exist_ok=True)
    EXPERIMENT.write_text(json.dumps(exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
    parser.add_argument("--merge-experiment", action="store_true")
    args = parser.parse_args()

    probe = probe_keywords(args.keywords)
    OUT.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.merge_experiment:
        merge_experiment(probe)

    print(json.dumps(probe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
