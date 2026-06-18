# -*- coding: utf-8 -*-
"""SERP → URL 후보 수집 (게시판 제외). DuckDuckGo lite + 시드."""
from __future__ import annotations

import re
import ssl
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path

from placement_classifier import is_board_url

REPO = Path(__file__).resolve().parents[3]
QUERIES_FILE = REPO / "website 확장 수집/misc/data/serp_backlink_queries.txt"
LEARNING_SEEDS = REPO / "website 확장 수집/misc/data/learning_seeds.json"
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
    # experiment: directory·guide_hub 집중 시드
    ("강남 가라오케", "https://roompang.com/search?q=강남+가라오케"),
    ("강남 풀싸롱", "https://roompang.com/search?q=강남+풀싸롱"),
    ("강남 하이퍼블릭", "https://roompang.com/search?q=강남+하이퍼블릭"),
    ("강남 가라오케", "https://gangnamhigh.clickn.co.kr/"),
    ("강남 하이퍼블릭", "https://gangnamhigh.clickn.co.kr/"),
    ("강남 풀싸롱", "https://gangnamko.co.kr/"),
    ("강남 가라오케", "https://choicelounge.co.kr/gangnam-garaoke/"),
    ("강남 풀싸롱", "https://choicelounge.co.kr/poolsalon/"),
    ("강남 하이퍼블릭", "https://choicelounge.co.kr/highpublic/"),
    # 풀싸롱 SERP 벤치마크 시드 (coverage 보강)
    ("강남 풀싸롱", "https://www.gangnamfullssalong.com/"),
    ("강남 풀싸롱", "https://www.fullssawara.com/"),
    ("강남 풀싸롱", "https://www.levelhotelsalon.com/"),
    ("강남 풀싸롱", "https://www.classicnamu.com/"),
    ("강남 풀싸롱", "https://gangnammirror.com/"),
    ("강남 풀싸롱", "https://thesevensalon.com/"),
    ("강남 풀싸롱", "https://roompang.com/guide/gangnam-poolsalon"),
    ("강남 풀싸롱", "https://www.gugudano.com/"),
    ("강남 풀싸롱", "https://hypublic.com/gangnam-poolsalon/"),
    ("강남 풀싸롱", "https://gangnamko.co.kr/poolsalon/"),
    ("강남 하이퍼블릭", "https://www.roompang.com/guide/gangnam-hyperpublic"),
    ("강남 하이퍼블릭", "https://gangnam-highpublic.com/"),
    ("강남 가라오케", "https://www.karaokegangnam.net/"),
]


def load_learning_seeds() -> list[tuple[str, str]]:
    """학습 루프가 SERP top URL로 추가한 동적 시드."""
    if not LEARNING_SEEDS.exists():
        return []
    try:
        data = json.loads(LEARNING_SEEDS.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[tuple[str, str]] = []
    for row in data.get("seeds", []):
        kw, url = row.get("keyword"), row.get("url")
        if kw and url:
            out.append((kw, url))
    return out


def all_seed_urls() -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    combined: list[tuple[str, str]] = []
    for item in SEED_URLS + load_learning_seeds():
        if item not in seen:
            seen.add(item)
            combined.append(item)
    return combined


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

    for kw, seed in all_seed_urls():
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
