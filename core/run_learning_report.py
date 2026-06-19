#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학습 루프 결과 보고 — 가설→실험→결과(일치/불일치) 형식.

  python3 core/run_learning_report.py
  python3 core/run_learning_report.py --email   # GANGARA_REPORT_* env 있으면 발송
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from learning_hypothesis_report import evaluate_experiment, render_experiment_markdown

REPO = Path(__file__).resolve().parent.parent
EXPERIMENT = REPO / "core/gangara_experiment.json"
STATUS = REPO / "core/backlink_deploy_status.json"
SERP = REPO / "tools/serp_rank_probe_output.json"
QUEUE = REPO / "core/backlink_deploy_queue.json"
DIGEST_MD = REPO / "tools/LEARNING_DIGEST_LATEST.md"
DIGEST_JSON = REPO / "tools/LEARNING_DIGEST_LATEST.json"
SCHEDULE_STATE = REPO / "tools/report_schedule_state.json"
CONFIG = REPO / "core/machine_config.json"
DEFAULT_REPORT_EMAIL = "qordjr2037@gmail.com"
NOTIFY_SECRETS = REPO / "core/notify_secrets.json"
ENV_FILE = REPO / ".env"
SMTP_ENV_KEYS = (
    "GANGARA_REPORT_EMAIL_TO",
    "GANGARA_SMTP_USER",
    "GANGARA_SMTP_PASS",
    "GANGARA_SMTP_HOST",
    "GANGARA_SMTP_PORT",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _load_smtp_env() -> None:
    """env → .env → core/notify_secrets.json (gitignore) 순으로 SMTP 설정 병합."""
    merged: dict[str, str] = {}
    if NOTIFY_SECRETS.is_file():
        try:
            data = json.loads(NOTIFY_SECRETS.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in SMTP_ENV_KEYS:
                    val = data.get(k) or data.get(k.lower())
                    if val:
                        merged[k] = str(val).strip()
        except Exception:
            pass
    merged.update(_parse_env_file(ENV_FILE))
    for k in SMTP_ENV_KEYS:
        val = (os.environ.get(k) or merged.get(k) or "").strip()
        if val:
            os.environ[k] = val


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_digest() -> dict:
    exp = load_json(EXPERIMENT, {})
    st = load_json(STATUS, {})
    serp = load_json(SERP, {})
    queue = load_json(QUEUE, {})
    ll = exp.get("learning_loop") or st.get("learning_loop") or {}
    cycles = exp.get("learning_cycles") or []
    last_cycle = cycles[-1] if cycles else {}

    ranks = {}
    top10 = 0
    for r in serp.get("results") or []:
        ranks[r.get("keyword", "")] = r.get("rank")
        if r.get("in_top10"):
            top10 += 1

    sync = st.get("gates", {}).get("sync_push", {})
    hypothesis = ll.get("hypothesis") or {}
    if isinstance(hypothesis, dict):
        hyp_text = hypothesis.get("statement_ko") or hypothesis.get("primary", "")
        hyp_id = hypothesis.get("primary", "")
    else:
        hyp_text = str(hypothesis)
        hyp_id = str(hypothesis)

    cmp = ll.get("comparison") or {}
    confidence = (hypothesis.get("confidence") if isinstance(hypothesis, dict) else None) or (
        last_cycle.get("confidence")
    )

    prev_cycle = None
    cur_num = ll.get("cycle") or last_cycle.get("cycle")
    if cur_num and cycles:
        numbered = [c for c in cycles if c.get("cycle") is not None]
        for c in reversed(numbered):
            if c.get("cycle") == cur_num:
                last_cycle = c
                break
        for c in reversed(numbered):
            cn = c.get("cycle")
            if cn is not None and cur_num is not None and cn < cur_num:
                prev_cycle = c
                break

    experiment = evaluate_experiment(
        hyp_id or "backlink_quality_and_type",
        hypothesis if isinstance(hypothesis, dict) else {"statement_ko": hyp_text},
        cmp,
        last_cycle or {},
        prev_cycle,
        deploy_queue_pending=queue.get("count", 0),
        fusion_live=(st.get("fusion_live") or {}).get("deployed", False),
        pool_total=sync.get("pool_total"),
        sync_count=sync.get("count"),
    )

    failure_md = ""
    try:
        sys.path.insert(0, str(REPO / "core"))
        from backlink_verified_store import load_store  # noqa: WPS433
        from failure_hypotheses import render_failure_report  # noqa: WPS433

        vstore = load_store()
        failure_md = render_failure_report(vstore.get("failures") or [])
        nh = (exp.get("learning_loop") or {}).get("next_hypothesis_on_failure")
        if nh:
            failure_md += (
                f"\n### 현재 dominant 실패 → 적용 중인 다음 가설\n"
                f"{nh.get('statement_ko', '—')}\n"
            )
    except Exception:
        pass

    digest = {
        "generated_at": now_iso(),
        "goal_met": ll.get("goal_met") or st.get("learning_loop", {}).get("goal_met", False),
        "serp_top10": f"{top10}/3",
        "serp_ranks": ranks,
        "hypothesis_id": hyp_id,
        "hypothesis_ko": hyp_text,
        "hypothesis_confidence": f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "?",
        "learning_cycle": ll.get("cycle") or last_cycle.get("cycle"),
        "pool_total": sync.get("pool_total"),
        "sync_count": sync.get("count"),
        "deploy_queue_pending": queue.get("count", 0),
        "awaiting_pc_deploy": exp.get("learning_loop", {}).get("awaiting_pc_deploy", False),
        "fusion_live": (st.get("fusion_live") or {}).get("deployed", False),
        "next_actions": st.get("next_actions", [])[:4],
        "money_site": st.get("money_site", "https://gangara.co.kr/"),
        "experiment": experiment,
        "failure_hypotheses_md": failure_md,
    }
    return digest


def render_markdown(d: dict) -> str:
    return render_experiment_markdown(d)


def _report_interval_hours() -> int:
    cfg = load_json(CONFIG, {})
    return int((cfg.get("learning_loop") or {}).get("report_interval_hours", 3))


def _load_schedule_state() -> dict:
    return load_json(SCHEDULE_STATE, {"last_email_at": None, "last_digest_at": None})


def _save_schedule_state(state: dict) -> None:
    SCHEDULE_STATE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _email_is_due(force: bool = False) -> bool:
    if force:
        return True
    state = _load_schedule_state()
    last = state.get("last_email_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return elapsed >= _report_interval_hours() * 3600
    except Exception:
        return True


def _report_email() -> str:
    cfg = load_json(CONFIG, {})
    return (
        os.environ.get("GANGARA_REPORT_EMAIL_TO", "").strip()
        or (cfg.get("learning_loop") or {}).get("report_email", "")
        or DEFAULT_REPORT_EMAIL
    )


def send_email(subject: str, body_md: str, digest: dict) -> bool:
    _load_smtp_env()
    to_addr = _report_email()
    smtp_host = os.environ.get("GANGARA_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("GANGARA_SMTP_PORT", "587"))
    smtp_user = os.environ.get("GANGARA_SMTP_USER", "").strip() or to_addr
    smtp_pass = os.environ.get("GANGARA_SMTP_PASS", "").strip()

    if not smtp_pass:
        print(f"EMAIL skip: GANGARA_SMTP_PASS not set (to={to_addr})", file=sys.stderr)
        print(
            "core/notify_secrets.json (gitignore) 또는 GitHub Secret GANGARA_SMTP_PASS 필요",
            file=sys.stderr,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_md, "plain", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_addr], msg.as_string())
        print(f"EMAIL sent → {to_addr}")
        state = _load_schedule_state()
        state["last_email_at"] = now_iso()
        state["last_digest_at"] = digest.get("generated_at") or now_iso()
        state["report_interval_hours"] = _report_interval_hours()
        _save_schedule_state(state)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"EMAIL auth failed: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"EMAIL failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", action="store_true", help="Gmail/SMTP로 보고 발송")
    ap.add_argument(
        "--scheduled",
        action="store_true",
        help="스케줄 모드 — report_interval_hours 경과 시에만 발송 (기본 3h)",
    )
    ap.add_argument("--force", action="store_true", help="--scheduled 시 due 무시하고 즉시 발송")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    digest = build_digest()
    md = render_markdown(digest)

    DIGEST_MD.write_text(md, encoding="utf-8")
    DIGEST_JSON.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    state = _load_schedule_state()
    state["last_digest_at"] = digest["generated_at"]
    _save_schedule_state(state)

    if not args.quiet:
        print(md)

    if args.email:
        if args.scheduled and not _email_is_due(force=args.force):
            hours = _report_interval_hours()
            print(f"EMAIL skip: scheduled — next in ≤{hours}h (tools/report_schedule_state.json)")
            return 0
        exp = digest.get("experiment") or {}
        verdict = exp.get("verdict_ko", "—")
        subj = (
            f"[gangara 학습] {verdict} · SERP {digest['serp_top10']} · "
            f"cycle {digest.get('learning_cycle', '?')}"
        )
        if not send_email(subj, md, digest):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
