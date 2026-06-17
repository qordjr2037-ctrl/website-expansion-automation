#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Crawl CDX + Bing link: search for referring domain estimates."""
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections import defaultdict

DOMAINS = [
    "gangara.co.kr",
    "choicelounge.co.kr",
    "gangnamdalto.co.kr",
    "classicsalong.com",
    "thesevensalon.com",
    "applegangnam.com",
    "gangnammirror.com",
    "gangnamko.co.kr",
    "richhuang.co.kr",
    "garaoke.clickn.co.kr",
]

CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; BacklinkProbe/1.0)"


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", errors="replace")


def get_cc_indexes():
    data = json.loads(fetch("https://index.commoncrawl.org/collinfo.json"))
    return [x["id"] for x in data[:4]]


def cc_backlinks(target_domain, indexes, limit=200):
    """Pages in CC whose url contains link to target (approximate via url= search on host pages)."""
    found = defaultdict(set)
    # Search crawl records where url field mentions target in link-out patterns is hard;
    # Use CDX url search for pages linking: search /* with filter not available free.
    # Proxy: count pages on target + search web for link: operator via DuckDuckGo HTML
    return {}


def duckduckgo_link_count(domain):
    q = urllib.parse.quote(f'link:{domain}')
    url = f"https://html.duckduckgo.com/html/?q={q}"
    try:
        html = fetch(url, timeout=20)
    except Exception as e:
        return {"error": str(e), "estimate_pages": 0, "sample_domains": []}
    links = re.findall(r'uddg=([^&"]+)', html)
    decoded = []
    for l in links:
        try:
            decoded.append(urllib.parse.unquote(l))
        except Exception:
            pass
    ext = []
    for u in decoded:
        m = re.search(r"https?://([^/]+)", u)
        if m:
            host = m.group(1).lower().replace("www.", "")
            if domain not in host:
                ext.append(host)
    unique = sorted(set(ext))
    return {
        "ddg_result_links": len(decoded),
        "sample_referring_hosts": unique[:15],
        "sample_count_unique": len(unique),
    }


def bing_link_search(domain):
    q = urllib.parse.quote(f"link:{domain}")
    url = f"https://www.bing.com/search?q={q}&count=50"
    try:
        html = fetch(url, timeout=20)
    except Exception as e:
        return {"error": str(e)}
    # Bing result count
    m = re.search(r"([\d,]+)\s+results", html, re.I)
    results = m.group(1).replace(",", "") if m else "?"
    hosts = []
    for u in re.findall(r'<cite[^>]*>([^<]+)</cite>', html):
        u = re.sub(r"\s+", "", u)
        host = u.split("/")[0].replace("www.", "")
        if domain not in host and "." in host:
            hosts.append(host)
    return {
        "bing_results_reported": results,
        "sample_referring_hosts": sorted(set(hosts))[:15],
        "sample_count_unique": len(set(hosts)),
    }


def main():
    out = {}
    for d in DOMAINS:
        row = {"domain": d}
        row["duckduckgo"] = duckduckgo_link_count(d)
        time.sleep(1.5)
        row["bing"] = bing_link_search(d)
        time.sleep(1.5)
        out[d] = row
        print(d, "ddg", row["duckduckgo"].get("sample_count_unique"), "bing", row["bing"].get("bing_results_reported"))
    path = __file__.replace("backlink_probe.py", "backlink_probe_output.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("WROTE", path)


if __name__ == "__main__":
    main()
