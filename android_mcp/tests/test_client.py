import subprocess

import pytest

from android_client.client import ADBClient


def _make_client(monkeypatch, host=None, serial=None):
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    if host:
        monkeypatch.setenv("ADB_HOST", host)
    if serial:
        monkeypatch.setenv("ADB_SERIAL", serial)
    return ADBClient()


class TestADBClient:
    """Unit tests for ADBClient core methods."""

    def test_adb_builds_command(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client._adb("devices")

        mock_run.assert_called_once_with(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result == {"stdout": "hello", "stderr": "", "exit_code": 0}

    def test_adb_includes_serial(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch, serial="emulator-5554")
        client._adb("shell", "ls")

        mock_run.assert_called_once_with(
            ["adb", "-s", "emulator-5554", "shell", "ls"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_shell_delegates_to_adb(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "file.txt"
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client.shell("ls /sdcard")

        mock_run.assert_called_once_with(
            ["adb", "shell", "ls /sdcard"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result["stdout"] == "file.txt"

    def test_connect_with_host(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "connected to 192.168.1.10:5555"
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch, host="192.168.1.10")
        result = client.connect()

        mock_run.assert_called_once_with(
            ["adb", "connect", "192.168.1.10:5555"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "connected" in result["stdout"]

    def test_connect_without_host(self, mock_subprocess_run, monkeypatch):
        client = _make_client(monkeypatch)
        result = client.connect()

        mock_run, _ = mock_subprocess_run
        mock_run.assert_not_called()
        assert result["exit_code"] == 0

    def test_strips_stdout_and_stderr(self, mock_subprocess_run, monkeypatch):
        _, mock_result = mock_subprocess_run
        mock_result.stdout = "  output with spaces  \n"
        mock_result.stderr = "  warning  \n"
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client._adb("shell", "echo test")

        assert result["stdout"] == "output with spaces"
        assert result["stderr"] == "warning"


class TestDeviceInfo:
    """Unit tests for ADBClient.get_device_info."""

    def test_get_device_info_returns_all_fields(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        responses = iter([
            ("Pixel 6", "", 0),
            ("13", "", 0),
            ("33", "", 0),
            ("Physical size: 1080x2400", "", 0),
            ("  level: 85", "", 0),
        ])

        def side_effect(*args, **kwargs):
            stdout, stderr, rc = next(responses)
            mock_result.stdout = stdout
            mock_result.stderr = stderr
            mock_result.returncode = rc
            return mock_result

        mock_run.side_effect = side_effect

        client = _make_client(monkeypatch)
        info = client.get_device_info()

        assert info["model"] == "Pixel 6"
        assert info["android_version"] == "13"
        assert info["sdk_level"] == "33"
        assert "1080x2400" in info["resolution"]
        assert "85" in info["battery"]


class TestPushPull:
    """Unit tests for ADBClient.push and pull."""

    def test_push_calls_adb_push(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "1 file pushed."
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client.push("/local/file.txt", "/sdcard/file.txt")

        mock_run.assert_called_once_with(
            ["adb", "push", "/local/file.txt", "/sdcard/file.txt"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result["exit_code"] == 0

    def test_pull_calls_adb_pull(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "1 file pulled."
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client.pull("/sdcard/photo.jpg", "/local/photo.jpg")

        mock_run.assert_called_once_with(
            ["adb", "pull", "/sdcard/photo.jpg", "/local/photo.jpg"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result["exit_code"] == 0
