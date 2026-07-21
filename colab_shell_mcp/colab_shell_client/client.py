"""Tool-facing shell and file operations for the Colab runtime.

``ColabClient`` presents the exact same method surface as the SSH, VirtualBox,
and Docker shell clients in this collection (``execute``, ``list_remote``,
``read_remote``, ``write_remote``, ``upload``, ``download``, ``system_info``),
so the shared ``mcp-shell-coding-agent`` skill and any client tooling work
against it unchanged. All the real work is delegated to a backend.
"""

import os


class ColabClient:
    """Shell and file operations against a Colab runtime via a backend."""

    def __init__(self, backend):
        self.backend = backend

    def execute(self, command: str) -> dict:
        """Run a command and return stdout, stderr, and exit_code."""
        return self.backend.run(command)

    def list_remote(self, path: str = "~") -> list[dict]:
        return self.backend.list_dir(path)

    def read_remote(self, path: str) -> str:
        data = self.backend.read_bytes(path)["data"]
        return data.decode("utf-8", "replace")

    def write_remote(self, path: str, content: str) -> dict:
        return self.backend.write_bytes(path, content.encode("utf-8"))

    def upload(self, local_path: str, remote_path: str) -> dict:
        with open(local_path, "rb") as handle:
            data = handle.read()
        result = self.backend.write_bytes(remote_path, data)
        return {"remote_path": result["path"], "size": result["size"]}

    def download(self, remote_path: str, local_path: str) -> dict:
        data = self.backend.read_bytes(remote_path)["data"]
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        with open(local_path, "wb") as handle:
            handle.write(data)
        return {"local_path": local_path, "size": len(data)}

    def system_info(self) -> dict:
        return self.backend.sysinfo()
