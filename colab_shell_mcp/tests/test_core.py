import os

from colab_shell_client import core


def test_run_command_captures_streams_and_exit_code():
    result = core.run_command("printf out; printf err >&2; exit 3")
    assert result["stdout"] == "out"
    assert result["stderr"] == "err"
    assert result["exit_code"] == 3


def test_run_command_times_out_with_124():
    result = core.run_command("sleep 5", timeout=1)
    assert result["exit_code"] == 124
    assert "timed out" in result["stderr"]


def test_resolve_path_expands_home():
    assert core.resolve_path("~") == os.path.expanduser("~")
    assert core.resolve_path("~/x") == os.path.join(os.path.expanduser("~"), "x")
    assert core.resolve_path("/abs/path") == "/abs/path"


def test_write_then_read_bytes_roundtrips(tmp_path):
    target = tmp_path / "note.bin"
    written = core.write_bytes(str(target), b"\x00\x01hello")
    assert written == {"path": str(target), "size": 7}
    assert core.read_bytes(str(target)) == {"data": b"\x00\x01hello", "size": 7}


def test_list_directory_reports_entries(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "sub").mkdir()
    entries = {e["name"]: e for e in core.list_directory(str(tmp_path))}
    assert entries["a.txt"]["size"] == 2
    assert entries["a.txt"]["is_dir"] is False
    assert entries["sub"]["is_dir"] is True
    assert entries["a.txt"]["permissions"].startswith("0o")


def test_system_info_has_expected_fields():
    info = core.system_info()
    for key in ("hostname", "kernel", "uptime", "gpu"):
        assert key in info
