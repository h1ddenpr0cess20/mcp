import os
import posixpath
import shlex

from .container_manager import ContainerManager


class DockerShellClient:
    """Shell and file operations inside a Docker container."""

    def __init__(self, manager: ContainerManager | None = None):
        self.manager = manager or ContainerManager()

    def execute(self, command: str) -> dict:
        """Execute a Bash command and return stdout, stderr, and exit code."""
        timeout = self.manager.command_timeout
        result = self.manager.exec(
            ["timeout", "--signal=KILL", f"{timeout}s", "bash", "-lc", command]
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }

    def _home(self) -> str:
        result = self.manager.exec(["bash", "-lc", 'printf %s "$HOME"'], check=True)
        return result.stdout

    def _resolve_path(self, path: str) -> str:
        if path == "~":
            return self._home()
        if path.startswith("~/"):
            return posixpath.join(self._home(), path[2:])
        return path

    def upload(self, local_path: str, remote_path: str) -> dict:
        remote_path = self._resolve_path(remote_path)
        self.manager.copy_to(local_path, remote_path)
        result = self.manager.exec(["stat", "--format=%s", "--", remote_path], check=True)
        return {"remote_path": remote_path, "size": int(result.stdout.strip())}

    def download(self, remote_path: str, local_path: str) -> dict:
        remote_path = self._resolve_path(remote_path)
        self.manager.copy_from(remote_path, local_path)
        return {"local_path": local_path, "size": os.path.getsize(local_path)}

    def list_remote(self, path: str = "~") -> list[dict]:
        path = self._resolve_path(path)
        command = (
            f"find {shlex.quote(path)} -mindepth 1 -maxdepth 1 "
            "-printf '%f\\0%s\\0%y\\0%m\\0%T@\\0'"
        )
        result = self.manager.exec(["bash", "-lc", command], check=True)
        fields = result.stdout.split("\0")
        if fields and fields[-1] == "":
            fields.pop()
        entries = []
        for index in range(0, len(fields), 5):
            name, size, file_type, permissions, modified = fields[index:index + 5]
            entries.append({
                "name": name,
                "size": int(size),
                "is_dir": file_type == "d",
                "permissions": oct(int(permissions, 8)),
                "modified": float(modified),
            })
        return entries

    def read_remote(self, path: str) -> str:
        path = self._resolve_path(path)
        return self.manager.exec(["cat", "--", path], check=True).stdout

    def write_remote(self, path: str, content: str) -> dict:
        path = self._resolve_path(path)
        self.manager.exec(["tee", "--", path], input_text=content, check=True)
        result = self.manager.exec(["stat", "--format=%s", "--", path], check=True)
        return {"path": path, "size": int(result.stdout.strip())}

    def system_info(self) -> dict:
        script = """
printf 'hostname=%s\\n' "$(hostname)"
printf 'uptime=%s\\n' "$(uptime -p)"
printf 'kernel=%s\\n' "$(uname -r)"
free -h | awk '/^Mem:/ {print "mem_total=" $2; print "mem_used=" $3; print "mem_available=" $7}'
df -h / | awk 'NR==2 {print "disk_total=" $2; print "disk_used=" $3; print "disk_available=" $4; print "disk_use_pct=" $5}'
"""
        result = self.manager.exec(["bash", "-lc", script])
        if result.returncode != 0:
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
