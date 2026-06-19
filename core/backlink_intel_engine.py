# -*- coding: utf-8 -*-
"""
백링크 인텔 — 원론적 방식 vs 경쟁자 추적.

Track B 코드·감사 데이터·경쟁사 페이지를 분석해 누적 intel 생성.
"""
from __future__ import annotations

import ast
import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
ACCUM = REPO / "tools/BACKLINK_INTEL_ACCUMULATED.json"
AUDIT = REPO / "tools/backlink_audit_output.json"
LIVE = REPO / "tools/backlink_live_output.json"
SERP = REPO / "tools/serp_rank_probe_output.json"

BENCHMARKS = [
    "choicelounge.co.kr",
    "gangnamdalto.co.kr",
    "classicsalong.com",
    "thesevensalon.com",
    "applegangnam.com",
    "gangnammirror.com",
    "gangnamko.co.kr",
    "gangara.co.kr",
]

CODE_FILES = [
    ("serp_backlink_collector", REPO / "website 확장 수집/misc/_program/serp_backlink_collector.py"),
    ("placement_classifier", REPO / "website 확장 수집/misc/_program/placement_classifier.py"),
    ("placement_qualifier", REPO / "website 확장 수집/misc/_program/placement_qualifier.py"),
    ("export_backlink_bridge", REPO / "website 확장 수집/misc/_program/export_backlink_bridge.py"),
    ("backlink_pool_rank", REPO / "website 확장 수집/misc/_program/backlink_pool_rank.py"),
    ("run_backlink_collect", REPO / "core/run_backlink_collect.py"),
    ("run_backlink_auto", REPO / "core/run_backlink_auto.py"),
    ("failure_hypotheses", REPO / "core/failure_hypotheses.py"),
    ("backlink_live_collect", REPO / "tools/backlink_live_collect.py"),
]

CTX = ssl.create_default_context()
UA = "Mozilla/5.0 (compatible; TrackB-Intel/1.0)"
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_accum(data: dict) -> None:
    ACCUM.parent.mkdir(parents=True, exist_ok=True)
    ACCUM.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_accum() -> dict:
    d = load_json(ACCUM, {"cycles": 0, "findings": [], "fundamental": [], "competitor": []})
    d.setdefault("findings", [])
    d.setdefault("fundamental", [])
    d.setdefault("competitor", [])
    return d


# ── A. 원론적 방식 (코드·설계 원리) ─────────────────────────────────────────

FUNDAMENTAL_PRINCIPLES: list[dict[str, str]] = [
    {
        "id": "surface_editable",
        "title": "편집 가능 surface만 placement",
        "theory": "백링크는 '링크를 넣을 수 있는 UI'가 있는 URL만 자산. search 결과·타인 site 열람 URL은 RD에 기여 안 함.",
        "code": "placement_classifier.is_board_url → reject; run_backlink_auto SKIP_URL",
    },
    {
        "id": "platform_tier",
        "title": "platform_type × tier_hint",
        "theory": "directory(S) > guide_hub/profile(A) > web2(B). SERP 1페이지는 roompang directory + 허브 내부링크 패턴.",
        "code": "placement_classifier PLATFORM_RULES; qualifier trait +25 directory",
    },
    {
        "id": "trait_score",
        "title": "trait_score 적격 (dofollow·无captcha·SERP proximity)",
        "theory": "dofollow +10, no captcha +10, SERP top10 URL +10. 40+ qualified, experiment는 70+.",
        "code": "placement_qualifier.qualify_placement()",
    },
    {
        "id": "keyword_balanced_export",
        "title": "키워드 균형 batch export",
        "theory": "3키워드 실험 — 부족한 키워드 placement 우선 sync 30건.",
        "code": "backlink_pool_rank.pick_keyword_balanced_batch()",
    },
    {
        "id": "anchor_diversity",
        "title": "anchor rotation",
        "theory": "money_url 키워드별 landing + anchor_for_index로 앵커 분산.",
        "code": "anchor_builder.anchor_for_index() in export_sync",
    },
    {
        "id": "spam_purge",
        "title": "postheaven/web2 스팸 purge",
        "theory": "RD 숫자만 키우면 안 됨 — 스팸 RD는 SERP 무기여. purge 후 directory/profile.",
        "code": "run_learning_loop.purge_spam_master(); SPAM_DOMAINS",
    },
    {
        "id": "verify_live",
        "title": "live href 검증 = 성공 정의",
        "theory": "queue done ≠ 성공. deploy_url HTML에 money domain href 존재해야 verified.",
        "code": "run_backlink_auto.process_row(); backlink_verified_store",
    },
    {
        "id": "volume_profile_farm",
        "title": "1000/일 = profile farm + web2 (이론)",
        "theory": "ClickN/isweb 3분/건 × 8브라우저 × 2PC ≈ 1000. directory는 볼륨小·품질大.",
        "code": "run_backlink_daily_plan DEFAULT_DAILY_QUOTA",
    },
]


