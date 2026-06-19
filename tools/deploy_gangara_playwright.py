#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chrome 프로필 + Playwright로 Netlify/호스팅 배포 시도."""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "website 확장 수집/templates/gangara-hub"
ZIP = REPO / "tools/gangara-hub-deploy.zip"
CHROME = Path("/home/ubuntu/.config/google-chrome")


def pack() -> Path:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in SRC.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(SRC))
    print(f"zip {ZIP.stat().st_size} bytes")
    return ZIP


def main() -> int:
    pack()
    from playwright.sync_api import sync_playwright

    headless = os.environ.get("HEADLESS", "1") != "0"
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(CHROME),
                channel="chrome",
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        except Exception as e:
            print("Chrome profile launch failed:", e)
            browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
            context = browser.new_context()

        page = context.new_page()

        # 1) Netlify — gangara.netlify.app
        page.goto("https://app.netlify.com/", timeout=60000)
        page.wait_for_timeout(3000)
        title = page.title()
        url = page.url
        print("Netlify:", title, url)

        if "login" not in url.lower() and "netlify" in url:
            page.goto("https://app.netlify.com/sites/gangara/deploys", timeout=60000)
            page.wait_for_timeout(2000)
            # Deploy drop zone
            try:
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    page.locator('input[type="file"]').first.click()
                fc = fc_info.value
                fc.set_files(str(ZIP))
                print("Uploaded zip to Netlify")
                page.wait_for_timeout(10000)
            except Exception as e:
                print("Netlify upload:", e)

        # 2) Verify live
        page.goto("https://gangara.co.kr/", timeout=30000)
        h1 = page.locator("h1").first.inner_text(timeout=5000) if page.locator("h1").count() else "no h1"
        print("Live gangara.co.kr H1:", h1[:80])

        context.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
