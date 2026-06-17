# -*- coding: utf-8 -*-
"""SERP → URL 후보 수집 (게시판 제외). DuckDuckGo lite + 시드."""
from __future__ import annotations

import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

from placement_classifier import is_board_url

REPO = Path(__file__).resolve().parents[3]
QUERIES_FILE = REPO / "website 확장 수집/misc/data/serp_backlink_queries.txt"
CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; TrackB-Collector/1.0)"

# P0/P1/P2 시드 — roompang·clickn·guide_hub·directory
SEED_URLS: list[tuple[str, str]] = [
    ("강남 가라오케", "https://roompang.com/"),
    ("강남 풀싸롱", "https://roompang.com/"),
    ("강남 하이퍼블릭", "https://roompang.com/"),
    ("강남 가라오케", "https://www.clickn.co.kr/"),
    ("강남 풀싸롱", "https://clicknn.co.kr/pages/gangnampoolsalon"),
    ("강남 하이퍼블릭", "https://clicknn.co.kr/pages/gangnamhyperbolic"),
    ("강남 가라오케", "https://choicelounge.co.kr/"),
    ("강남 풀싸롱", "https://choicelounge.co.kr/"),
    ("강남 하이퍼블릭", "https://gangnamdalto.co.kr/"),
    ("강남 가라오케", "https://gangnamko.co.kr/"),
    ("강남 풀싸롱", "https://classicsalong.com/"),
    ("강남 하이퍼블릭", "https://gangnammirror.com/"),
    ("강남 가라오케", "https://garaoke.clickn.co.kr/"),
    ("강남 풀싸롱", "https://applegangnam.com/"),
    ("강남 하이퍼블릭", "https://thesevensalon.com/"),
    ("강남 유흥", "https://www.korea.kr/"),
    ("강남 가라오케", "https://www.safetyreport.go.kr/"),
]

RESULT_LINK = re.compile(r'uddg=([^&"]+)')


def load_query_templates() -> list[str]:
    if not QUERIES_FILE.exists():
        return ['{keyword} "FAQ" "주대" site:co.kr -inurl:write.php']
    lines = []
    for line in QUERIES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines or ['{keyword} -inurl:write.php -inurl:bbs']


def ddg_search(query: str, max_results: int = 8) -> list[str]:
    q = urllib.parse.quote_plus(query)
    url = f"https://lite.duckduckgo.com/lite/?q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=CTX) as resp:
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

    # fallback: href pattern
    if not urls:
        for m in re.finditer(r'href="(https?://[^"]+)"', html):
            u = m.group(1)
            if "duckduckgo" not in u and u not in urls:
                urls.append(u)
            if len(urls) >= max_results:
                break
    return urls


def collect_for_keyword(keyword: str, max_per_query: int = 6) -> list[dict]:
    """Return [{url, target_keyword, serp_rank, source}]."""
    seen: set[str] = set()
    rows: list[dict] = []

    def add(url: str, rank: int, source: str) -> None:
        if url in seen or is_board_url(url):
            return
        seen.add(url)
        rows.append(
            {
                "url": url,
                "target_keyword": keyword,
                "serp_rank": rank,
                "source": source,
            }
        )

    for kw, seed in SEED_URLS:
        if kw == keyword:
            add(seed, 1, "seed")

    templates = load_query_templates()
    rank = 1
    for tpl in templates[:3]:
        query = tpl.replace("{keyword}", keyword)
        for u in ddg_search(query, max_results=max_per_query):
            add(u, rank, "ddg")
            rank += 1
        time.sleep(0.8)

    return rows


def collect_keywords(keywords: list[str]) -> list[dict]:
    all_rows: list[dict] = []
    global_seen: set[str] = set()
    for kw in keywords:
        for row in collect_for_keyword(kw):
            if row["url"] not in global_seen:
                global_seen.add(row["url"])
                all_rows.append(row)
    return all_rows
