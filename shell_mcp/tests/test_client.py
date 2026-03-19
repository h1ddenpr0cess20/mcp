import stat
from unittest.mock import MagicMock

import pytest

from shell_client.client import ShellClient


def _make_client(monkeypatch):
    monkeypatch.setenv("SSH_HOST", "test-host")
    monkeypatch.setenv("SSH_USER", "test-user")
    monkeypatch.setenv("SSH_PASSWORD", "test-pass")
    monkeypatch.delenv("SSH_KEY_PATH", raising=False)
    return ShellClient()


class TestShellClient:
    """Unit tests for ShellClient (mocked SSH)."""

    def test_execute_returns_stdout_stderr_exitcode(self, mock_ssh_client, monkeypatch):
        monkeypatch.setenv("SSH_HOST", "test-host")
        monkeypatch.setenv("SSH_USER", "test-user")
        monkeypatch.setenv("SSH_PASSWORD", "test-pass")

        _, mock_stdout, mock_stderr = mock_ssh_client.exec_command.return_value
        mock_stdout.read.return_value = b"hello\n"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        client = ShellClient()
        result = client.execute("echo hello")

        assert result["stdout"] == "hello\n"
        assert result["stderr"] == ""
        assert result["exit_code"] == 0

    def test_connect_uses_key_when_provided(self, mock_ssh_client, monkeypatch):
        monkeypatch.setenv("SSH_HOST", "test-host")
        monkeypatch.setenv("SSH_USER", "test-user")
        monkeypatch.setenv("SSH_KEY_PATH", "~/.ssh/test_key")

        client = ShellClient()
        client.connect()

        call_kwargs = mock_ssh_client.connect.call_args[1]
        assert "key_filename" in call_kwargs
        assert "password" not in call_kwargs

    def test_connect_uses_password_when_no_key(self, mock_ssh_client, monkeypatch):
        monkeypatch.setenv("SSH_HOST", "test-host")
        monkeypatch.setenv("SSH_USER", "test-user")
        monkeypatch.setenv("SSH_PASSWORD", "secret")
        monkeypatch.delenv("SSH_KEY_PATH", raising=False)

        client = ShellClient()
        client.connect()

        call_kwargs = mock_ssh_client.connect.call_args[1]
        assert call_kwargs["password"] == "secret"
        assert "key_filename" not in call_kwargs

    def test_disconnect_closes_client(self, mock_ssh_client, monkeypatch):
        monkeypatch.setenv("SSH_HOST", "test-host")
        monkeypatch.setenv("SSH_USER", "test-user")
        monkeypatch.setenv("SSH_PASSWORD", "test-pass")

        client = ShellClient()
        client.connect()
        client.disconnect()

        mock_ssh_client.close.assert_called_once()
        assert client._client is None

    def test_reconnects_when_transport_inactive(self, mock_ssh_client, monkeypatch):
        monkeypatch.setenv("SSH_HOST", "test-host")
        monkeypatch.setenv("SSH_USER", "test-user")
        monkeypatch.setenv("SSH_PASSWORD", "test-pass")

        mock_transport = mock_ssh_client.get_transport.return_value
        mock_transport.is_active.return_value = False

        client = ShellClient()
        client.execute("ls")

        assert mock_ssh_client.connect.call_count >= 1


