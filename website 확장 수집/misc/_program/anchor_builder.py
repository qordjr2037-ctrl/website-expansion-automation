# -*- coding: utf-8 -*-
"""앵커 텍스트 생성 — exact 40 / partial 30 / brand 20 / naked 10."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ANCHOR_PLAN = REPO / "website 확장 수집/misc/data/anchor_plan.json"
MONEY_SITES = REPO / "website 확장 수집/misc/data/money_sites.json"

BRAND = "강남가라"
LANDING_MAP = {
    "강남 가라오케": "/gangnam-garaoke.html",
    "강남 풀싸롱": "/gangnam-poolsalon.html",
    "강남 하이퍼블릭": "/gangnam-hyperbolic.html",
    "강남 쩜오": "/gangnam-jjom.html",
}


def load_money_url(campaign_id: str = "gangara-experiment") -> str:
    data = json.loads(MONEY_SITES.read_text(encoding="utf-8"))
    for c in data.get("campaigns", []):
        if c.get("id") == campaign_id and c.get("enabled"):
            return c.get("money_url", "https://gangara.co.kr/")
    for c in data.get("campaigns", []):
        if c.get("enabled"):
            return c.get("money_url", "https://gangara.co.kr/")
    return "https://gangara.co.kr/"


def landing_url(keyword: str, base: str | None = None) -> str:
    base = (base or load_money_url()).rstrip("/")
    path = LANDING_MAP.get(keyword, "/")
    return f"{base}{path}"


def anchor_for_index(index: int, keyword: str, base: str | None = None) -> tuple[str, str]:
    """Return (anchor_text, money_url). Cycle: exact→partial→brand→naked."""
    url = landing_url(keyword, base)
    slot = index % 10
    if slot < 4:
        return keyword, url
    if slot < 7:
        return f"{keyword} 가이드", url
    if slot < 9:
        return BRAND, url
    return "gangara.co.kr", f"{base or load_money_url()}/"
