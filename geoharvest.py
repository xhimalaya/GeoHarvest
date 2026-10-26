#!/usr/bin/env python3
import os
import sys
import time
import argparse
import webbrowser
import threading
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Auto-switch to project virtualenv if not already executing within it
if os.environ.get("_GEOHARVEST_REEXEC") != "1":
    venv_py = BASE_DIR / "venv" / "bin" / "python"
    dot_venv_py = BASE_DIR / ".venv" / "bin" / "python"
    target_py = None
    if venv_py.exists() and Path(sys.executable).resolve() != venv_py.resolve():
        target_py = venv_py
    elif dot_venv_py.exists() and Path(sys.executable).resolve() != dot_venv_py.resolve() and not venv_py.exists():
        target_py = dot_venv_py
    if target_py:
        os.environ["_GEOHARVEST_REEXEC"] = "1"
        os.execv(str(target_py), [str(target_py)] + sys.argv)

import uvicorn
from backend.app.dependencies.config import settings
from backend.app.dependencies.database import init_db
from backend.core.recovery.manager import crash_recovery_manager


def open_browser(url: str, delay_sec: float = 1.2):
    def _open():
        time.sleep(delay_sec)
        print(f"\n[GeoHarvest] Opening web browser at {url} ...")
        webbrowser.open(url)
    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(description="GeoHarvest Desktop Platform")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind (default: 9009)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot-reload")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print(f"       GeoHarvest v{settings.app_version} - Desktop Platform")
    import re
    safe_db_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", settings.get_database_url)
    print(f"[1/4] Initializing database at: {safe_db_url}")
    init_db()

    print("[2/4] Checking and recovering previous jobs...")
    recovered = crash_recovery_manager.recover_interrupted_jobs()
    if recovered > 0:
        print(f"      -> Successfully recovered {recovered} interrupted job(s)!")
    else:
        print("      -> No interrupted jobs. Clean state.")

    print(f"[3/4] Ready to serve at: {url}")
    if not args.no_browser:
        open_browser(url)

    print("[4/4] Starting FastAPI Core Engine...")
    print("=" * 60)

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
