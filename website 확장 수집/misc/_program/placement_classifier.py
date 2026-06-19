# -*- coding: utf-8 -*-
"""URL → platform_type 분류 (게시판 REJECT)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

BOARD_REJECT = re.compile(
    r"(write\.php|/bbs/|bo_table=|wr_id=|/board/|/forum/post|/community/)",
    re.I,
)

PLATFORM_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("directory", re.compile(r"(roompang|directory|업소|listing|register|submit)", re.I)),
    ("guide_hub", re.compile(r"(choicelounge|guide|허브|magazine|pages/)", re.I)),
    ("profile", re.compile(r"(clickn|clicknn|profile|my\.|/user/|/member/)", re.I)),
    ("web2", re.compile(r"(tistory|blog\.naver|velog|medium|postheaven|blogspot)", re.I)),
    ("comment", re.compile(r"(comment|reply|#comment)", re.I)),
    ("forum", re.compile(r"(forum|cafe\.daum|dcinside)", re.I)),
    ("guest_post", re.compile(r"(guest.?post|write-for-us|contribute)", re.I)),
]


def registrable_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        if len(parts) >= 2 and parts[-1] in ("kr", "uk", "jp"):
            return ".".join(parts[-3:]) if len(parts) >= 3 else host
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    except Exception:
        return ""


def is_board_url(url: str) -> bool:
    return bool(BOARD_REJECT.search(url))


def classify_url(url: str) -> dict:
    """Return {platform_type, tier_hint, reject, reject_reason}."""
    if not url or not url.startswith("http"):
        return {"platform_type": "unknown", "tier_hint": "F", "reject": True, "reject_reason": "invalid_url"}

    if is_board_url(url):
        return {
            "platform_type": "forum",
            "tier_hint": "F",
            "reject": True,
            "reject_reason": "board_url",
        }

    platform = "web2"
    tier = "B"
    for ptype, pattern in PLATFORM_RULES:
        if pattern.search(url):
            platform = ptype
            break

    if platform == "directory":
        tier = "S"
    elif platform == "guide_hub":
        tier = "A"
    elif platform == "profile":
        tier = "A"
    elif platform in ("web2", "comment"):
        tier = "B"

    return {
        "platform_type": platform,
        "tier_hint": tier,
        "reject": False,
        "reject_reason": "",
        "domain": registrable_domain(url),
    }
