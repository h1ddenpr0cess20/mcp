import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from colab_shell_client import ColabClient, FileServer, make_backend

load_dotenv()

_backend = make_backend()
_client = ColabClient(_backend)
_file_server = FileServer()
_file_server.start()

sys.stderr.write(f"[colab-shell] backend: {_backend.describe()}\n")
sys.stderr.flush()

mcp = FastMCP("colab-shell")


@mcp.tool
def execute_command(command: str) -> dict:
    """Execute a shell command in the Google Colab runtime (its built-in shell).

    This is Colab's own bash — the same environment as a `!command` notebook
    cell, including any attached GPU/TPU and preinstalled data-science stack.
    Use for installing packages (pip/apt), running scripts, compiling code,
    training or inference, and anything needing pipes, redirection, or other
    shell features.

    Args:
        command: Bash command or pipeline to run, e.g. "pip install numpy" or
            "python3 train.py | tail -n 20".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.execute(command)


@mcp.tool
def list_directory(path: str = "~") -> list[dict]:
    """List files and directories at the given path in the Colab runtime.

    Args:
        path: Directory path in Colab (default: "~", the home dir; content
            usually lives under "/content").

    Returns:
        List of file entries with name, size, is_dir, permissions, and modified.
    """
    return _client.list_remote(path)


@mcp.tool
def read_file(path: str) -> str:
    """Read the text contents of a file in the Colab runtime.

    Args:
        path: Path to the file in Colab, e.g. "/content/notebook_output.txt".

    Returns:
        File contents as a string.
    """
    return _client.read_remote(path)


@mcp.tool
def write_file(path: str, content: str) -> dict:
    """Write text content to a file in the Colab runtime, creating or overwriting it.

    For uploading a binary or existing local file use upload_file instead.
    Parent directories must exist; create them first with execute_command if needed.

    Args:
        path: Destination path in Colab, e.g. "/content/script.py".
        content: Text content to write. Replaces existing content entirely.

    Returns:
        Dict with path (str) and size (int).
    """
    return _client.write_remote(path, content)


@mcp.tool
def upload_file(local_path: str, remote_path: str) -> dict:
    """Upload a file from the MCP server host into the Colab runtime.

    Use for binary files or existing local files. For text you have in memory,
    use write_file instead. When the server runs inside Colab, "local" and
    "remote" are the same filesystem.

    Args:
        local_path: Absolute path on the MCP SERVER HOST, e.g. "/home/user/data.csv".
        remote_path: Destination path in COLAB, e.g. "/content/data.csv".

    Returns:
        Dict with remote_path (str) and size (int).
    """
    return _client.upload(local_path, remote_path)


@mcp.tool
def download_file(remote_path: str, local_path: str) -> dict:
    """Download a file from the Colab runtime to the MCP server host.

    Use to save a Colab file to a specific local path. To serve a file to a
    client via HTTP URL (e.g. a generated PDF), use fetch_file instead.

    Args:
        remote_path: Path in COLAB, e.g. "/content/output.zip".
        local_path: Destination path on the MCP SERVER HOST, e.g. "/tmp/output.zip".

    Returns:
        Dict with local_path (str) and size (int).
    """
    return _client.download(remote_path, local_path)


@mcp.tool
def get_system_info() -> dict:
    """Get hostname, uptime, kernel, memory, disk, and GPU details from Colab.

    Returns:
        Dict with system information fields, including the attached accelerator.
    """
    return _client.system_info()


@mcp.tool
def fetch_file(remote_path: str) -> dict:
    """Serve a Colab file to the client via an HTTP download URL.

    Use after Colab generates a document, image, model checkpoint, or archive
    that the client needs to download. To save to a local path instead, use
    download_file.

    Args:
        remote_path: Path to the file in COLAB, e.g. "/content/report.pdf".

    Returns:
        Dict with file_id, filename, size, mime_type, and url.
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
    host = os.getenv("COLAB_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("COLAB_MCP_PORT", "9630"))
    # Default to HTTP when launched directly in a terminal or the Colab
    # notebook (where smoketest connects over http://127.0.0.1:9630/mcp), and
    # to stdio when an MCP client spawns the server. COLAB_MCP_TRANSPORT
    # overrides the auto-detection ("http" or "stdio").
    transport = os.getenv("COLAB_MCP_TRANSPORT", "").strip().lower()
    if transport == "stdio" or (not transport and not sys.stdin.isatty()):
        mcp.run()
    else:
        mcp.run(transport="http", host=host, port=port, path="/mcp")
