# -*- coding: utf-8 -*-
"""
SmallSEOTools 백링크 체커 + 2captcha(Turnstile) → DR/RD/백링크 실측.
결과: tools/backlink_live_output.json (+ --merge-audit 로 audit JSON 병합)
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from secrets_loader import ensure_env_file, load_secrets

SST_URL = "https://smallseotools.com/backlink-checker/"
SST_TURNSTILE_SITEKEY = "0x4AAAAAAAcJkOV11SoqC-Ws"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
CTX = ssl.create_default_context()
TOOLS_DIR = Path(__file__).resolve().parent
REPO = TOOLS_DIR.parent

DEFAULT_DOMAINS = [
    "gangara.co.kr",
    "choicelounge.co.kr",
    "gangnamdalto.co.kr",
    "classicsalong.com",
    "thesevensalon.com",
    "applegangnam.com",
    "gangnammirror.com",
    "gangnamko.co.kr",
    "richhuang.co.kr",
]


def solve_turnstile(api_key: str, sitekey: str, pageurl: str) -> str:
    payload = {
        "key": api_key,
        "method": "turnstile",
        "sitekey": sitekey,
        "pageurl": pageurl,
        "json": 1,
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request("https://2captcha.com/in.php", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
        j = json.loads(r.read().decode())
    if j.get("status") != 1:
        raise RuntimeError(f"2captcha submit failed: {j}")
    task_id = str(j["request"])
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(5)
        q = urllib.parse.urlencode(
            {"key": api_key, "action": "get", "id": task_id, "json": 1}
        )
        req2 = urllib.request.Request(f"https://2captcha.com/res.php?{q}")
        with urllib.request.urlopen(req2, timeout=30, context=CTX) as r:
            j2 = json.loads(r.read().decode())
        if j2.get("status") == 1:
            return str(j2["request"])
        if str(j2.get("request", "")).upper() != "CAPCHA_NOT_READY":
            raise RuntimeError(f"2captcha poll failed: {j2}")
    raise TimeoutError("2captcha turnstile timeout")


def extract_csrf(html: str) -> str:
    m = re.search(r'name="_token"\s+type="hidden"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'name="_token"\s+value="([^"]+)"', html)
    if not m:
        raise ValueError("CSRF _token not found")
    return m.group(1)


class SstSession:
    """Laravel 세션 + XSRF + submission 쿠키 유지."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=CTX),
        )

    def _xsrf(self) -> str:
        for c in self.jar:
            if c.name == "XSRF-TOKEN":
                return urllib.parse.unquote(c.value)
        return ""

    def _set_submission_cookie(self) -> None:
        self.jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name="submission",
                value="done",
                port=None,
                port_specified=False,
                domain=".smallseotools.com",
                domain_specified=True,
                domain_initial_dot=True,
                path="/",
                path_specified=True,
                secure=True,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
        )

    def fetch(self, url: str, *, method: str = "GET", data: bytes | None = None, headers: dict | None = None):
        h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", **(headers or {})}
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        return self.opener.open(req, timeout=90)

    def get_form_page(self) -> tuple[int, str]:
        with self.fetch(SST_URL) as r:
            return r.status, r.read().decode("utf-8", errors="replace")

    def post_check(self, url_target: str, token: str, turnstile_token: str) -> tuple[int, str]:
        self._set_submission_cookie()
        form = urllib.parse.urlencode(
            {
                "_token": token,
                "url": url_target,
                "cf-turnstile-response": turnstile_token,
            }
        ).encode()
        headers = {
            "Referer": SST_URL,
            "Origin": "https://smallseotools.com",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        xsrf = self._xsrf()
        if xsrf:
            headers["X-XSRF-TOKEN"] = xsrf
        with self.fetch(SST_URL, method="POST", data=form, headers=headers) as r:
            return r.status, r.read().decode("utf-8", errors="replace")


def parse_sst_metrics(html: str) -> dict[str, Any]:
    """SmallSEOTools(Semrush 데이터) 결과 HTML 파싱."""
    out: dict[str, Any] = {
        "source": "smallseotools_semrush",
        "parsed": False,
        "provider_note": "Semrush 데이터 via SmallSEOTools 무료 체커",
    }

    if "BacklinkChecker_res" not in html:
        if re.search(r"Page Expired|HTTP 419|419 Page Expired", html, re.I):
            out["error"] = "csrf_419"
        elif re.search(r"ad-blocker|It looks like you", html, re.I):
            out["blocked"] = "adblocker_warning"
        else:
            out["error"] = "no_result_section"
        return out

    m = re.search(
        r"backlink_circle[\s\S]*?<strong>(\d+(?:\.\d+)?)\s*</strong>[\s\S]*?Domain Rating",
        html,
        re.I,
    )
    if m:
        out["dr"] = int(float(m.group(1)))
        out["parsed"] = True

    for key, cls in (
        ("referring_urls", "back_box1"),
        ("backlinks_total", "back_box2"),
        ("referring_domains", "back_box3"),
        ("referring_ips", "back_box4"),
    ):
        block = re.search(rf'class="{cls}[\s\S]*?(?=class="back_box|\Z)', html, re.I)
        if not block:
            continue
        chunk = block.group(0)
        tm = re.search(r'title="([\d,]+)"', chunk)
        if not tm:
            tm = re.search(r'class="fs24"[^>]*>([\d.K]+)', chunk)
        if tm:
            raw = tm.group(1).replace(",", "")
            if raw.endswith("K"):
                out[key] = int(float(raw[:-1]) * 1000)
            else:
                out[key] = int(float(raw))
            out["parsed"] = True

    for label, key in (("Dofollow", "dofollow"), ("No Follow", "nofollow")):
        dm = re.search(rf">{label}\s*-\s*([\d.K,]+)<", html, re.I)
        if dm:
            val = dm.group(1).replace(",", "")
            out[key] = int(float(val[:-1]) * 1000) if val.endswith("K") else int(float(val))

    samples: list[str] = []
    for um in re.finditer(
        r'class="row m-0 ip_res fw_600">[\s\S]*?href="(https?://[^"]+)" target="_blank"',
        html,
    ):
        u = um.group(1)
        if "smallseotools.com" not in u and "semrush.sjv.io" not in u:
            samples.append(u)
    out["sample_backlinks"] = samples[:8]

    return out


def fetch_smallseotools(domain: str, api_key: str) -> dict[str, Any]:
    url_target = domain if domain.startswith("http") else f"https://{domain}/"
    session = SstSession()
    status, html = session.get_form_page()
    if status != 200:
        return {"domain": domain, "error": f"GET {status}", "source": "smallseotools_semrush"}

    token = extract_csrf(html)
    turnstile_token = solve_turnstile(api_key, SST_TURNSTILE_SITEKEY, SST_URL)
    status2, html2 = session.post_check(url_target, token, turnstile_token)

    metrics = parse_sst_metrics(html2)
    metrics["domain"] = domain
    metrics["http_status"] = status2
    metrics["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not metrics.get("parsed") and not metrics.get("error"):
        metrics["error"] = "parse_failed"
    return metrics


def merge_into_audit(live_path: Path, audit_path: Path) -> None:
    live = json.loads(live_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    by_domain = {r["domain"]: r for r in live.get("results", [])}

    for rep in audit.get("reports", []):
        d = rep["domain"]
        m = by_domain.get(d)
        if not m or not m.get("parsed"):
            continue
        rep["sst_dr"] = m.get("dr")
        rep["sst_referring_domains"] = m.get("referring_domains")
        rep["sst_backlinks_total"] = m.get("backlinks_total")
        rep["sst_referring_urls"] = m.get("referring_urls")
        rep["sst_sample_backlinks"] = m.get("sample_backlinks", [])
        rep["data_sources"] = list(dict.fromkeys([*(rep.get("data_sources") or []), "smallseotools_live"]))
        rep["notes"] = [n for n in rep.get("notes", []) if "SmallSEOTools" not in n]
        rep["notes"].insert(
            0,
            f"SmallSEOTools 실측(Semrush): DR={m.get('dr')} RD={m.get('referring_domains')} BL={m.get('backlinks_total')}",
        )

    audit["live_sst_collected_at"] = live.get("generated_at")
    audit["live_sst_provider"] = live.get("provider")
    audit["live_sst_summary"] = [
        {
            "domain": r["domain"],
            "dr": r.get("dr"),
            "referring_domains": r.get("referring_domains"),
            "backlinks_total": r.get("backlinks_total"),
            "referring_urls": r.get("referring_urls"),
            "sample_backlinks": (r.get("sample_backlinks") or [])[:3],
            "status": "ok" if r.get("parsed") else r.get("error", "fail"),
        }
        for r in live.get("results", [])
    ]
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def update_comparison_doc(live_path: Path, doc_path: Path) -> None:
    live = json.loads(live_path.read_text(encoding="utf-8"))
    rows = []
    for r in live.get("results", []):
        if not r.get("parsed"):
            rows.append(f"| {r.get('domain', '?')} | — | — | — | {r.get('error', 'fail')} |")
            continue
        rows.append(
            f"| {r['domain']} | {r.get('dr', '—')} | {r.get('referring_domains', '—')} | "
            f"{r.get('backlinks_total', '—')} | {r.get('referring_urls', '—')} |"
        )

    block = "\n".join(
        [
            "",
            "================================================================================",
            f"9. 백링크 실측 (SmallSEOTools/Semrush, {live.get('generated_at', '')})",
            "================================================================================",
            "",
            "| domain | DR(SST) | RD | backlinks | ref URLs |",
            "|--------|---------|-----|-----------|----------|",
            *rows,
            "",
            "출처: python tools/backlink_live_collect.py --all (2captcha Turnstile)",
            "주의: SST=Semrush 샘플 데이터. Ahrefs DR/RD와 수치가 다를 수 있음.",
            "",
        ]
    )

    text = doc_path.read_text(encoding="utf-8")
    marker = "9. 백링크 실측 (SmallSEOTools"
    if marker in text:
        head = text.split("================================================================================\n9. 백링크 실측")[0].rstrip()
        doc_path.write_text(head + block, encoding="utf-8")
    else:
        doc_path.write_text(text.rstrip() + block, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--merge-audit", action="store_true", help="audit JSON + SERP 비교 문서 갱신")
    args = ap.parse_args()

    ensure_env_file()
    secrets = load_secrets()
    key = secrets.get("TWOCAPTCHA_API_KEY", "")
    if not key:
        raise SystemExit("TWOCAPTCHA_API_KEY not found in local secrets")

    domains = args.domain or (DEFAULT_DOMAINS if args.all else ["gangara.co.kr"])
    results = []
    for i, d in enumerate(domains):
        if i:
            time.sleep(10)
        try:
            row = fetch_smallseotools(d, key)
            results.append(row)
            print(
                d,
                "DR",
                row.get("dr"),
                "RD",
                row.get("referring_domains"),
                "BL",
                row.get("backlinks_total"),
                row.get("error") or "OK",
            )
        except Exception as e:
            results.append({"domain": d, "error": str(e), "source": "smallseotools_semrush"})
            print(d, "ERR", e)

    out_path = Path(args.out) if args.out else TOOLS_DIR / "backlink_live_output.json"
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": "smallseotools+2captcha",
        "results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)

    if args.merge_audit:
        audit_path = TOOLS_DIR / "backlink_audit_output.json"
        merge_into_audit(out_path, audit_path)
        update_comparison_doc(out_path, REPO / "core" / "SERP_VS_GANGARA_COMPARISON.txt")
        print("merged:", audit_path)


if __name__ == "__main__":
    main()
