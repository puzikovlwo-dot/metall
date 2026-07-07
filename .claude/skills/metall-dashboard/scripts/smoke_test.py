"""
smoke_test.py — Headless boot test for the METALL dashboard.

Boots the Dash/Flask app on a free port via werkzeug in a daemon thread,
hits a few internal endpoints, then shuts down. Catches:
  - import-time errors
  - callback signature mismatches (raised on first request)
  - missing data files
  - dead routes

Usage:
    python .claude/skills/metall-dashboard/scripts/smoke_test.py

Exit codes:
    0  success
    1  smoke test failed
"""
import os
import sys
import socket
import urllib.request
import threading


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    # scripts/smoke_test.py → scripts/ → metall-dashboard/ → skills/ → .claude/ → repo root
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    os.chdir(repo_root)
    sys.path.insert(0, repo_root)

    try:
        import app  # noqa: F401
    except Exception as e:
        print(f"[FAIL] app.py failed to import: {e}", file=sys.stderr)
        return 1

    from werkzeug.serving import make_server

    port = _free_port()
    server = make_server("127.0.0.1", port, app.app.server)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    routes = [
        ("/",               200, "html shell"),
        ("/_dash-layout",   200, "layout tree"),
        ("/_dash-dependencies", 200, "callback graph"),
    ]
    failed = []
    for route, expected, label in routes:
        url = f"http://127.0.0.1:{port}{route}"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                body = r.read()
                if r.status != expected or len(body) == 0:
                    failed.append((route, f"status={r.status} len={len(body)}"))
                else:
                    print(f"[OK]   GET {route:25s}  {r.status} ({label})")
        except Exception as e:
            failed.append((route, str(e)))
            print(f"[FAIL] GET {route}  → {e}", file=sys.stderr)

    server.shutdown()

    if failed:
        print(f"\n{len(failed)} route(s) failed:", file=sys.stderr)
        for route, err in failed:
            print(f"  - {route}: {err}", file=sys.stderr)
        return 1

    print("\n[OK] smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
