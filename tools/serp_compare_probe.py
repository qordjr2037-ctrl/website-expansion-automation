#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import ssl
import urllib.request
from urllib.error import URLError

SITES = [
    ("gangara.co.kr (YOU)", "https://gangara.co.kr"),
    ("gangnamdalto.co.kr", "https://gangnamdalto.co.kr"),
    ("garaoke.clickn.co.kr", "https://garaoke.clickn.co.kr"),
    ("richhuang.co.kr", "https://richhuang.co.kr"),
    ("gangnamko.co.kr", "https://gangnamko.co.kr"),
    ("clicknn/pages", "https://www.clicknn.co.kr/pages/gangnamnoraeppa"),
    ("classicsalong.com", "https://classicsalong.com"),
    ("thesevensalon.com", "https://thesevensalon.com"),
    ("applegangnam.com", "https://applegangnam.com"),
    ("gangnammirror.com", "https://gangnammirror.com"),
    ("choicelounge.co.kr", "https://choicelounge.co.kr"),
]

KW = ["강남", "가라오케", "하이퍼블릭", "풀싸롱", "쩜오", "주대", "초이스"]


def fetch(url):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SERPProbe/1.0)"})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        raw = r.read()
        enc = "utf-8"
        ct = r.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ct, re.I)
        if m:
            enc = m.group(1)
        try:
            html = raw.decode(enc, errors="replace")
        except LookupError:
            html = raw.decode("utf-8", errors="replace")
        return html, dict(r.headers)


def analyze(name, url):
    row = {"name": name, "url": url}
    try:
        html, headers = fetch(url)
    except Exception as e:
        row["error"] = str(e)
        return row

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""
    h1s = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)]
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    faq_blocks = len(re.findall(r"(?i)(자주\s*묻|FAQ|질문\s*\d|accordion|details\s*>)", html))
    faq_schema = bool(re.search(r"FAQPage", html))
    price_hits = len(re.findall(r"주대|TC|룸티|가격표|1부|2부|비교표", text))
    nap_hits = len(re.findall(r"주소|지하철|영업시간|역삼|선릉|강남역|네이버\s*지도|카카오\s*맵", text))
    tel = len(re.findall(r"010[-\s]?\d{4}[-\s]?\d{4}", html))
    tables = len(re.findall(r"<table", html, re.I))
    internal = len(re.findall(r"""href=["'](?!http|mailto|tel|#)[^"']+["']""", html))
    external = len(re.findall(r"""href=["']https?://[^"']+["']""", html))

    row.update(
        {
            "html_bytes": len(html),
            "text_chars": len(text),
            "title": title[:120],
            "title_kw": sum(1 for k in KW if k in title),
            "h1_count": len(h1s),
            "h1": (h1s[0][:80] if h1s else ""),
            "h1_kw": sum(1 for k in KW if h1s and any(k in h for h in h1s)),
            "faq_signals": faq_blocks,
            "faq_schema": faq_schema,
            "price_signals": price_hits,
            "nap_signals": nap_hits,
            "tel_count": tel,
            "table_count": tables,
            "internal_links": internal,
            "external_links": external,
            "wordpress": bool(re.search(r"wp-content|wordpress", html, re.I)),
            "clickn": bool(re.search(r"clickn|clicknn", html, re.I)),
            "schema_json": bool(re.search(r"application/ld\+json", html, re.I)),
            "server": headers.get("Server", ""),
        }
    )

    # on_page_score from SERP_RANKING_VS_INVISIBLE.txt
    score = 0
    if any(k in title for k in ["강남", "가라오케", "하이퍼블릭", "풀싸롱"]):
        score += 20
    if h1s and any(k in h1s[0] for k in ["강남", "가라오케", "하이퍼블릭", "풀싸롱"]):
        score += 15
    if faq_blocks >= 5 or faq_schema:
        score += 15
    if price_hits >= 5:
        score += 15
    if nap_hits >= 3:
        score += 10
    if len(text) >= 3000:
        score += 10
    if internal >= 5:
        score += 10
    if re.search(r"bbs|write\.php", url, re.I):
        score -= 30
    if len(text) < 500:
        score -= 20
    row["on_page_score_est"] = score
    return row


def main():
    out = [analyze(n, u) for n, u in SITES]
    path = __file__.replace("serp_compare_probe.py", "serp_probe_output.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(path)


if __name__ == "__main__":
    main()
