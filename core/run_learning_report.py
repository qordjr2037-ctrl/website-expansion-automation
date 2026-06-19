#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학습 루프 결과 보고 — 3시간 스케줄 / 사용자 메시지 / Gmail(선택).

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

REPO = Path(__file__).resolve().parent.parent
EXPERIMENT = REPO / "core/gangara_experiment.json"
STATUS = REPO / "core/backlink_deploy_status.json"
SERP = REPO / "tools/serp_rank_probe_output.json"
QUEUE = REPO / "core/backlink_deploy_queue.json"
DIGEST_MD = REPO / "tools/LEARNING_DIGEST_LATEST.md"
DIGEST_JSON = REPO / "tools/LEARNING_DIGEST_LATEST.json"
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
    you_rd = (cmp.get("you") or {}).get("rd") or st.get("pool_keyword_coverage", {})

    digest = {
        "generated_at": now_iso(),
        "goal_met": ll.get("goal_met") or st.get("learning_loop", {}).get("goal_met", False),
        "serp_top10": f"{top10}/3",
        "serp_ranks": ranks,
        "hypothesis_id": hyp_id,
        "hypothesis_ko": hyp_text,
        "learning_cycle": ll.get("cycle") or last_cycle.get("cycle"),
        "pool_total": sync.get("pool_total"),
        "sync_count": sync.get("count"),
        "deploy_queue_pending": queue.get("count", 0),
        "awaiting_pc_deploy": exp.get("learning_loop", {}).get("awaiting_pc_deploy", False),
        "fusion_live": (st.get("fusion_live") or {}).get("deployed", False),
        "next_actions": st.get("next_actions", [])[:4],
        "money_site": st.get("money_site", "https://gangara.co.kr/"),
    }
    return digest


def render_markdown(d: dict) -> str:
    rank_lines = "\n".join(
        f"| {kw} | {r if r else '미노출'} | {'✅' if r and r <= 10 else '❌'} |"
        for kw, r in d.get("serp_ranks", {}).items()
    )
    actions = "\n".join(f"- {a}" for a in d.get("next_actions", []))
    return f"""# gangara 학습 루프 보고 — {d['generated_at']}

## SERP (목표: 3키워드 top10)
**현재:** {d['serp_top10']} | **goal_met:** {d['goal_met']}

| 키워드 | rank | top10 |
|--------|------|-------|
{rank_lines}

## 가설 (cycle {d.get('learning_cycle', '?')})
{d.get('hypothesis_ko', '—')}

## 큐·풀
- sync: {d.get('sync_count')} / pool: {d.get('pool_total')}
- **Browser 배포 대기:** {d.get('deploy_queue_pending')}건 (`core/backlink_deploy_queue.json`)
- fusion live: {'✅' if d.get('fusion_live') else '❌'}
- PC deploy 필요: {'⚠️ 예' if d.get('awaiting_pc_deploy') else '아니오'}

## 다음 액션
{actions or '- —'}

## 재실행
```bash
python3 core/run_learning_loop.py --until-top10 --max-cycles 5
python3 core/run_learning_report.py --email
```

프롬프트: `tools/CURSOR_BROWSER_DEPLOY_QUEUE_PROMPT.md`
"""


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
        print(
            "호스팅/cPanel 비번 ≠ Gmail SMTP — 앱 비밀번호: https://myaccount.google.com/apppasswords",
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
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"EMAIL auth failed: {e}", file=sys.stderr)
        print(
            "로그인 거부 — cPanel/호스팅 비번으로는 Gmail SMTP 불가. "
            "Google 계정 → 앱 비밀번호(16자) 생성 후 notify_secrets.json 또는 "
            "GitHub Secret GANGARA_SMTP_PASS 에 등록",
            file=sys.stderr,
        )
        print("https://myaccount.google.com/apppasswords", file=sys.stderr)
        return False
    except Exception as e:
        print(f"EMAIL failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", action="store_true", help="Gmail/SMTP로 보고 발송")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    digest = build_digest()
    md = render_markdown(digest)

    DIGEST_MD.write_text(md, encoding="utf-8")
    DIGEST_JSON.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        print(md)

    if args.email:
        subj = f"[gangara 학습] SERP {digest['serp_top10']} | queue {digest['deploy_queue_pending']}건"
        send_email(subj, md, digest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
