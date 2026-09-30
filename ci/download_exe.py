# -*- coding: utf-8 -*-
"""等待 GitHub Release 中的 PyTray.exe 并下载到 dist/。

供 CNB 云原生构建在 tag_push 时调用（见 .cnb.yml）。
"""
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    tag = os.environ.get("CNB_BRANCH", "").strip()
    repo = os.environ.get("GITHUB_REPO", "borisxxz/PyTray").strip()
    exe = os.environ.get("EXE_NAME", "PyTray.exe").strip()
    timeout = int(os.environ.get("WAIT_TIMEOUT_SEC", "1800"))
    if not tag:
        print("CNB_BRANCH is empty; expected a tag_push event", file=sys.stderr)
        return 2

    url = f"https://github.com/{repo}/releases/download/{tag}/{exe}"
    dest = Path("dist") / exe
    dest.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        print(f"[{attempt}] GET {url}", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            size = dest.stat().st_size
            if size < 1024:
                raise RuntimeError(f"file too small: {size} bytes")
            print(f"OK {dest} ({size} bytes)", flush=True)
            return 0
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, OSError) as e:
            print(f"    not ready: {e}", flush=True)
            time.sleep(20)
    print(f"timed out waiting for {url}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
