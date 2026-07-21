"""Execution backends for the Colab shell.

Two ways to reach Colab's shell, behind one interface:

* :class:`LocalBackend` runs commands in *this* process. It is what the server
  uses when it is launched from inside the Colab notebook itself — the process
  already lives in the Colab VM, so "the shell" is just a local subprocess.

* :class:`RemoteBridgeBackend` speaks HTTP to a :mod:`colab_shell_client.bridge`
  instance running inside a Colab VM (typically exposed through a Cloudflare or
  Colab port-proxy tunnel). This is what the server uses when it runs on your
  laptop and drives a remote Colab runtime.

``make_backend`` picks one from the environment: a bridge URL means remote,
otherwise local.
"""

import base64
import os

from . import core


class LocalBackend:
    """Run Colab's shell directly in the current process."""

    mode = "local"

    def __init__(self, command_timeout: int = core.DEFAULT_COMMAND_TIMEOUT):
        self.command_timeout = command_timeout

    def describe(self) -> str:
        return "local (executing inside this runtime)"

    def health(self) -> dict:
        return {"status": "ok", "mode": self.mode}

    def run(self, command: str, timeout: int | None = None) -> dict:
        return core.run_command(command, timeout or self.command_timeout)

    def list_dir(self, path: str) -> list[dict]:
        return core.list_directory(path)

    def read_bytes(self, path: str) -> dict:
        return core.read_bytes(path)

    def write_bytes(self, path: str, data: bytes) -> dict:
        return core.write_bytes(path, data)

    def sysinfo(self) -> dict:
        return core.system_info()


class RemoteBridgeBackend:
    """Reach Colab's shell over HTTP through a running bridge."""

    mode = "remote"

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        command_timeout: int = core.DEFAULT_COMMAND_TIMEOUT,
        connect_timeout: float = 30.0,
        verify_tls: bool = True,
    ):
        if not base_url:
            raise ValueError("COLAB_BRIDGE_URL is required for the remote backend")
        # Imported lazily so the bridge (stdlib only) and the local backend
        # never pull in httpx just by importing this module.
        import httpx

        self.base_url = base_url.rstrip("/")
        self.command_timeout = command_timeout
        self.connect_timeout = connect_timeout
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._httpx = httpx
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            verify=verify_tls,
            timeout=connect_timeout,
            follow_redirects=True,
        )

    def describe(self) -> str:
        return f"remote bridge at {self.base_url}"

    def _wrap(self, exc) -> RuntimeError:
        return RuntimeError(
            f"Colab bridge request failed ({exc}). Confirm the bridge cell is "
            f"still running in the Colab notebook and COLAB_BRIDGE_URL / "
            f"COLAB_BRIDGE_TOKEN match what it printed."
        )

    def _get(self, path: str, params: dict | None = None, timeout: float | None = None):
        try:
            response = self._client.get(path, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except self._httpx.HTTPError as exc:
            raise self._wrap(exc) from exc

    def _post(self, path: str, payload: dict, timeout: float | None = None):
        try:
            response = self._client.post(path, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except self._httpx.HTTPError as exc:
            raise self._wrap(exc) from exc

    def health(self) -> dict:
        return self._get("/health", timeout=self.connect_timeout)

    def run(self, command: str, timeout: int | None = None) -> dict:
        timeout = timeout or self.command_timeout
        # Give the HTTP read a margin beyond the command's own timeout so the
        # bridge, not the client, is the thing that decides a command timed out.
        return self._post(
            "/exec",
            {"command": command, "timeout": timeout},
            timeout=timeout + 15,
        )

    def list_dir(self, path: str) -> list[dict]:
        return self._get("/list", params={"path": path})["entries"]

    def read_bytes(self, path: str) -> dict:
        result = self._post("/read", {"path": path}, timeout=self.command_timeout)
        return {
            "data": base64.b64decode(result["content_b64"]),
            "size": result["size"],
        }

    def write_bytes(self, path: str, data: bytes) -> dict:
        payload = {"path": path, "content_b64": base64.b64encode(data).decode("ascii")}
        return self._post("/write", payload, timeout=self.command_timeout)

    def sysinfo(self) -> dict:
        return self._get("/system")


def make_backend():
    """Build the backend the environment asks for.

    ``COLAB_MODE`` forces ``local`` or ``remote``; ``auto`` (the default) uses
    the remote bridge when ``COLAB_BRIDGE_URL`` is set and the local backend
    otherwise.
    """
    command_timeout = int(os.getenv("COMMAND_TIMEOUT", str(core.DEFAULT_COMMAND_TIMEOUT)))
    bridge_url = os.getenv("COLAB_BRIDGE_URL", "").strip()
    mode = os.getenv("COLAB_MODE", "auto").strip().lower()

    if mode == "remote" or (mode == "auto" and bridge_url):
        return RemoteBridgeBackend(
            bridge_url,
            os.getenv("COLAB_BRIDGE_TOKEN", "").strip(),
            command_timeout=command_timeout,
            connect_timeout=float(os.getenv("CONNECT_TIMEOUT", "30")),
            verify_tls=os.getenv("COLAB_BRIDGE_VERIFY_TLS", "true").lower()
            not in ("0", "false", "no"),
        )
    return LocalBackend(command_timeout=command_timeout)
