# -*- coding: utf-8 -*-
"""placements_master → core/backlink_targets_sync.json export."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
PROG = REPO / "website 확장 수집/misc/_program"
if str(PROG) not in sys.path:
    sys.path.insert(0, str(PROG))

from anchor_builder import anchor_for_index, load_money_url  # noqa: E402

MASTER = REPO / "website 확장 수집/misc/data/placements_master.json"
SYNC = REPO / "core/backlink_targets_sync.json"
CONFIG = REPO / "core/machine_config.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_master(new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    master = load_json(MASTER, {"placements": []})
    existing_urls = {p.get("deploy_url") or p.get("url") for p in master.get("placements", [])}
    for row in new_rows:
        url = row.get("deploy_url") or row.get("url")
        if not url or url in existing_urls:
            continue
        if not row.get("qualified"):
            continue
        master.setdefault("placements", []).append(row)
        existing_urls.add(url)
    master["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json(MASTER, master)
    return master.get("placements", [])


def export_sync(pool: list[dict[str, Any]], batch: list[dict[str, Any]]) -> dict[str, Any]:
    cfg = load_json(CONFIG, {})
    campaign_id = cfg.get("campaign_id", "gangara-experiment")
    base_url = load_money_url(campaign_id)
    experiment = cfg.get("experiment_mode", False)

    coverage = Counter()
    for row in batch:
        coverage[row.get("target_keyword", "")] += 1

    table_rows = []
    for i, row in enumerate(batch):
        kw = row.get("target_keyword", "")
        anchor, money_url = anchor_for_index(i, kw, base_url)
        table_rows.append(
            {
                "target_keyword": kw,
                "platform_type": row.get("platform_type", ""),
                "tier_hint": row.get("tier_hint", "B"),
                "deploy_url": row.get("deploy_url") or row.get("url", ""),
                "entry_url": row.get("entry_url") or row.get("url", ""),
                "money_url": money_url,
                "anchor_text": anchor,
                "dofollow_hint": row.get("dofollow_hint", True),
                "write_captcha": row.get("write_captcha", False),
                "signup_captcha": row.get("signup_captcha", False),
                "trait_score": row.get("trait_score", 50),
                "serp_rank": row.get("serp_rank", 99),
            }
        )

    sync = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(table_rows),
        "pool_total": len(pool),
        "campaign_id": campaign_id,
        "money_site": base_url,
        "source": "gangara_experiment" if experiment else "backlink_sync",
        "board_urls": 0,
        "keyword_coverage": dict(coverage),
        "tier_distribution": dict(Counter(r.get("tier_hint", "B") for r in batch)),
        "table_rows": table_rows,
    }
    save_json(SYNC, sync)
    return sync
