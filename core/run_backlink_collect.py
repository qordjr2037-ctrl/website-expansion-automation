# -*- coding: utf-8 -*-
"""Track B 백링크 수집 1사이클 — SERP → qualify → master → sync."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROG = REPO / "website 확장 수집/misc/_program"
sys.path.insert(0, str(PROG))

from backlink_pool_rank import pick_keyword_balanced_batch  # noqa: E402
from export_backlink_bridge import export_sync, merge_master  # noqa: E402
from placement_classifier import is_board_url  # noqa: E402
from placement_qualifier import qualify_placement  # noqa: E402
from serp_backlink_collector import collect_keywords  # noqa: E402

STATUS = REPO / "core/backlink_deploy_status.json"
CONFIG = REPO / "core/machine_config.json"
KEYWORDS = REPO / "website 확장 수집/misc/data/backlink_keywords.txt"
LOG = REPO / "website 확장 수집/misc/logs/backlink_collect_live.log"


def load_keywords() -> list[str]:
    lines = []
    for line in KEYWORDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}\n"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line.rstrip())


def update_status(keywords: list[str], sync: dict, exit_code: int) -> None:
    cfg = load_json(CONFIG, {})
    target_kw = cfg.get("target_keywords", 13)
    per_kw = cfg.get("placements_per_keyword", 10)
    urls_refresh = cfg.get("urls_per_refresh", 20)

    coverage = sync.get("keyword_coverage", {})
    kw_ok = sum(1 for k in keywords if coverage.get(k, 0) >= per_kw)
    board_count = sum(
        1 for r in sync.get("table_rows", []) if is_board_url(r.get("deploy_url", ""))
    )

    all_pass = (
        len(keywords) >= target_kw
        and kw_ok >= target_kw
        and sync.get("count", 0) >= urls_refresh
        and sync.get("pool_total", 0) >= target_kw * per_kw
        and board_count == 0
        and exit_code == 0
    )

    status = load_json(STATUS, {})
    status.update(
        {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "current_phase": 2,
            "all_pass": all_pass,
            "gates": {
                "keyword_quota": {
                    "ok": len(keywords) >= target_kw,
                    "current": len(keywords),
                    "target": target_kw,
                    "detail": "backlink_keywords.txt 키워드 수",
                },
                "sync_push": {
                    "ok": sync.get("count", 0) >= urls_refresh,
                    "count": sync.get("count", 0),
                    "pool_total": sync.get("pool_total", 0),
                    "detail": "backlink_targets_sync.json",
                },
                "collect_round": {
                    "ok": exit_code == 0,
                    "exit_code": exit_code,
                    "detail": "run_backlink_collect.py",
                },
            },
            "keyword_coverage": coverage,
            "tier_distribution": sync.get("tier_distribution", {}),
            "board_urls_in_sync": board_count,
            "failures": [] if all_pass else status.get("failures", []),
        }
    )
    if not all_pass:
        failures = []
        if len(keywords) < target_kw:
            failures.append(f"키워드 {len(keywords)}/{target_kw}")
        if sync.get("count", 0) < urls_refresh:
            failures.append(f"sync count {sync.get('count', 0)}/{urls_refresh}")
        if board_count > 0:
            failures.append(f"게시판 URL {board_count}건 — 제거 필요")
        if kw_ok < target_kw:
            failures.append(f"키워드당 queued 부족 ({kw_ok}/{target_kw} 키워드 충족)")
        status["failures"] = failures[:3]
        status["next_actions"] = [
            "키워드 deficit 우선 pick_batch",
            "directory·guide_hub 시드 확대",
            "fusion gangara-hub 호스팅 배포",
        ]
    save_json(STATUS, status)


def run(dry_check: bool = False) -> int:
    keywords = load_keywords()
    cfg = load_json(CONFIG, {})
    batch_size = cfg.get("urls_per_refresh", 20)

    priority = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"]
    collect_kw = priority + [k for k in keywords if k not in priority]

    log(f"collect start keywords={len(keywords)} priority={priority}")

    if dry_check:
        sync = load_json(REPO / "core/backlink_targets_sync.json", {})
        update_status(keywords, sync, 0)
        log("dry-check done")
        return 0

    candidates = collect_keywords(collect_kw)
    log(f"candidates={len(candidates)}")

    qualified = []
    for c in candidates:
        q = qualify_placement(c["url"], c["target_keyword"], c.get("serp_rank", 99))
        if q.get("qualified"):
            q["source"] = c.get("source", "serp")
            qualified.append(q)
    log(f"qualified={len(qualified)}")

    pool = merge_master(qualified)
    batch = pick_keyword_balanced_batch(pool, collect_kw, batch_size)
    sync = export_sync(pool, batch)

    tier_dist = Counter(r.get("tier_hint", "B") for r in batch)
    log(f"sync count={sync['count']} pool_total={sync['pool_total']} tiers={dict(tier_dist)}")

    update_status(keywords, sync, 0)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-check", action="store_true")
    args = parser.parse_args()
    try:
        code = run(dry_check=args.dry_check)
    except Exception as e:
        log(f"ERROR {e}")
        update_status(load_keywords(), load_json(REPO / "core/backlink_targets_sync.json", {}), 1)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
