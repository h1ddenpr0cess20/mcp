from unittest.mock import MagicMock

from colab_shell_client import ColabClient, LocalBackend


def test_execute_delegates_to_backend():
    backend = MagicMock()
    backend.run.return_value = {"stdout": "ok", "stderr": "", "exit_code": 0}
    client = ColabClient(backend)
    assert client.execute("echo ok")["stdout"] == "ok"
    backend.run.assert_called_once_with("echo ok")


def test_read_remote_decodes_bytes():
    backend = MagicMock()
    backend.read_bytes.return_value = {"data": b"caf\xc3\xa9", "size": 5}
    assert ColabClient(backend).read_remote("/content/x") == "café"


def test_write_remote_encodes_utf8():
    backend = MagicMock()
    backend.write_bytes.return_value = {"path": "/content/x", "size": 5}
    result = ColabClient(backend).write_remote("/content/x", "café")
    assert result == {"path": "/content/x", "size": 5}
    assert backend.write_bytes.call_args.args[1] == "café".encode("utf-8")


def test_upload_reads_local_file(tmp_path):
    source = tmp_path / "data.bin"
    source.write_bytes(b"payload")
    backend = MagicMock()
    backend.write_bytes.return_value = {"path": "/content/data.bin", "size": 7}
    result = ColabClient(backend).upload(str(source), "/content/data.bin")
    assert result == {"remote_path": "/content/data.bin", "size": 7}
    assert backend.write_bytes.call_args.args == ("/content/data.bin", b"payload")


def test_download_writes_local_file(tmp_path):
    backend = MagicMock()
    backend.read_bytes.return_value = {"data": b"payload", "size": 7}
    dest = tmp_path / "nested" / "out.bin"
    result = ColabClient(backend).download("/content/out.bin", str(dest))
    assert result == {"local_path": str(dest), "size": 7}
    assert dest.read_bytes() == b"payload"


def test_local_backend_runs_real_command():
    client = ColabClient(LocalBackend(command_timeout=30))
    assert client.execute("echo hello")["stdout"].strip() == "hello"