def extract_code_insights() -> list[dict[str, str]]:
    """Python AST로 함수·상수·주석에서 원리 추출."""
    insights: list[dict[str, str]] = []
    for name, path in CODE_FILES:
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        doc = ast.get_docstring(ast.parse(src)) or ""
        funcs = [n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)][:8]
        rules = []
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("#") and len(s) > 10 and "noqa" not in s:
                rules.append(s.lstrip("# ").strip())
            if "reject" in s.lower() or "REJECT" in s or "SPAM" in s:
                rules.append(s[:100])
        if doc or funcs:
            insights.append(
                {
                    "module": name,
                    "doc_first_line": doc.splitlines()[0][:200] if doc else "",
                    "key_functions": ", ".join(funcs),
                    "rules_sample": "; ".join(rules[:4]),
                }
            )
    return insights


def fundamental_section() -> dict[str, Any]:
    code_insights = extract_code_insights()
    return {
        "principles": FUNDAMENTAL_PRINCIPLES,
        "code_modules": code_insights,
        "track_b_pipeline": [
            "SERP+seed → classify(reject board) → qualify(trait) → placements_master",
            "→ pick_keyword_balanced_batch → backlink_targets_sync → deploy_queue",
            "→ auto verify / Browser deploy → verified_store → milestone 100",
        ],
    }


# ── B. 경쟁자 추적 ───────────────────────────────────────────────────────────

def fetch_page(url: str, timeout: int = 12) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.read(100000).decode("utf-8", errors="replace")
    except Exception:
        return ""


def classify_link(url: str) -> str:
    u = url.lower()
    if "roompang" in u:
        return "directory"
    if "clickn" in u or "isweb" in u:
        return "profile"
    if "tistory" in u or "velog" in u or "blog.naver" in u:
        return "web2"
    if "postheaven" in u or "blogspot" in u or "bcbloggers" in u:
        return "web2_spam"
    if u.startswith("/") or "#" in u:
        return "internal"
    return "external_other"


def scrape_competitor(domain: str) -> dict[str, Any]:
    base = f"https://{domain}/"
    html = fetch_page(base)
    hrefs = HREF_RE.findall(html)
    internal: dict[str, int] = {}
    external: dict[str, int] = {}
    ext_types: dict[str, int] = {}
    for h in hrefs:
        if domain in h or h.startswith("/"):
            internal[h[:80]] = internal.get(h[:80], 0) + 1
        else:
            t = classify_link(h)
            ext_types[t] = ext_types.get(t, 0) + 1
            if t not in ("internal",):
                external[h[:100]] = external.get(h[:100], 0) + 1

    internal_links = len([h for h in hrefs if h.startswith("/") or domain in h])
    return {
        "domain": domain,
        "fetched": bool(html),
        "page_bytes": len(html),
        "total_hrefs": len(hrefs),
        "internal_link_count": internal_links,
        "external_by_type": ext_types,
        "sample_external": list(external.keys())[:8],
    }


