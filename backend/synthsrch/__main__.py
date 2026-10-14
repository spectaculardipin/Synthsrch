"""`synthsrch` CLI — start localhost server, open browser. `synthsrch doctor` for checks."""
from __future__ import annotations

import argparse
import socket
import sys
import webbrowser

import uvicorn


def find_port(preferred: int) -> int:
    for p in range(preferred, preferred + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return preferred


def cmd_serve(port: int, no_browser: bool) -> int:
    from .db import init_db
    import asyncio

    asyncio.run(init_db())
    port = find_port(port)
    url = f"http://127.0.0.1:{port}"
    print(f"Synthsrch — Learn without clutter.\nServing {url} ...", flush=True)
    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    # keep host pinned to localhost; frontend build served by app if present
    uvicorn.run("synthsrch.app:app", host="127.0.0.1", port=port, log_level="info")
    return 0


def cmd_doctor() -> int:
    from .config import get_settings
    s = get_settings()
    print(f"python: {sys.version.split()[0]}")
    print(f"db: {s.db_path} exists={s.db_path.exists()}")
    print(f"host/port: {s.host}/{s.port}")
    print(f"nim: {s.nim_base_url} model={s.nim_model} key={'set' if s.nim_api_key else 'MISSING'}")
    for name in ("tavily", "exa", "serper", "linkup", "firecrawl"):
        has = bool(getattr(s, f"{name}_api_key"))
        print(f"{name}: {'set' if has else 'MISSING'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="synthsrch", description="Synthsrch — local search & synthesis")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("command", nargs="?", default="serve", choices=["serve", "doctor"])
    args = ap.parse_args(argv)
    if args.command == "doctor":
        return cmd_doctor()
    return cmd_serve(args.port, args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
