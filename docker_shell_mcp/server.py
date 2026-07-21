import atexit
import os
import signal
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from docker_shell_client import ContainerManager, DockerShellClient, FileServer

load_dotenv()

_manager = ContainerManager()
_client = DockerShellClient(_manager)
_file_server = FileServer()
_file_server.start()
_manager.start_background_setup()
atexit.register(_manager.stop_container)


def _handle_signal(_signum, _frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_signal)
mcp = FastMCP("docker-shell")


@mcp.tool
def execute_command(command: str) -> dict:
    """Execute a Bash command in an isolated Docker container.

    Args:
        command: Bash command or pipeline to execute.

    Returns:
        Dict with stdout, stderr, and exit_code.
    """
    return _client.execute(command)


@mcp.tool
def list_directory(path: str = "~") -> list[dict]:
    """List files and directories in the sandbox.

    Args:
        path: Container directory path. Defaults to the container home.

    Returns:
        File entries with name, size, type, permissions, and modification time.
    """
    return _client.list_remote(path)


@mcp.tool
def read_file(path: str) -> str:
    """Read a text file from the sandbox.

    Args:
        path: Path inside the container.

    Returns:
        File contents.
    """
    return _client.read_remote(path)


@mcp.tool
def write_file(path: str, content: str) -> dict:
    """Create or overwrite a text file in the sandbox.

    Args:
        path: Destination path inside the container.
        content: Complete text content to write.

    Returns:
        Dict with path and size.
    """
    return _client.write_remote(path, content)


@mcp.tool
def upload_file(local_path: str, remote_path: str) -> dict:
    """Copy a local file into the sandbox.

    Args:
        local_path: Path on the MCP server host.
        remote_path: Destination path inside the container.

    Returns:
        Dict with remote_path and size.
    """
    return _client.upload(local_path, remote_path)


@mcp.tool
def download_file(remote_path: str, local_path: str) -> dict:
    """Copy a sandbox file to the MCP server host.

    Args:
        remote_path: Source path inside the container.
        local_path: Destination path on the MCP server host.

    Returns:
        Dict with local_path and size.
    """
    return _client.download(remote_path, local_path)


@mcp.tool
def get_system_info() -> dict:
    """Return hostname, uptime, kernel, memory, and disk details."""
    return _client.system_info()


@mcp.tool
def fetch_file(remote_path: str) -> dict:
    """Copy out a sandbox file and expose it through a local HTTP URL.

    Args:
        remote_path: Source path inside the container.

    Returns:
        File metadata and download URL.
    """
    filename = os.path.basename(remote_path)
    # Namespace by remote path so files with the same basename don't clobber
    # each other in files_dir.
    subdir = _file_server.files_dir / _file_server.make_file_id(remote_path)
    subdir.mkdir(parents=True, exist_ok=True)
    local_path = str(subdir / filename)
    result = _client.download(remote_path, local_path)
    return _file_server.register(local_path, filename, result["size"])


if __name__ == "__main__":
    if sys.stdin.isatty():
        from mcp_http_compat import serve_http

        serve_http(mcp, host="127.0.0.1", port=9620, path="/mcp")
    else:
        mcp.run()
