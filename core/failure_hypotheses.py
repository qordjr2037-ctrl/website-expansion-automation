# -*- coding: utf-8 -*-
"""실패 유형 → 다음 실험 가설 (자동 학습·보고용)."""
from __future__ import annotations

from typing import Any

# failure_code → 실패 설명 + 다음 가설 + 즉시 실행 액션
FAILURE_NEXT_HYPOTHESES: dict[str, dict[str, Any]] = {
    "not_editable": {
        "failure_ko": "deploy_url에 편집 UI 없음 (roompang search?q=, 타인 guide_hub 등)",
        "next_hypothesis_ko": (
            "「편집 불가 URL은 skip하고 ClickN/isweb 신규 profile bulk」— "
            "editable surface만 queue에 넣으면 성공률이 오른다."
        ),
        "next_hypothesis_id": "profile_bulk_new_signup",
        "actions": [
            "queue에서 roompang search·choicelounge 타인 URL 제외",
            "NEW_SIGNUP:profile 슬롯 비율 ↑ (daily_quota.profile)",
            "run_backlink_daily_plan.py 재생성",
        ],
        "confidence": 0.88,
    },
    "captcha_blocked": {
        "failure_ko": "가입·글쓰기 캡차 차단",
        "next_hypothesis_ko": (
            "「write_captcha=false pool 우선 + 2captcha 연동」— "
            "캡차 없는 profile/web2부터 1000/일 채운 뒤 captcha 플랫폼 확장."
        ),
        "next_hypothesis_id": "captcha_bypass_priority",
        "actions": [
            "notify_secrets / .env에 TWOCAPTCHA_API_KEY",
            "placement_qualifier write_captcha=false 필터",
            "min_trait_score 유지",
        ],
        "confidence": 0.82,
    },
    "login_required": {
        "failure_ko": "로그인·계정 없음 (roompang, clickn 등)",
        "next_hypothesis_ko": (
            "「PC notify_secrets에 CLICKN/ROOMPANG 계정 → Playwright 자동 로그인」— "
            "계정 없으면 profile 신규 가입 bulk가 유일한 자동 경로."
        ),
        "next_hypothesis_id": "credential_automation",
        "actions": [
            "core/notify_secrets.json → CLICKN_USER, CLICKN_PASS (gitignore)",
            "run_backlink_auto.py --adapter profile",
            "계정 없으면 Browser 수동 1회 후 cookie export",
        ],
        "confidence": 0.85,
    },
    "deploy_not_saved": {
        "failure_ko": "편집했으나 gangara.co.kr href live 미확인",
        "next_hypothesis_ko": (
            "「저장·캐시·nofollow 확인」— footer HTML 직접 삽입 후 재검증, "
            "동일 URL 2회 실패 시 skip하고 다음 placement."
        ),
        "next_hypothesis_id": "verify_and_retry_once",
        "actions": [
            "run_backlink_verify.py --row-id",
            "HTML `<a href>` dofollow 위치 변경 (본문 vs footer)",
            "2회 실패 → status failed_permanent",
        ],
        "confidence": 0.79,
    },
    "new_signup_pending": {
        "failure_ko": "NEW_SIGNUP 슬롯 — 아직 ClickN/isweb 사이트 미생성",
        "next_hypothesis_ko": (
            "「Playwright ClickN 무료 홈페이지 자동 생성」— "
            "3분/건 × 8브라우저 parallel = profile 450/일 경로."
        ),
        "next_hypothesis_id": "playwright_profile_farm",
        "actions": [
            "run_backlink_auto.py --adapter clickn",
            "CLICKN_USER/PASS in notify_secrets",
            "실패 시 web2(tistory)로 quota 이동",
        ],
        "confidence": 0.86,
    },
    "rate_limited": {
        "failure_ko": "IP·계정 rate limit / 429 / 차단",
        "next_hypothesis_ko": (
            "「머신·브라우저 분산 + 배치 pause」— "
            "machines_in_fleet 2+, batch_pause 60s, 동일 도메인 1시간 1건."
        ),
        "next_hypothesis_id": "fleet_throttle",
        "actions": [
            "run_backlink_prepare.py --machine-id N",
            "auto_batch_pause_sec ↑",
            "동일 registrable_domain cooldown",
        ],
        "confidence": 0.8,
    },
    "spam_rejected": {
        "failure_ko": "스팸·저품질 도메인 (postheaven, blogspot) 또는 purge 대상",
        "next_hypothesis_ko": (
            "「directory+guide_hub+ClickN만」— spam purge 유지, "
            "web2는 tistory/velog 신규 글만 (postheaven 금지)."
        ),
        "next_hypothesis_id": "backlink_quality_disavow_spam",
        "actions": [
            "purge_spam_master 재실행",
            "learning_loop exclude_spam_domains 유지",
        ],
        "confidence": 0.9,
    },
    "network_error": {
        "failure_ko": "네트워크·타임아웃·SSL 오류",
        "next_hypothesis_ko": "「재시도 3회 + 지수 backoff」— 일시 오류는 다음 batch에서 재queue.",
        "next_hypothesis_id": "retry_with_backoff",
        "actions": ["status queued로 복귀", "retry_count++", "3회 초과 failed"],
        "confidence": 0.75,
    },
    "unknown": {
        "failure_ko": "미분류 실패",
        "next_hypothesis_ko": "「실패 URL skip + pool 다음 row」— 로그 수집 후 failure_code 수동 매핑.",
        "next_hypothesis_id": "skip_and_advance",
        "actions": ["failed 기록", "다음 queued row"],
        "confidence": 0.6,
    },
}


def classify_failure(reason: str, row: dict | None = None) -> str:
    r = (reason or "").lower()
    row = row or {}
    url = (row.get("deploy_url") or "").lower()

    if row.get("deploy_url", "").startswith("NEW_SIGNUP:"):
        return "new_signup_pending"
    if "search?q=" in url or "choicelounge" in url or "seoulafterdark" in url:
        return "not_editable"
    if "postheaven" in url or "blogspot" in url:
        return "spam_rejected"
    if "captcha" in r or "recaptcha" in r:
        return "captcha_blocked"
    if "login" in r or "auth" in r or "credential" in r:
        return "login_required"
    if "no_href" in r or "not saved" in r:
        return "deploy_not_saved"
    if "429" in r or "rate" in r or "blocked" in r:
        return "rate_limited"
    if "timeout" in r or "ssl" in r or "connection" in r or "network" in r:
        return "network_error"
    if "not_deployed" in r:
        return "new_signup_pending"
    return "unknown"


def get_next_hypothesis(failure_code: str) -> dict[str, Any]:
    return FAILURE_NEXT_HYPOTHESES.get(failure_code, FAILURE_NEXT_HYPOTHESES["unknown"])


def render_failure_report(recent_failures: list[dict]) -> str:
    if not recent_failures:
        return "### 최근 실패 → 다음 가설\n- (없음)\n"

    lines = ["### 최근 실패 → 다음 가설\n"]
    seen: set[str] = set()
    for f in recent_failures[-10:]:
        code = f.get("failure_code", "unknown")
        if code in seen:
            continue
        seen.add(code)
        hyp = get_next_hypothesis(code)
        lines.append(f"**실패:** {hyp['failure_ko']}")
        lines.append(f"**다음 가설:** {hyp['next_hypothesis_ko']}")
        lines.append("**액션:**")
        for a in hyp.get("actions", []):
            lines.append(f"- {a}")
        lines.append("")
    return "\n".join(lines)
