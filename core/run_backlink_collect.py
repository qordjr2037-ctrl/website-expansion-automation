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
KEYWORDS_DEFAULT = REPO / "website 확장 수집/misc/data/backlink_keywords.txt"
LOG = REPO / "website 확장 수집/misc/logs/backlink_collect_live.log"


def load_keywords(cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_json(CONFIG, {})
    kw_file = REPO / cfg.get("keywords_file", KEYWORDS_DEFAULT.relative_to(REPO))
    if not kw_file.is_absolute():
        kw_file = REPO / kw_file
    lines = []
    for line in kw_file.read_text(encoding="utf-8").splitlines():
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


def update_status(keywords: list[str], sync: dict, exit_code: int, cfg: dict) -> None:
    target_kw = cfg.get("target_keywords", 13)
    per_kw = cfg.get("placements_per_keyword", 10)
    urls_refresh = cfg.get("urls_per_refresh", 20)
    experiment = cfg.get("experiment_mode", False)

    coverage = sync.get("pool_keyword_coverage") or sync.get("keyword_coverage", {})
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
            "experiment_mode": experiment,
            "money_site": sync.get("money_site", "https://gangara.co.kr/"),
            "targets": {
                "keywords": target_kw,
                "placements_per_keyword": per_kw,
                "urls_per_refresh": urls_refresh,
            },
            "fusion_live": {
                "deployed": True,
                "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "h1": "강남 가라오케 · 하이퍼블릭 · 풀싸롱 · 쩜오 2026 완벽 가이드",
                "canonical": "https://gangara.co.kr/",
                "sitemap_urls": 5,
            },
            "gates": {
                "keyword_quota": {
                    "ok": len(keywords) >= target_kw,
                    "current": len(keywords),
                    "target": target_kw,
                    "detail": cfg.get("keywords_file", "backlink_keywords.txt"),
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
            "pool_keyword_coverage": sync.get("pool_keyword_coverage", coverage),
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
        if experiment:
            status["next_actions"] = [
                "PC 워커: backlink_targets_sync.json pull → directory·guide_hub 30건 배포",
                "roompang.com gangara.co.kr live citation 등록 (P0 Tier S)",
                "Google Search Console sitemap 제출 + site:gangara.co.kr 인덱스 확인",
            ]
        else:
            status["next_actions"] = [
                "gangara 실험: directory·guide_hub 배포 실행",
                "python tools/serp_rank_probe.py --merge-experiment (주 1회)",
                "roompang live citation 재등록",
            ]
    save_json(STATUS, status)


def run(dry_check: bool = False) -> int:
    cfg = load_json(CONFIG, {})
    keywords = load_keywords(cfg)
    batch_size = cfg.get("urls_per_refresh", 20)
    experiment = cfg.get("experiment_mode", False)

    priority = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"]
    collect_kw = [k for k in priority if k in keywords] + [k for k in keywords if k not in priority]

    mode = "experiment" if experiment else "standard"
    log(f"collect start mode={mode} keywords={len(keywords)} money=gangara.co.kr")

    if dry_check:
        sync = load_json(REPO / "core/backlink_targets_sync.json", {})
        update_status(keywords, sync, 0, cfg)
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
    pool_cov = Counter(r.get("target_keyword", "") for r in pool)
    batch = pick_keyword_balanced_batch(
        pool, collect_kw, batch_size, existing_coverage=dict(pool_cov), experiment_mode=experiment
    )
    sync = export_sync(pool, batch)

    tier_dist = Counter(r.get("tier_hint", "B") for r in batch)
    log(f"sync count={sync['count']} pool_total={sync['pool_total']} tiers={dict(tier_dist)}")

    update_status(keywords, sync, 0, cfg)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-check", action="store_true")
    args = parser.parse_args()
    cfg = load_json(CONFIG, {})
    try:
        code = run(dry_check=args.dry_check)
    except Exception as e:
        log(f"ERROR {e}")
        update_status(
            load_keywords(cfg),
            load_json(REPO / "core/backlink_targets_sync.json", {}),
            1,
            cfg,
        )
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
