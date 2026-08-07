"""Auto-install, configure, and start a local SearXNG instance."""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
import time

import httpx

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARXNG_DIR = os.path.join(_DIR, "searxng", "searxng-src")
SETTINGS_PATH = os.path.join(_DIR, "searxng", "settings.yml")
DEFAULT_PORT = 8888
DEFAULT_HOST = "127.0.0.1"

_process: subprocess.Popen | None = None


def _is_installed() -> bool:
    """Check if SearXNG is importable."""
    try:
        import searx  # noqa: F401
        return True
    except ImportError:
        return False


def _install():
    """Clone and install SearXNG into the current environment."""
    if not os.path.isdir(SEARXNG_DIR):
        print("[web-mcp] Cloning SearXNG...", flush=True)
        subprocess.check_call(
            ["git", "clone", "--depth", "1", "https://github.com/searxng/searxng.git", SEARXNG_DIR],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    # SearXNG's setup.py imports searx which imports msgspec at build time.
    # We must install its runtime deps + build tools first, then use
    # --no-build-isolation so the build subprocess can see them.
    print("[web-mcp] Installing build tools and SearXNG dependencies...", flush=True)
    req_file = os.path.join(SEARXNG_DIR, "requirements.txt")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "setuptools", "wheel", "-r", req_file],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    print("[web-mcp] Installing SearXNG...", flush=True)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "--no-build-isolation", "--no-deps", SEARXNG_DIR],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print("[web-mcp] SearXNG installed.", flush=True)


def _health_check(url: str, retries: int = 30) -> bool:
    for _ in range(retries):
        try:
            r = httpx.get(f"{url}/search", params={"q": "test", "format": "json"}, timeout=2)
            if r.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            # Not up yet -- that is what we are polling for; sleep and retry.
            pass
        time.sleep(1)
    return False


def _shutdown():
    # Claim the handle before touching it: _shutdown runs both on a failed
    # start-up and again via atexit, and clearing it first keeps the second
    # call from signalling a pid that has already been reaped.
    global _process
    process, _process = _process, None
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def ensure_running(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    """Ensure SearXNG is installed and running. Returns the base URL."""
    global _process
    url = f"http://{host}:{port}"

    # Already running?
    try:
        r = httpx.get(f"{url}/search", params={"q": "test", "format": "json"}, timeout=2)
        if r.status_code == 200:
            return url
    except (httpx.ConnectError, httpx.TimeoutException):
        # Nothing listening on that port, so no instance to reuse; fall
        # through and start one.
        pass

    # Install if needed
    if not _is_installed():
        _install()

    # Start SearXNG
    env = {**os.environ, "SEARXNG_SETTINGS_PATH": SETTINGS_PATH}
    _process = subprocess.Popen(
        [sys.executable, "-m", "searx.webapp"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(_shutdown)

    print("[web-mcp] Starting SearXNG...", flush=True)
    if not _health_check(url):
        _shutdown()
        raise RuntimeError("SearXNG failed to start")

    print(f"[web-mcp] SearXNG ready at {url}", flush=True)
    return url