def competitor_audit_row(domain: str) -> dict[str, Any]:
    audit = load_json(AUDIT, {})
    for r in audit.get("reports") or []:
        if r.get("domain") == domain:
            return {
                "domain": domain,
                "dr": r.get("sst_dr"),
                "rd": r.get("sst_referring_domains"),
                "backlinks": r.get("sst_backlinks_total"),
                "known_citations": r.get("known_citations") or [],
                "sample_backlinks": (r.get("sst_sample_backlinks") or [])[:3],
            }
    return {"domain": domain}


def competitor_section() -> dict[str, Any]:
    profiles = []
    for d in BENCHMARKS:
        audit_row = competitor_audit_row(d)
        scrape = scrape_competitor(d)
        profiles.append({**audit_row, **scrape})

    # SERP top URLs per keyword (경쟁 노출 surface)
    serp = load_json(SERP, {})
    serp_surfaces = []
    for r in serp.get("results") or []:
        serp_surfaces.append(
            {
                "keyword": r.get("keyword"),
                "gangara_rank": r.get("rank"),
                "top5_domains": [
                    re.sub(r"^https?://([^/]+).*", r"\1", u)
                    for u in (r.get("sample_urls") or [])[:5]
                ],
            }
        )

    # 경쟁자 패턴 요약 (SERP_VS 문서 + 실측)
    patterns = [
        {
            "competitor": "gangnamdalto.co.kr",
            "rd": 556,
            "pattern": "single_landing + roompang directory + sibling_domain 상호링크",
            "actionable": "roompang 업소등록 + .co.kr 형제도메인 네트워크 (장기)",
        },
        {
            "competitor": "choicelounge.co.kr",
            "rd": 101,
            "pattern": "guide_hub 8매장 카드 → 내부 PageRank 24+ 하부 URL",
            "actionable": "gangara fusion 허브 내부링크 5 URL (이미 live) + 외부 citation",
        },
        {
            "competitor": "thesevensalon.com",
            "rd": 93,
            "pattern": "중위 RD — directory+profile mix",
            "actionable": "RD 98 중위 목표 — profile bulk로 수량, roompang으로 품질",
        },
        {
            "competitor": "gangara.co.kr",
            "rd": 46,
            "pattern": "postheaven 스팸 RD 100% — SERP 0/3",
            "actionable": "스팸 purge + live citation 100건 milestone",
        },
    ]

    return {
        "profiles": profiles,
        "serp_surfaces": serp_surfaces,
        "pattern_summary": patterns,
        "gap_vs_gangara": _gap_analysis(profiles),
    }


def _gap_analysis(profiles: list[dict]) -> list[str]:
    you = next((p for p in profiles if p.get("domain") == "gangara.co.kr"), {})
    gaps = []
    your_rd = you.get("rd") or 46
    for p in profiles:
        if p.get("domain") == "gangara.co.kr":
            continue
        rd = p.get("rd")
        if rd and rd > your_rd:
            gaps.append(f"{p['domain']} RD {rd} vs gangara {your_rd} (+{rd - your_rd})")
    return gaps[:6]


def new_findings_this_cycle(fund: dict, comp: dict, cycle: int) -> list[dict]:
    """사이클마다 새 intel 조각 (중복 최소)."""
    findings = []
    for p in comp.get("profiles") or []:
        if p.get("fetched") and p.get("external_by_type"):
            findings.append(
                {
                    "cycle": cycle,
                    "type": "competitor_scrape",
                    "domain": p["domain"],
                    "text": f"{p['domain']} 외부링크 유형: {p.get('external_by_type')}",
                }
            )
    for pr in FUNDAMENTAL_PRINCIPLES[:2]:
        findings.append(
            {
                "cycle": cycle,
                "type": "fundamental",
                "id": pr["id"],
                "text": f"[원론] {pr['title']}: {pr['theory'][:120]}",
            }
        )
    for pat in comp.get("pattern_summary") or []:
        if pat["competitor"] != "gangara.co.kr":
            findings.append(
                {
                    "cycle": cycle,
                    "type": "competitor_pattern",
                    "domain": pat["competitor"],
                    "text": f"[경쟁] {pat['pattern']} → gangara: {pat['actionable']}",
                }
            )
    return findings


