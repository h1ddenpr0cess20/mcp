import subprocess
from unittest.mock import MagicMock

from docker_shell_client import DockerShellClient


def result(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def test_execute_returns_command_result():
    manager = MagicMock(command_timeout=30)
    manager.exec.return_value = result(7, "out", "err")
    client = DockerShellClient(manager)
    assert client.execute("false") == {"stdout": "out", "stderr": "err", "exit_code": 7}
    command = manager.exec.call_args.args[0]
    assert command[-2:] == ["-lc", "false"]


def test_write_remote_passes_content_over_stdin():
    manager = MagicMock(command_timeout=30)
    manager.exec.side_effect = [result(stdout="hello"), result(stdout="5\n")]
    client = DockerShellClient(manager)
    assert client.write_remote("/tmp/a file", "hello") == {"path": "/tmp/a file", "size": 5}
    assert manager.exec.call_args_list[0].kwargs["input_text"] == "hello"


def test_list_remote_parses_find_records():
    manager = MagicMock(command_timeout=30)
    manager.exec.return_value = result(stdout="a.txt\x0012\x00f\x00644\x001700000000.5\x00docs\x004096\x00d\x00755\x001700000001.0\x00")
    entries = DockerShellClient(manager).list_remote("/workspace")
    assert entries[0] == {"name": "a.txt", "size": 12, "is_dir": False,
                          "permissions": "0o644", "modified": 1700000000.5}
    assert entries[1]["is_dir"] is True


def test_tilde_path_uses_container_home():
    manager = MagicMock(command_timeout=30)
    manager.exec.side_effect = [result(stdout="/root"), result(stdout="content")]
    content = DockerShellClient(manager).read_remote("~/note.txt")
    assert content == "content"
    assert manager.exec.call_args_list[-1].args[0] == ["cat", "--", "/root/note.txt"]
