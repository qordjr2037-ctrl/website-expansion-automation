#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gangara-hub → gangara.co.kr FTP 배포 (env: GANGARA_FTP_*)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "website 확장 수집/templates/gangara-hub"


def main() -> int:
    host = os.environ.get("GANGARA_FTP_HOST", "ftp.gangara.co.kr")
    user = os.environ.get("GANGARA_FTP_USER", "")
    password = os.environ.get("GANGARA_FTP_PASS", "")
    remote = os.environ.get("GANGARA_FTP_REMOTE", "/public_html")

    if not user or not password:
        print("ERROR: GANGARA_FTP_USER / GANGARA_FTP_PASS env required", file=sys.stderr)
        return 1

    if not SRC.is_dir():
        print(f"ERROR: missing {SRC}", file=sys.stderr)
        return 1

    # lftp mirror upload
    script = f"""
set ssl:verify-certificate no
open -u {user},{password} {host}
lcd {SRC}
cd {remote}
mirror --reverse --delete --verbose --exclude-glob .git* --exclude-glob .DS_Store
bye
"""
    rc = subprocess.run(["lftp", "-c", script], capture_output=True, text=True)
    print(rc.stdout)
    if rc.stderr:
        print(rc.stderr, file=sys.stderr)
    if rc.returncode == 0:
        print("OK deploy complete → https://gangara.co.kr/")
    return rc.returncode


if __name__ == "__main__":
    sys.exit(main())