def run_intel_cycle() -> dict[str, Any]:
    accum = load_accum()
    cycle = int(accum.get("cycles") or 0) + 1

    fund = fundamental_section()
    comp = competitor_section()
    findings = new_findings_this_cycle(fund, comp, cycle)

    # 누적 (최근 200 findings)
    all_findings = (accum.get("findings") or []) + findings
    if len(all_findings) > 200:
        all_findings = all_findings[-200:]

    report = {
        "generated_at": now_iso(),
        "cycle": cycle,
        "fundamental": fund,
        "competitor": comp,
        "new_findings": findings,
        "stop_note": "중지: tools/BACKLINK_INTEL_STOP 파일 생성 또는 backlink_intel.enabled=false",
    }

    accum.update(
        {
            "cycles": cycle,
            "updated_at": now_iso(),
            "findings": all_findings,
            "last_report": report,
        }
    )
    save_accum(accum)
    return report


def render_intel_markdown(r: dict) -> str:
    comp = r.get("competitor") or {}
    fund = r.get("fundamental") or {}
    new = r.get("new_findings") or []

    lines = [
        f"# 백링크 인텔 보고 — cycle {r.get('cycle')} ({r.get('generated_at')})",
        "",
        "> **A. 원론적 방식** (SEO·Track B 코드 원리) | **B. 경쟁자 추적** (SERP·RD·페이지 분석)",
        "",
        "---",
        "",
        "## A. 원론적 방식 (백링크 올리는 원리)",
        "",
        "### Track B 파이프라인",
    ]
    for step in fund.get("track_b_pipeline") or []:
        lines.append(f"- {step}")

    lines.append("\n### 핵심 원칙\n")
    for p in fund.get("principles") or []:
        lines.append(f"**{p['title']}**")
        lines.append(f"- 이론: {p['theory']}")
        lines.append(f"- 코드: `{p['code']}`\n")

    lines.append("### 코드 모듈 (이번 스캔)\n")
    lines.append("| 모듈 | doc | 핵심 함수 |")
    lines.append("|------|-----|-----------|")
    for m in fund.get("code_modules") or []:
        lines.append(
            f"| {m.get('module')} | {m.get('doc_first_line','')[:40]} | {m.get('key_functions','')[:30]} |"
        )

    lines += ["", "---", "", "## B. 경쟁자 추적", ""]

    lines.append("### RD·백링크 실측 + 홈페이지 링크 구조\n")
    lines.append("| domain | RD | BL | internal | external types |")
    lines.append("|--------|-----|-----|----------|----------------|")
    for p in comp.get("profiles") or []:
        ext = p.get("external_by_type") or {}
        lines.append(
            f"| {p.get('domain')} | {p.get('rd','?')} | {p.get('backlinks','?')} | "
            f"{p.get('internal_link_count','?')} | {ext} |"
        )

    lines.append("\n### SERP top5 surface (키워드별)\n")
    for s in comp.get("serp_surfaces") or []:
        lines.append(f"- **{s.get('keyword')}** gangara={s.get('gangara_rank') or '미노출'} → top: {s.get('top5_domains')}")

    lines.append("\n### 경쟁 패턴 → gangara 적용\n")
    for pat in comp.get("pattern_summary") or []:
        lines.append(f"- **{pat['competitor']}** ({pat.get('pattern')})")
        lines.append(f"  → {pat.get('actionable')}")

    lines.append("\n### gangara 격차\n")
    for g in comp.get("gap_vs_gangara") or []:
        lines.append(f"- {g}")

    lines += ["", "---", "", "## 이번 cycle 신규 intel\n"]
    for f in new:
        lines.append(f"- {f.get('text')}")

    lines += [
        "",
        "---",
        f"누적 cycle: {r.get('cycle')} | 중지: `touch tools/BACKLINK_INTEL_STOP`",
        "누적 파일: `tools/BACKLINK_INTEL_ACCUMULATED.json`",
    ]
    return "\n".join(lines) + "\n"
