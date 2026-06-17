# -*- coding: utf-8 -*-
"""Track B — 로컬 API 키 자동 로드 (커밋 금지 파일만)."""
from __future__ import annotations

import json
import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_ENV = _REPO / ".env"

# 게시판 자동화 프로젝트에 이미 있는 키 경로
_SEARCH_PATHS = [
    _REPO / "captcha_solver.json",
    _REPO / "tools" / "captcha_solver.json",
    Path(r"C:\Users\qordj\Desktop\게시글 자동화_원드라이브아님\게시판 자동 등록\misc\data\captcha_solver.json"),
    Path(r"C:\Users\qordj\Desktop\게시글 자동화_원드라이브아님\게시판 수집 및 회원가입\misc\data\captcha_solver.json"),
    Path(r"C:\Users\qordj\OneDrive\Desktop\게시글 자동화\게시판 자동 등록\misc\data\captcha_solver.json"),
]

_LOCAL_DEFAULTS = [
    Path(r"C:\Users\qordj\Desktop\게시글 자동화_원드라이브아님\게시판 자동 등록\misc\_program\local_defaults.py"),
    Path(r"C:\Users\qordj\OneDrive\Desktop\게시글 자동화\게시판 자동 등록\misc\_program\local_defaults.py"),
]


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


def _from_captcha_json(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        key = (data.get("api_key") or "").strip()
        if key and key not in ("your_2captcha_key", "여기에_2captcha_API_키", "여기에_키"):
            return key
    except Exception:
        pass
    return ""


def _from_local_defaults(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        ns: dict = {}
        exec(path.read_text(encoding="utf-8"), ns)  # noqa: S102 — trusted local file
        return (ns.get("DEFAULT_TWOCAPTCHA_KEY") or "").strip()
    except Exception:
        return ""


def load_secrets() -> dict[str, str]:
    """환경변수 + .env + 알려진 로컬 경로 순으로 병합."""
    merged: dict[str, str] = {}

    for p in _SEARCH_PATHS:
        k = _from_captcha_json(p)
        if k:
            merged.setdefault("TWOCAPTCHA_API_KEY", k)

    for p in _LOCAL_DEFAULTS:
        k = _from_local_defaults(p)
        if k:
            merged.setdefault("TWOCAPTCHA_API_KEY", k)

    merged.update(_parse_env_file(_ENV))

    for name in (
        "TWOCAPTCHA_API_KEY",
        "AHREFS_API_KEY",
        "SEMRUSH_API_KEY",
        "SEOREVIEWTOOLS_API_KEY",
        "BLAZEHIVE_API_KEY",
    ):
        val = (os.environ.get(name) or merged.get(name) or "").strip()
        if val:
            merged[name] = val
            os.environ[name] = val

    return merged


def ensure_env_file() -> Path:
    """키가 없으면 로컬에서 찾아 .env 에 기록 (gitignore)."""
    secrets = load_secrets()
    if not secrets.get("TWOCAPTCHA_API_KEY") and not _ENV.is_file():
        return _ENV
    lines = []
    if _ENV.is_file():
        lines = _ENV.read_text(encoding="utf-8", errors="replace").splitlines()
    existing = {ln.split("=", 1)[0].strip() for ln in lines if "=" in ln and not ln.strip().startswith("#")}

    changed = False
    for k, v in secrets.items():
        if k not in existing and v:
            lines.append(f"{k}={v}")
            changed = True
    if changed:
        _ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _ENV
