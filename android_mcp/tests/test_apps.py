import pytest

from android_client.apps import AppManager
from android_client.client import ADBClient


def _make_apps(monkeypatch, mock_subprocess_run):
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    client = ADBClient()
    return AppManager(client)


class TestInstallApk:
    """Unit tests for AppManager.install_apk."""

    def test_install_apk_calls_adb_install(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.install_apk("/path/to/app.apk")

        mock_run.assert_called_once_with(
            ["adb", "install", "-r", "/path/to/app.apk"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result["exit_code"] == 0

    def test_install_apk_without_replace(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.install_apk("/path/to/app.apk", replace=False)

        args = mock_run.call_args[0][0]
        assert "-r" not in args


class TestUninstallApp:
    """Unit tests for AppManager.uninstall_app."""

    def test_uninstall_calls_adb_uninstall(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.uninstall_app("com.example.app")

        mock_run.assert_called_once_with(
            ["adb", "uninstall", "com.example.app"],
            capture_output=True,
            text=True,
            timeout=10,
        )


class TestLaunchApp:
    """Unit tests for AppManager.launch_app."""

    def test_launch_uses_monkey(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Events injected: 1"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.launch_app("com.android.chrome")

        args = mock_run.call_args[0][0]
        assert "monkey" in args[2]
        assert "com.android.chrome" in args[2]


class TestStopApp:
    """Unit tests for AppManager.stop_app."""

    def test_stop_calls_force_stop(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.stop_app("com.example.app")

        args = mock_run.call_args[0][0]
        assert "am force-stop com.example.app" in args[2]


class TestListPackages:
    """Unit tests for AppManager.list_packages."""

    def test_list_packages_parses_output(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "package:com.android.chrome\npackage:com.android.settings\n"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.list_packages()

        assert result["count"] == 2
        assert "com.android.chrome" in result["packages"]
        assert "com.android.settings" in result["packages"]

    def test_list_packages_empty(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.list_packages()

        assert result["count"] == 0
        assert result["packages"] == []

    def test_list_packages_with_filter(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "package:com.android.chrome\n"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.list_packages("chrome")

        args = mock_run.call_args[0][0]
        assert "grep" in args[2]
        assert "chrome" in args[2]


class TestCurrentActivity:
    """Unit tests for AppManager.current_activity."""

    def test_current_activity_returns_result(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "mResumedActivity: ActivityRecord{abc com.android.launcher3/.Launcher}"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.current_activity()

        assert "Launcher" in result["stdout"]


class TestClearAppData:
    """Unit tests for AppManager.clear_app_data."""

    def test_clear_calls_pm_clear(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.clear_app_data("com.example.app")

        args = mock_run.call_args[0][0]
        assert "pm clear com.example.app" in args[2]