class TestSystemInfo:
    """Unit tests for ShellClient.system_info."""

    def test_parses_system_info(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        _, mock_stdout, mock_stderr = mock_ssh_client.exec_command.return_value
        mock_stdout.read.return_value = (
            b"HOSTNAME=ai-sandbox\n"
            b"UPTIME=up 2 hours, 14 minutes\n"
            b"KERNEL=6.1.0-18-amd64\n"
            b"MEM_TOTAL=3.8Gi MEM_USED=1.2Gi MEM_AVAILABLE=2.4Gi\n"
            b"DISK_TOTAL=30G DISK_USED=5.2G DISK_AVAILABLE=23G DISK_USE_PCT=19%\n"
        )
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        info = client.system_info()

        assert info["hostname"] == "ai-sandbox"
        assert info["kernel"] == "6.1.0-18-amd64"
        assert info["mem_total"] == "3.8Gi"
        assert info["disk_use_pct"] == "19%"

    def test_returns_raw_result_on_failure(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        _, mock_stdout, mock_stderr = mock_ssh_client.exec_command.return_value
        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"command not found"
        mock_stdout.channel.recv_exit_status.return_value = 127

        result = client.system_info()

        assert result["exit_code"] == 127
        assert result["stderr"] == "command not found"


class TestSFTPUpload:
    """Unit tests for ShellClient.upload."""

    def test_upload_returns_remote_path_and_size(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.stat.return_value = MagicMock(st_size=1024)

        result = client.upload("/local/file.txt", "/remote/file.txt")

        mock_sftp.put.assert_called_once_with("/local/file.txt", "/remote/file.txt")
        assert result == {"remote_path": "/remote/file.txt", "size": 1024}

    def test_upload_closes_sftp_on_success(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.stat.return_value = MagicMock(st_size=0)

        client.upload("/local/a", "/remote/a")

        mock_sftp.close.assert_called_once()

    def test_upload_closes_sftp_on_error(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.put.side_effect = IOError("upload failed")

        with pytest.raises(IOError):
            client.upload("/local/a", "/remote/a")

        mock_sftp.close.assert_called_once()


class TestSFTPDownload:
    """Unit tests for ShellClient.download."""

    def test_download_returns_local_path_and_size(self, mock_ssh_client, monkeypatch, tmp_path):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        local_file = tmp_path / "downloaded.txt"
        local_file.write_bytes(b"hello world")

        result = client.download("/remote/file.txt", str(local_file))

        mock_sftp.get.assert_called_once_with("/remote/file.txt", str(local_file))
        assert result == {"local_path": str(local_file), "size": 11}

    def test_download_closes_sftp_on_success(self, mock_ssh_client, monkeypatch, tmp_path):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        local_file = tmp_path / "f.txt"
        local_file.write_bytes(b"x")

        client.download("/remote/f.txt", str(local_file))

        mock_sftp.close.assert_called_once()

    def test_download_closes_sftp_on_error(self, mock_ssh_client, monkeypatch, tmp_path):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.get.side_effect = IOError("not found")

        with pytest.raises(IOError):
            client.download("/remote/missing.txt", str(tmp_path / "out.txt"))

        mock_sftp.close.assert_called_once()


class TestSFTPListRemote:
    """Unit tests for ShellClient.list_remote."""

    def test_list_remote_returns_entries(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.normalize.return_value = "/home/user"

        attr_file = MagicMock()
        attr_file.filename = "file.txt"
        attr_file.st_size = 512
        attr_file.st_mode = stat.S_IFREG | 0o644
        attr_file.st_mtime = 1700000000.0

        attr_dir = MagicMock()
        attr_dir.filename = "subdir"
        attr_dir.st_size = 4096
        attr_dir.st_mode = stat.S_IFDIR | 0o755
        attr_dir.st_mtime = 1700000001.0

        mock_sftp.listdir_attr.return_value = [attr_file, attr_dir]

        entries = client.list_remote("~")

        assert len(entries) == 2
        file_entry = next(e for e in entries if e["name"] == "file.txt")
        dir_entry = next(e for e in entries if e["name"] == "subdir")
        assert file_entry["is_dir"] is False
        assert file_entry["size"] == 512
        assert dir_entry["is_dir"] is True
        assert dir_entry["permissions"] == oct(0o755)

    def test_list_remote_resolves_tilde(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.normalize.return_value = "/home/user"
        mock_sftp.listdir_attr.return_value = []

        client.list_remote("~")

        mock_sftp.listdir_attr.assert_called_once_with("/home/user")

    def test_list_remote_resolves_tilde_subpath(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.normalize.return_value = "/home/user"
        mock_sftp.listdir_attr.return_value = []

        client.list_remote("~/docs")

        mock_sftp.listdir_attr.assert_called_once_with("/home/user/docs")

    def test_list_remote_absolute_path_not_modified(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.listdir_attr.return_value = []

        client.list_remote("/var/log")

        mock_sftp.listdir_attr.assert_called_once_with("/var/log")

    def test_list_remote_closes_sftp(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        mock_sftp.normalize.return_value = "/home/user"
        mock_sftp.listdir_attr.return_value = []

        client.list_remote("~")

        mock_sftp.close.assert_called_once()


class TestSFTPReadRemote:
    """Unit tests for ShellClient.read_remote."""

    def test_read_remote_returns_content(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = b"file contents"
        mock_sftp.open.return_value = mock_file

        content = client.read_remote("/remote/file.txt")

        assert content == "file contents"
        mock_sftp.open.assert_called_once_with("/remote/file.txt", "r")

    def test_read_remote_closes_sftp(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = b""
        mock_sftp.open.return_value = mock_file

        client.read_remote("/remote/file.txt")

        mock_sftp.close.assert_called_once()


class TestSFTPWriteRemote:
    """Unit tests for ShellClient.write_remote."""

    def test_write_remote_returns_path_and_size(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_sftp.open.return_value = mock_file
        mock_sftp.stat.return_value = MagicMock(st_size=42)

        result = client.write_remote("/remote/out.txt", "hello")

        assert result == {"path": "/remote/out.txt", "size": 42}
        mock_file.write.assert_called_once_with("hello")

    def test_write_remote_closes_sftp(self, mock_ssh_client, monkeypatch):
        client = _make_client(monkeypatch)
        mock_sftp = MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_sftp.open.return_value = mock_file
        mock_sftp.stat.return_value = MagicMock(st_size=0)

        client.write_remote("/remote/out.txt", "data")

        mock_sftp.close.assert_called_once()
