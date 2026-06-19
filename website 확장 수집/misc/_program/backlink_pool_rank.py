# -*- coding: utf-8 -*-
"""placement 풀 랭킹 — experiment 모드: S/A directory·guide_hub 우선."""
from __future__ import annotations

from collections import Counter
from typing import Any

EXPERIMENT_PLATFORMS = {"directory", "guide_hub", "profile"}
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "F": 3}


def pick_keyword_balanced_batch(
    pool: list[dict[str, Any]],
    keywords: list[str],
    batch_size: int,
    existing_coverage: dict[str, int] | None = None,
    experiment_mode: bool = False,
    min_trait: int = 40,
) -> list[dict[str, Any]]:
    coverage = Counter(existing_coverage or {})
    for kw in keywords:
        coverage.setdefault(kw, 0)

    def sort_key(row: dict[str, Any]) -> tuple:
        kw = row.get("target_keyword", "")
        deficit = -coverage.get(kw, 0)
        ptype = row.get("platform_type", "")
        platform_penalty = 0
        if experiment_mode:
            platform_penalty = 0 if ptype in EXPERIMENT_PLATFORMS else 5
        dofollow = 0 if row.get("dofollow_hint") else 1
        captcha = 1 if row.get("write_captcha") else 0
        rank = row.get("serp_rank", 99)
        trait = -row.get("trait_score", 0)
        tier = TIER_ORDER.get(row.get("tier_hint", "B"), 2)
        return (platform_penalty, tier, deficit, dofollow, captcha, rank, trait)

    active = [r for r in pool if r.get("qualified", True) and r.get("trait_score", 0) >= min_trait]
    if experiment_mode:
        preferred = [r for r in active if r.get("platform_type") in EXPERIMENT_PLATFORMS]
        if len(preferred) >= batch_size // 2:
            active = preferred + [r for r in active if r not in preferred]
    active.sort(key=sort_key)

    picked: list[dict[str, Any]] = []
    picked_urls: set[str] = set()
    for row in active:
        if len(picked) >= batch_size:
            break
        url = row.get("deploy_url") or row.get("url", "")
        if url in picked_urls:
            continue
        picked_urls.add(url)
        picked.append(row)
        kw = row.get("target_keyword", "")
        coverage[kw] += 1

    return picked
