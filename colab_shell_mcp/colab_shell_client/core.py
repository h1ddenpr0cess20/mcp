"""Stdlib-only shell and file primitives that run inside the Colab runtime.

These functions are the single source of truth for what "run a command in
Colab's shell" actually does. Both the in-process ``LocalBackend`` (used when
the MCP server runs inside the Colab VM) and the standalone ``bridge`` HTTP
server (used when the MCP server runs on your laptop and talks to a remote
Colab) call straight into here, so the two paths behave identically.

Nothing here imports a third-party package: the bridge has to run in a bare
Colab kernel with no ``pip install`` step, and Colab already ships CPython.
"""

import os
import platform
import shutil
import stat
import subprocess

DEFAULT_COMMAND_TIMEOUT = 1200


def resolve_path(path: str) -> str:
    """Expand ``~`` and ``~user`` against the Colab runtime's home directory.

    Deliberately does not confine the result to a sandbox root. This module
    exists to hand an authenticated operator the Colab runtime's own shell,
    and :func:`run_command` already grants strictly more access than any
    file read or write below, so a path allowlist here would buy nothing.
    """
    if path in ("", "~"):
        return os.path.expanduser("~")
    return os.path.expanduser(path)


def run_command(command: str, timeout: int = DEFAULT_COMMAND_TIMEOUT) -> dict:
    """Run a command through ``bash -lc`` in the Colab shell.

    Returns the same ``{stdout, stderr, exit_code}`` shape as the other shell
    MCP servers. A timeout maps to exit code 124, matching GNU ``timeout``.
    """
    try:
        proc = subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        note = f"Command timed out after {timeout} seconds"
        return {
            "stdout": stdout,
            "stderr": f"{stderr}\n{note}".strip(),
            "exit_code": 124,
        }
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
    }


def list_directory(path: str = "~") -> list[dict]:
    """List one directory level with name, size, is_dir, permissions, modified."""
    resolved = resolve_path(path)
    entries: list[dict] = []
    # Unrestricted paths are intentional here; see resolve_path.
    # codeql[py/path-injection]
    with os.scandir(resolved) as it:
        for entry in it:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            entries.append(
                {
                    "name": entry.name,
                    "size": info.st_size,
                    "is_dir": entry.is_dir(follow_symlinks=False),
                    "permissions": oct(stat.S_IMODE(info.st_mode)),
                    "modified": info.st_mtime,
                }
            )
    entries.sort(key=lambda item: item["name"])
    return entries


def read_bytes(path: str) -> dict:
    """Read a file's raw bytes. Returns ``{data, size}``."""
    resolved = resolve_path(path)
    # Unrestricted paths are intentional here; see resolve_path.
    # codeql[py/path-injection]
    with open(resolved, "rb") as handle:
        data = handle.read()
    return {"data": data, "size": len(data)}


def write_bytes(path: str, data: bytes) -> dict:
    """Write raw bytes to a file, creating or overwriting it. Returns ``{path, size}``."""
    resolved = resolve_path(path)
    # Unrestricted paths are intentional here; see resolve_path.
    # codeql[py/path-injection]
    with open(resolved, "wb") as handle:
        handle.write(data)
    return {"path": resolved, "size": len(data)}


def _uptime() -> str:
    try:
        with open("/proc/uptime", encoding="utf-8") as handle:
            seconds = float(handle.read().split()[0])
    except (OSError, ValueError):
        return "unknown"
    minutes, _ = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _memory() -> dict:
    fields = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
    except OSError:
        return {}

    def to_gib(key: str) -> str:
        raw = fields.get(key, "").split()
        if not raw:
            return "unknown"
        try:
            return f"{int(raw[0]) / (1024 * 1024):.1f}Gi"
        except ValueError:
            return "unknown"

    total = fields.get("MemTotal", "0 kB").split()[0]
    available = fields.get("MemAvailable", "0 kB").split()[0]
    used = "unknown"
    try:
        used = f"{(int(total) - int(available)) / (1024 * 1024):.1f}Gi"
    except ValueError:
        # /proc/meminfo held something non-numeric; ``used`` stays "unknown".
        pass
    return {
        "mem_total": to_gib("MemTotal"),
        "mem_available": to_gib("MemAvailable"),
        "mem_used": used,
    }


def _gpu() -> str:
    """Colab's headline feature; report the attached accelerator if present."""
    if not shutil.which("nvidia-smi"):
        return "none"
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    output = proc.stdout.strip()
    return output.replace("\n", "; ") if output else "none"


def system_info() -> dict:
    """Return hostname, uptime, kernel, memory, disk, and GPU details."""
    info = {
        "hostname": platform.node(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "uptime": _uptime(),
        "gpu": _gpu(),
    }
    info.update(_memory())
    try:
        usage = shutil.disk_usage("/")
        gib = 1024 ** 3
        info.update(
            {
                "disk_total": f"{usage.total / gib:.1f}Gi",
                "disk_used": f"{usage.used / gib:.1f}Gi",
                "disk_available": f"{usage.free / gib:.1f}Gi",
            }
        )
    except OSError:
        # Disk usage is a nice-to-have; the rest of the report still stands.
        pass
    return info
