import subprocess

import pytest

from firetv_client.client import ADBClient


def _make_client(monkeypatch, host=None, serial=None):
    monkeypatch.delenv("FIRETV_HOST", raising=False)
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    if host:
        monkeypatch.setenv("FIRETV_HOST", host)
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

    def test_connect_with_firetv_host(self, mock_subprocess_run, monkeypatch):
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

    def test_timeout_returns_error(self, mocker, monkeypatch):
        monkeypatch.delenv("FIRETV_HOST", raising=False)
        monkeypatch.delenv("ADB_HOST", raising=False)
        monkeypatch.delenv("ADB_SERIAL", raising=False)
        monkeypatch.setenv("ADB_TIMEOUT", "10")
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("adb", 10))

        client = ADBClient()
        result = client._adb("shell", "sleep 30")

        assert result["exit_code"] == 1
        assert "timed out" in result["stderr"]


class TestDeviceInfo:
    """Unit tests for ADBClient.get_device_info."""

    def test_get_device_info_returns_all_fields(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        responses = iter([
            ("Fire TV Stick 4K", "", 0),
            ("9", "", 0),
            ("28", "", 0),
            ("Physical size: 1920x1080", "", 0),
            ("  level: 100", "", 0),
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

        assert info["model"] == "Fire TV Stick 4K"
        assert info["android_version"] == "9"
        assert info["sdk_level"] == "28"
        assert "1920x1080" in info["resolution"]
        assert "100" in info["battery"]


class TestNetworkStorage:
    """Unit tests for network and storage info."""

    def test_get_network_info_returns_ssid_and_ip(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        responses = iter([
            ("mWifiInfo SSID: MyNetwork", "", 0),
            ("    inet 192.168.1.50/24", "", 0),
        ])

        def side_effect(*args, **kwargs):
            stdout, stderr, rc = next(responses)
            mock_result.stdout = stdout
            mock_result.stderr = stderr
            mock_result.returncode = rc
            return mock_result

        mock_run.side_effect = side_effect

        client = _make_client(monkeypatch)
        result = client.get_network_info()

        assert "ssid" in result
        assert "ip" in result

    def test_get_storage_info(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/block/dm-0  12G  8.0G  3.5G  70% /data"
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        result = client.get_storage_info()

        assert result["exit_code"] == 0
        assert "/data" in result["stdout"]


class TestReboot:
    """Unit tests for ADBClient.reboot."""

    def test_reboot_calls_adb_reboot(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        client = _make_client(monkeypatch)
        client.reboot()

        mock_run.assert_called_once_with(
            ["adb", "reboot"],
            capture_output=True,
            text=True,
            timeout=10,
        )


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
