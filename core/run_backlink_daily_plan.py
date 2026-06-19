#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
일일 백링크 실행 플랜 생성 (기본 1000건/일).

  python3 core/run_backlink_daily_plan.py
  python3 core/run_backlink_daily_plan.py --target 1000 --email
  python3 core/run_backlink_prepare.py --machine-id 1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "core/machine_config.json"
MASTER = REPO / "website 확장 수집/misc/data/placements_master.json"
SYNC = REPO / "core/backlink_targets_sync.json"
PLAN_JSON = REPO / "core/backlink_daily_plan.json"
EXEC_JSON = REPO / "tools/BACKLINK_EXECUTE_TODAY.json"
EXEC_MD = REPO / "tools/BACKLINK_EXECUTE_TODAY.md"
PLAYBOOK = REPO / "core/BACKLINK_1000_DAY_PLAYBOOK.md"

# 1000/일 — 플랫폼별 일일 할당 (실행 난이도·속도 기준)
DEFAULT_DAILY_QUOTA: dict[str, int] = {
    "profile": 450,
    "web2": 350,
    "directory": 80,
    "guide_hub": 40,
    "comment": 80,
}

PLATFORM_HOWTO: dict[str, dict] = {
    "profile": {
        "title": "ClickN / isweb 프로필·무료 사이트",
        "steps": [
            "1) https://www.clickn.co.kr/ 회원가입 (또는 isweb.co.kr)",
            "2) 「무료 홈페이지 만들기」→ 서브도메인 생성 (예: gangnam-gara-{n}.clickn.co.kr)",
            "3) 페이지 편집 → 소개/푸터/연락처에 `<a href=\"{money_url}\">{anchor}</a>` 삽입",
            "4) 저장 → deploy_url에서 gangara.co.kr href live 확인",
            "5) verified_store에 done 기록",
        ],
        "minutes_per_link": 3,
        "automation": "Playwright: signup → site wizard → footer HTML paste (Phase 3)",
        "signup_urls": ["https://www.clickn.co.kr/", "https://www.isweb.co.kr/"],
    },
    "web2": {
        "title": "티스토리·Velog·네이버 블로그 글",
        "steps": [
            "1) 플랫폼 회원가입 (tistory.com / velog.io / blog.naver.com)",
            "2) 새 글 작성 — 제목에 키워드, 본문 300자+ 가이드 요약",
            "3) 본문 중 `{anchor}` → `{money_url}` dofollow 링크 1~2개",
            "4) 발행 → deploy_url(글 URL)에서 href 확인",
        ],
        "minutes_per_link": 5,
        "automation": "Playwright post editor + 2captcha (Phase 3)",
        "signup_urls": ["https://www.tistory.com/", "https://velog.io/", "https://section.blog.naver.com/"],
    },
    "directory": {
        "title": "roompang 등 디렉터리 업소등록",
        "steps": [
            "1) https://www.roompang.com/ 로그인",
            "2) 업소등록 / 가이드 편집 UI (search URL은 등록폼 아님 — /guide/ 또는 홈 등록)",
            "3) 업소명·소개·공식 URL에 money_url + anchor",
            "4) 저장 후 페이지에서 gangara href 확인",
        ],
        "minutes_per_link": 8,
        "automation": "Browser 수동 P0 — 자동화 전 Tier S 17건 먼저",
        "signup_urls": ["https://www.roompang.com/"],
    },
    "guide_hub": {
        "title": "경쟁 guide_hub (편집 가능한 것만)",
        "steps": [
            "1) deploy_url 열기 — 본인 소유·편집 권한 있는 site만",
            "2) choicelounge/clicknn 등 **타인 사이트 편집 불가** → skip",
            "3) 본인 ClickN·isweb guide 페이지는 profile과 동일 처리",
        ],
        "minutes_per_link": 10,
        "automation": "대부분 skip — pool에서 editable_only 필터",
        "signup_urls": [],
    },
    "comment": {
        "title": "댓글·QA (nofollow 허용, 볼륨용)",
        "steps": [
            "1) ntiming.co.kr/article 등 QA·댓글 가능 URL",
            "2) 키워드 관련 2~3문장 + money_url (nofollow OK)",
            "3) 스팸 필터 회피 — 키워드별 1회/도메인",
        ],
        "minutes_per_link": 4,
        "automation": "Playwright comment form (Phase 3)",
        "signup_urls": [],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_pool() -> list[dict]:
    master = load_json(MASTER, {"placements": []})
    rows = list(master.get("placements") or [])
    sync = load_json(SYNC, {})
    sync_urls = {r.get("deploy_url") for r in sync.get("table_rows") or []}
    for r in rows:
        r.setdefault("in_sync", r.get("deploy_url") in sync_urls)
    return rows


def pick_daily_rows(pool: list[dict], quota: dict[str, int]) -> list[dict]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in pool:
        pt = row.get("platform_type", "web2")
        by_type[pt].append(row)

    for pt in by_type:
        by_type[pt].sort(key=lambda r: (-(r.get("trait_score") or 0), r.get("deploy_url", "")))

    picked: list[dict] = []
    for pt, limit in quota.items():
        for row in by_type.get(pt, [])[:limit]:
            picked.append(
                {
                    "target_keyword": row.get("target_keyword", ""),
                    "platform_type": pt,
                    "tier_hint": row.get("tier_hint", "B"),
                    "deploy_url": row.get("deploy_url") or row.get("url", ""),
                    "money_url": row.get("money_url", "https://gangara.co.kr/"),
                    "anchor_text": row.get("anchor_text", "gangara.co.kr"),
                    "trait_score": row.get("trait_score"),
                    "dofollow_hint": row.get("dofollow_hint"),
                    "write_captcha": row.get("write_captcha"),
                    "status": "queued",
                    "action": _action_for_row(row),
                }
            )

    # pool 부족 시 신규 생성 슬롯 (ClickN/isweb/tistory 신규 가입)
    deficit = sum(quota.values()) - len(picked)
    if deficit > 0:
        for i in range(deficit):
            kw_idx = i % 3
            kw = ["강남 가라오케", "강남 풀싸롱", "강남 하이퍼블릭"][kw_idx]
            money = [
                "https://gangara.co.kr/gangnam-garaoke.html",
                "https://gangara.co.kr/gangnam-poolsalon.html",
                "https://gangara.co.kr/gangnam-hyperbolic.html",
            ][kw_idx]
            anchor = kw if kw != "강남 하이퍼블릭" else "강남 하이퍼블릭 가이드"
            pt = "profile" if i % 2 == 0 else "web2"
            picked.append(
                {
                    "target_keyword": kw,
                    "platform_type": pt,
                    "tier_hint": "A" if pt == "profile" else "B",
                    "deploy_url": f"NEW_SIGNUP:{pt}:{i + 1}",
                    "money_url": money,
                    "anchor_text": anchor,
                    "trait_score": None,
                    "status": "new_signup",
                    "action": PLATFORM_HOWTO[pt]["title"] + " — 신규 계정·사이트 생성",
                }
            )
    return picked


def _action_for_row(row: dict) -> str:
    pt = row.get("platform_type", "web2")
    if "roompang.com/search" in (row.get("deploy_url") or ""):
        return "SKIP 또는 roompang 업소등록폼으로 대체 (search URL은 편집 불가)"
    if pt in ("guide_hub",) and "choicelounge" in (row.get("deploy_url") or ""):
        return "SKIP — 타인 guide_hub 편집 불가 (본인 ClickN/isweb만)"
    return PLATFORM_HOWTO.get(pt, {}).get("title", pt)


def fleet_plan(total: int, machines: int, browsers: int) -> dict:
    per_machine = total // max(1, machines)
    per_browser = per_machine // max(1, browsers)
    hours = 8
    links_per_hour_browser = max(1, per_browser // hours)
    return {
        "machines": machines,
        "browsers_per_machine": browsers,
        "total_workers": machines * browsers,
        "links_per_machine": per_machine,
        "links_per_browser_day": per_browser,
        "links_per_browser_hour": links_per_hour_browser,
        "shift_hours": hours,
    }


def render_markdown(plan: dict) -> str:
    quota = plan["daily_quota"]
    fleet = plan["fleet"]
    pool_stats = plan["pool_stats"]
    rows = plan["rows"]
    by_type = Counter(r["platform_type"] for r in rows)

    howto_blocks = []
    for pt, meta in PLATFORM_HOWTO.items():
        steps = "\n".join(f"   {s}" for s in meta["steps"])
        howto_blocks.append(
            f"### {pt} — {meta['title']}\n"
            f"- 소요: ~{meta['minutes_per_link']}분/건\n"
            f"- 자동화: {meta['automation']}\n"
            f"{steps}\n"
        )

    sample_rows = "\n".join(
        f"| {i + 1} | {r['platform_type']} | {r['target_keyword']} | {r['deploy_url'][:50]} | {r['status']} |"
        for i, r in enumerate(rows[:25])
    )

    return f"""# gangara 백링크 1000/일 — 오늘 실행 플랜

생성: {plan['generated_at']} | 목표: **{plan['daily_target']}건/일**

---

## 1. 오늘 숫자

| 항목 | 값 |
|------|-----|
| pool 총 placement | {pool_stats['pool_total']} |
| 오늘 배정 | {len(rows)}건 |
| platform 분포 | {dict(by_type)} |
| fleet | {fleet['machines']}대 × {fleet['browsers_per_machine']}브라우저 = {fleet['total_workers']} workers |
| 브라우저당/일 | ~{fleet['links_per_browser_day']}건 ({fleet['shift_hours']}h 근무 기준) |

---

## 2. 플랫폼별 일일 할당

| platform | 목표/일 | pool 보유 | 실행 방법 |
|----------|---------|-----------|-----------|
| profile (ClickN·isweb) | {quota.get('profile', 0)} | {pool_stats['by_type'].get('profile', 0)} | 무료 사이트 생성 → footer 링크 |
| web2 (tistory·velog·naver) | {quota.get('web2', 0)} | {pool_stats['by_type'].get('web2', 0)} | 새 글 + dofollow 링크 |
| directory (roompang) | {quota.get('directory', 0)} | {pool_stats['by_type'].get('directory', 0)} | 업소등록 (search URL 제외) |
| guide_hub | {quota.get('guide_hub', 0)} | {pool_stats['by_type'].get('guide_hub', 0)} | 편집 가능한 것만 |
| comment/QA | {quota.get('comment', 0)} | {pool_stats['by_type'].get('comment', 0)} | 댓글 (볼륨·nofollow OK) |

---

## 3. 바로 실행 (PC Cursor Browser)

```bash
git pull origin cursor/gangara-faeb
python3 core/run_backlink_prepare.py --machine-id 1
# → core/backlink_deploy_queue_machine1.json 생성
```

Browser 프롬프트: `tools/CURSOR_BROWSER_DAILY_1000_PROMPT.md` 전체 복사

**P0 오늘 (기존 큐 17건):** roompang 업소등록 + choicelounge skip  
**P1 bulk (983건):** ClickN 신규 사이트 → profile 링크 반복

---

## 4. 플랫폼별 실행 절차

{"".join(howto_blocks)}

---

## 5. 오늘 배정 샘플 (상위 25건)

| # | type | keyword | deploy_url | status |
|---|------|---------|------------|--------|
{sample_rows}

… 전체 {len(rows)}건 → `tools/BACKLINK_EXECUTE_TODAY.json`

---

## 6. 명령어

```bash
# 수집 (pool 확장)
python3 core/run_backlink_collect.py

# 일일 플랜 재생성
python3 core/run_backlink_daily_plan.py --target 1000

# PC N번 머신 큐
python3 core/run_backlink_prepare.py --machine-id 1

# 배포 후 검증 (Phase 3)
python3 core/run_backlink_verify.py --today
```

상세: `core/BACKLINK_1000_DAY_PLAYBOOK.md`
"""


def build_plan(target: int) -> dict:
    cfg = load_json(CONFIG, {})
    vol = cfg.get("backlink_volume") or {}
    quota = dict(vol.get("daily_quota") or DEFAULT_DAILY_QUOTA)
    # scale quota to target
    base_sum = sum(quota.values()) or 1000
    if base_sum != target:
        scale = target / base_sum
        quota = {k: max(1, int(v * scale)) for k, v in quota.items()}
        diff = target - sum(quota.values())
        if diff:
            quota["profile"] = quota.get("profile", 0) + diff

    pool = load_pool()
    by_type = Counter(r.get("platform_type", "web2") for r in pool)
    rows = pick_daily_rows(pool, quota)

    machines = int(cfg.get("machines_in_fleet", 1))
    browsers = int(cfg.get("browsers_per_machine", 8))

    plan = {
        "generated_at": now_iso(),
        "daily_target": target,
        "daily_quota": quota,
        "pool_stats": {"pool_total": len(pool), "by_type": dict(by_type)},
        "fleet": fleet_plan(len(rows), machines, browsers),
        "rows": rows,
        "count": len(rows),
        "money_site": "https://gangara.co.kr/",
        "executable": True,
        "playbook": str(PLAYBOOK.relative_to(REPO)),
        "browser_prompt": "tools/CURSOR_BROWSER_DAILY_1000_PROMPT.md",
    }
    return plan


def main() -> int:
    ap = argparse.ArgumentParser(description="일일 백링크 1000 실행 플랜")
    ap.add_argument("--target", type=int, default=1000, help="일일 목표 건수")
    ap.add_argument("--email", action="store_true", help="완료 후 Gmail 보고")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    plan = build_plan(args.target)
    md = render_markdown(plan)

    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EXEC_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EXEC_MD.write_text(md, encoding="utf-8")

    if not args.quiet:
        print(md)

    if args.email:
        sys.path.insert(0, str(REPO / "core"))
        from run_learning_report import send_email  # noqa: WPS433

        subj = f"[gangara 백링크] 1000/일 실행 플랜 — pool {plan['pool_stats']['pool_total']} · 배정 {plan['count']}건"
        send_email(subj, md, plan)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
