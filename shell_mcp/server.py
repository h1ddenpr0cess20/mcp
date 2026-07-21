import atexit
import os
import signal
import sys
import threading

from dotenv import load_dotenv
from fastmcp import FastMCP

from shell_client import FileServer, ShellClient
from shell_client.vm_manager import VMManager

load_dotenv()

_vm = VMManager()
atexit.register(_vm.stop_vm)


def _handle_signal(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_signal)

# VM bring-up (create/restore/boot/wait-for-SSH) can take anywhere from
# seconds to tens of minutes. Do it on a background thread so the MCP
# transport starts answering the handshake immediately instead of looking
# hung/offline to the client for the whole duration; tool calls block on
# _get_client() until it's ready.
_client: ShellClient | None = None
_client_ready = threading.Event()
_client_error: Exception | None = None


def _bring_up_vm():
    global _client, _client_error
    try:
        conn = _vm.ensure_running()
        _client = ShellClient(host=conn["ssh_host"], port=conn["ssh_port"])
    except Exception as exc:
        _client_error = exc
    finally:
        _client_ready.set()


threading.Thread(target=_bring_up_vm, daemon=True, name="vm-bringup").start()


def _get_client() -> ShellClient:
    """Block until the sandbox VM is ready, then return the shell client.

    Only tool calls wait here — the MCP transport itself starts responding
    to the protocol handshake right away, without waiting on the VM.
    """
    _client_ready.wait()
    if _client_error is not None:
        raise RuntimeError(f"Sandbox failed to start: {_client_error}")
    return _client


_file_server = FileServer()

mcp = FastMCP("shell")

_file_server.start()


@mcp.tool
def execute_command(command: str) -> dict:
    """Execute a shell command in the sandbox (an isolated Linux VM).

    Use for installing packages, running scripts, compiling code, processing
    data, or anything requiring pipes, redirection, or shell features.

    Args:
        command: Bash command or pipeline to run, e.g. "ls -la /tmp" or
            "python3 script.py | grep error".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _get_client().execute(command)


@mcp.tool
def list_directory(path: str = "~") -> list[dict]:
    """List files and directories at the given path in the sandbox.

    Args:
        path: Directory path on the sandbox (default: "~", the home dir).

    Returns:
        List of file entries with name, size, is_dir, permissions, and modified.
    """
    return _get_client().list_remote(path)


@mcp.tool
def read_file(path: str) -> str:
    """Read the text contents of a file in the sandbox.

    Args:
        path: Absolute path to the file on the sandbox, e.g. "/home/ai-agent/script.py".

    Returns:
        File contents as a string.
    """
    return _get_client().read_remote(path)


@mcp.tool
def write_file(path: str, content: str) -> dict:
    """Write text content to a file in the sandbox, creating or overwriting it.

    For uploading a binary or existing local file use upload_file instead.
    Parent directories must exist; create them first with execute_command if needed.

    Args:
        path: Absolute destination path on the sandbox, e.g. "/home/ai-agent/script.py".
        content: Text content to write. Replaces existing content entirely.

    Returns:
        Dict with path (str) and size (int).
    """
    return _get_client().write_remote(path, content)


@mcp.tool
def upload_file(local_path: str, remote_path: str) -> dict:
    """Upload a file from the local host into the sandbox via SFTP.

    Use for binary files or existing local files. For text you have in memory,
    use write_file instead.

    Args:
        local_path: Absolute path on the LOCAL machine, e.g. "/home/user/data.csv".
        remote_path: Destination absolute path on the SANDBOX, e.g. "/home/ai-agent/data.csv".

    Returns:
        Dict with remote_path (str) and size (int).
    """
    return _get_client().upload(local_path, remote_path)


@mcp.tool
def download_file(remote_path: str, local_path: str) -> dict:
    """Download a file from the sandbox to the local machine via SFTP.

    Use to save a sandbox file to a specific local path. To serve a file to a
    client via HTTP URL (e.g. a generated PDF), use fetch_file instead.

    Args:
        remote_path: Absolute path on the SANDBOX, e.g. "/home/ai-agent/output.zip".
        local_path: Destination absolute path on the LOCAL machine, e.g. "/tmp/output.zip".

    Returns:
        Dict with local_path (str) and size (int).
    """
    return _get_client().download(remote_path, local_path)


@mcp.tool
def get_system_info() -> dict:
    """Get hostname, uptime, memory usage, and disk usage from the sandbox.

    Returns:
        Dict with system information fields.
    """
    return _get_client().system_info()


@mcp.tool
def fetch_file(remote_path: str) -> dict:
    """Serve a sandbox file to the client via an HTTP download URL.

    Use after the sandbox generates a document, image, or archive that the
    client needs to download (PDF, Word, spreadsheet, zip, etc.). To save to
    a local path instead, use download_file.

    Args:
        remote_path: Absolute path to the file on the SANDBOX, e.g. "/home/ai-agent/report.pdf".

    Returns:
        Dict with file_id, filename, size, mime_type, and url.
    """
    filename = os.path.basename(remote_path)
    local_path = str(_file_server.files_dir / filename)
    result = _get_client().download(remote_path, local_path)
    return _file_server.register(local_path, filename, result["size"])


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9610, path="/mcp")
    else:
        mcp.run()
