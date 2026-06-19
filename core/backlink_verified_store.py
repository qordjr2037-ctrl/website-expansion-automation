# -*- coding: utf-8 -*-
"""백링크 live 성공 추적 + 100건 milestone."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STORE_PATH = REPO / "core/backlink_verified_store.json"
CONFIG = REPO / "core/machine_config.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_store() -> dict:
    return {
        "updated_at": None,
        "success_total": 0,
        "failed_total": 0,
        "last_milestone_reported": 0,
        "milestone_step": 100,
        "successes": [],
        "failures": [],
    }


def load_store() -> dict:
    if not STORE_PATH.exists():
        return _default_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        for k, v in _default_store().items():
            data.setdefault(k, v)
        return data
    except Exception:
        return _default_store()


def save_store(data: dict) -> None:
    data["updated_at"] = now_iso()
    data["success_total"] = len(data.get("successes") or [])
    data["failed_total"] = len(data.get("failures") or [])
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def milestone_step() -> int:
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        vol = cfg.get("backlink_volume") or {}
        return int(vol.get("success_milestone", 100))
    return 100


def url_already_success(store: dict, deploy_url: str) -> bool:
    return any(s.get("deploy_url") == deploy_url for s in store.get("successes") or [])


def record_success(store: dict, row: dict, *, verified_url: str | None = None) -> dict:
    url = row.get("deploy_url") or row.get("url", "")
    if url_already_success(store, url):
        return store
    store.setdefault("successes", []).append(
        {
            "at": now_iso(),
            "deploy_url": url,
            "money_url": row.get("money_url"),
            "anchor_text": row.get("anchor_text"),
            "platform_type": row.get("platform_type"),
            "target_keyword": row.get("target_keyword"),
            "verified_url": verified_url or url,
        }
    )
    save_store(store)
    return store


def record_failure(store: dict, row: dict, failure_code: str, reason: str) -> dict:
    from failure_hypotheses import get_next_hypothesis

    hyp = get_next_hypothesis(failure_code)
    store.setdefault("failures", []).append(
        {
            "at": now_iso(),
            "deploy_url": row.get("deploy_url"),
            "platform_type": row.get("platform_type"),
            "failure_code": failure_code,
            "reason": reason[:200],
            "next_hypothesis_id": hyp.get("next_hypothesis_id"),
            "next_hypothesis_ko": hyp.get("next_hypothesis_ko"),
        }
    )
    # 최근 500건만 유지
    if len(store["failures"]) > 500:
        store["failures"] = store["failures"][-500:]
    save_store(store)
    return store


def success_count(store: dict | None = None) -> int:
    s = store or load_store()
    return len(s.get("successes") or [])


def pending_milestone(store: dict | None = None) -> int | None:
    """다음 보고 milestone (100, 200, …). 도달 시 int, 아니면 None."""
    s = store or load_store()
    total = success_count(s)
    step = int(s.get("milestone_step") or milestone_step())
    last = int(s.get("last_milestone_reported") or 0)
    current_milestone = (total // step) * step
    if current_milestone > last and total >= step:
        return current_milestone
    return None


def mark_milestone_reported(store: dict, milestone: int) -> dict:
    store["last_milestone_reported"] = milestone
    store["milestone_step"] = milestone_step()
    save_store(store)
    return store


def stats_by_platform(store: dict | None = None) -> dict[str, int]:
    s = store or load_store()
    out: dict[str, int] = {}
    for row in s.get("successes") or []:
        pt = row.get("platform_type") or "unknown"
        out[pt] = out.get(pt, 0) + 1
    return out
