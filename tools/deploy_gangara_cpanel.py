#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cPanel File Manager → public_html 업로드 (env: GANGARA_CPANEL_*)."""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "website 확장 수집/templates/gangara-hub"
ZIP = REPO / "tools/gangara-hub-deploy.zip"
CPANEL = os.environ.get("GANGARA_CPANEL_URL", "https://gangara.co.kr:2083/")


def pack() -> Path:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in SRC.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(SRC))
    print(f"packed {ZIP.stat().st_size} bytes")
    return ZIP


def main() -> int:
    user = os.environ.get("GANGARA_CPANEL_USER", os.environ.get("GANGARA_FTP_USER", ""))
    password = os.environ.get("GANGARA_CPANEL_PASS", os.environ.get("GANGARA_FTP_PASS", ""))
    if not user or not password:
        print("ERROR: GANGARA_CPANEL_USER/PASS or GANGARA_FTP_USER/PASS required", file=sys.stderr)
        return 1

    pack()
    from playwright.sync_api import sync_playwright

    headless = os.environ.get("HEADLESS", "1") != "0"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.goto(CPANEL, timeout=60000)
        page.fill('input#user, input[name="user"]', user)
        page.fill('input#pass, input[name="pass"]', password)
        page.click('button#login_submit, #login_submit')
        page.wait_for_load_state("networkidle", timeout=30000)

        if "login" in page.url.lower() and "cpsession" not in page.url:
            print("ERROR: cPanel login failed", page.url, file=sys.stderr)
            browser.close()
            return 1

        print("cPanel login OK:", page.url[:80])

        # File Manager iframe
        page.goto(page.url.split("/login")[0].rstrip("/") + "/frontend/jupiter/filemanager/index.html", timeout=60000)
        page.wait_for_timeout(3000)

        # public_html 이동 후 zip 업로드 (cPanel Jupiter UI)
        for sel in ['text=public_html', 'a:has-text("public_html")']:
            try:
                page.locator(sel).first.click(timeout=5000)
                break
            except Exception:
                pass

        page.wait_for_timeout(2000)
        with page.expect_file_chooser(timeout=15000) as fc_info:
            for sel in ['text=Upload', 'button:has-text("Upload")', '#btnUpload']:
                try:
                    page.locator(sel).first.click(timeout=3000)
                    break
                except Exception:
                    continue
        fc = fc_info.value
        fc.set_files(str(ZIP))
        page.wait_for_timeout(8000)

        # Extract zip if upload succeeded
        for sel in ['text=Extract', 'button:has-text("Extract")']:
            try:
                page.locator(sel).first.click(timeout=5000)
                page.wait_for_timeout(5000)
                break
            except Exception:
                pass

        page.goto("https://gangara.co.kr/", timeout=30000)
        h1 = page.locator("h1").first.inner_text(timeout=8000)
        print("Live H1:", h1[:100])
        browser.close()

    if "완벽 가이드" in h1 or "강남가라" in h1:
        print("OK deploy verified")
        return 0
    print("WARN: fusion H1 not detected — manual extract may be needed", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
