#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playwright로 호스팅/Netlify 배포 시도 — env 또는 Chrome 프로필."""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "website 확장 수집/templates/gangara-hub"
ZIP = REPO / "tools/gangara-hub-deploy.zip"


def make_zip() -> Path:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in SRC.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(SRC))
    return ZIP


def try_netlify_drop(page) -> bool:
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "")
    if not token:
        return False
    page.goto("https://app.netlify.com/")
    return True


def try_hosting_ftp_env() -> int:
    from deploy_gangara_hub import main as ftp_main
    return ftp_main()


def main() -> int:
    if os.environ.get("GANGARA_FTP_USER") and os.environ.get("GANGARA_FTP_PASS"):
        return try_hosting_ftp_env()

    make_zip()
    print(f"Packaged {ZIP} ({ZIP.stat().st_size} bytes)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed")
        return 1

    user = os.environ.get("GANGARA_FTP_USER", "")
    pwd = os.environ.get("GANGARA_FTP_PASS", "")
    panel = os.environ.get("GANGARA_PANEL_URL", "https://www.hosting.kr/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        if user and pwd:
            # 호스팅코리아 파일매니저 (일반 패턴 — 계정별 URL 상이)
            fm = os.environ.get("GANGARA_FILEMANAGER_URL", "")
            if fm:
                page.goto(fm, timeout=60000)
                page.fill('input[name="username"], input#username, input[type="text"]', user)
                page.fill('input[name="password"], input#password, input[type="password"]', pwd)
                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_timeout(3000)
                print("Logged into file manager — manual upload may be required")
        browser.close()

    print("Deploy needs GANGARA_FTP_USER + GANGARA_FTP_PASS in env")
    print("Run: GANGARA_FTP_USER=... GANGARA_FTP_PASS=... python3 tools/deploy_gangara_hub.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
