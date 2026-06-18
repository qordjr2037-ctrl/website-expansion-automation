# -*- coding: utf-8 -*-
"""placement 적격 판정 — dofollow·captcha hint·trait_score."""
from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from typing import Any

from placement_classifier import classify_url, is_board_url

CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; TrackB-Collector/1.0)"
SPAM_DOMAINS = re.compile(
    r"(news\.|naver\.com/news|daum\.net/v/|postheaven\.net|bcbloggers\.com)",
    re.I,
)
NOFOLLOW_HINT = re.compile(r'rel=["\']nofollow["\']', re.I)
CAPTCHA_HINT = re.compile(r"(recaptcha|hcaptcha|turnstile|captcha)", re.I)
SIGNUP_HINT = re.compile(r"(sign.?up|register|회원가입|가입하기)", re.I)


def _fetch_head(url: str, timeout: int = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            return resp.status, body[:4000]
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2000).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body
    except Exception:
        return 0, ""


def qualify_placement(url: str, target_keyword: str, serp_rank: int = 99) -> dict[str, Any]:
    """Return qualified row or reject dict."""
    cls = classify_url(url)
    if cls["reject"]:
        return {"qualified": False, "reject_reason": cls["reject_reason"], "url": url}

    if SPAM_DOMAINS.search(url) or re.search(r"postheaven\.net|blogspot\.com", url, re.I):
        return {"qualified": False, "reject_reason": "news_spam", "url": url}

    status, snippet = _fetch_head(url)
    dofollow_hint = not bool(NOFOLLOW_HINT.search(snippet))
    write_captcha = bool(CAPTCHA_HINT.search(snippet))
    signup_captcha = write_captcha and bool(SIGNUP_HINT.search(snippet))

    trait = 50
    if cls["platform_type"] == "directory":
        trait += 25
    elif cls["platform_type"] == "guide_hub":
        trait += 20
    elif cls["platform_type"] == "profile":
        trait += 15
    if dofollow_hint:
        trait += 10
    if not write_captcha:
        trait += 10
    if status == 200:
        trait += 5
    if serp_rank <= 10:
        trait += 10
    elif serp_rank <= 20:
        trait += 5
    if target_keyword.lower() in url.lower():
        trait += 5

    if status >= 400 and status != 0:
        trait -= 20

    return {
        "qualified": trait >= 40,
        "url": url,
        "target_keyword": target_keyword,
        "platform_type": cls["platform_type"],
        "tier_hint": cls["tier_hint"],
        "domain": cls["domain"],
        "deploy_url": url,
        "entry_url": url,
        "dofollow_hint": dofollow_hint,
        "write_captcha": write_captcha,
        "signup_captcha": signup_captcha,
        "trait_score": min(100, max(0, trait)),
        "serp_rank": serp_rank,
        "http_status": status,
        "reject_reason": "" if trait >= 40 else "low_trait_score",
    }
