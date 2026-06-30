import pytest

from firetv_client.apps import AppManager, DEFAULT_APP_ALIASES
from firetv_client.client import ADBClient


def _make_apps(monkeypatch, mock_subprocess_run, extra_aliases=None):
    monkeypatch.delenv("FIRETV_HOST", raising=False)
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    client = ADBClient()
    return AppManager(client, extra_aliases)


class TestAliasResolution:
    """Unit tests for AppManager alias resolution."""

    def test_resolve_friendly_name(self, mock_subprocess_run, monkeypatch):
        apps = _make_apps(monkeypatch, mock_subprocess_run)
        assert apps._resolve("netflix") == "com.netflix.ninja"

    def test_resolve_case_insensitive(self, mock_subprocess_run, monkeypatch):
        apps = _make_apps(monkeypatch, mock_subprocess_run)
        assert apps._resolve("Netflix") == "com.netflix.ninja"
        assert apps._resolve("NETFLIX") == "com.netflix.ninja"

    def test_resolve_unknown_returns_as_is(self, mock_subprocess_run, monkeypatch):
        apps = _make_apps(monkeypatch, mock_subprocess_run)
        assert apps._resolve("com.example.custom") == "com.example.custom"

    def test_extra_aliases_merged(self, mock_subprocess_run, monkeypatch):
        apps = _make_apps(monkeypatch, mock_subprocess_run, {"myapp": "com.example.myapp"})
        assert apps._resolve("myapp") == "com.example.myapp"

    def test_list_aliases_returns_dict(self, mock_subprocess_run, monkeypatch):
        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.list_aliases()
        assert "aliases" in result
        assert "netflix" in result["aliases"]


class TestLaunchApp:
    """Unit tests for AppManager.launch_app."""

    def test_launch_by_alias(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Events injected: 1"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.launch_app("netflix")

        args = mock_run.call_args[0][0]
        assert "com.netflix.ninja" in args[2]
        assert "monkey" in args[2]

    def test_launch_by_package_name(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Events injected: 1"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.launch_app("com.example.app")

        args = mock_run.call_args[0][0]
        assert "com.example.app" in args[2]


class TestCloseApp:
    """Unit tests for AppManager.close_app."""

    def test_close_by_alias(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.close_app("prime")

        args = mock_run.call_args[0][0]
        assert "am force-stop com.amazon.avod.thirdpartyclient" in args[2]


class TestListApps:
    """Unit tests for AppManager.list_apps."""

    def test_list_apps_parses_output(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "package:com.netflix.ninja\npackage:com.amazon.avod.thirdpartyclient\n"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        result = apps.list_apps()

        assert result["count"] == 2
        assert "com.netflix.ninja" in result["packages"]

    def test_list_apps_with_filter(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "package:com.netflix.ninja\n"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.list_apps("netflix")

        args = mock_run.call_args[0][0]
        assert "grep" in args[2]
        assert "netflix" in args[2]


class TestOpenUrl:
    """Unit tests for AppManager.open_url."""

    def test_open_url_uses_am_start(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.open_url("https://example.com")

        args = mock_run.call_args[0][0]
        assert "am start" in args[2]
        assert "https://example.com" in args[2]


class TestSideload:
    """Unit tests for AppManager.sideload."""

    def test_sideload_calls_adb_install(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.sideload("/tmp/app.apk")

        mock_run.assert_called_once_with(
            ["adb", "install", "-r", "/tmp/app.apk"],
            capture_output=True,
            text=True,
            timeout=120,
        )


class TestOpenSettings:
    """Unit tests for AppManager.open_settings."""

    def test_open_main_settings(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.open_settings()

        args = mock_run.call_args[0][0]
        assert "SettingsActivity" in args[2]

    def test_open_network_settings(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.open_settings("network")

        args = mock_run.call_args[0][0]
        assert "NetworkActivity" in args[2]

    def test_open_settings_case_insensitive(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.open_settings("AUDIO")

        args = mock_run.call_args[0][0]
        assert "DisplayAndSoundsActivity" in args[2]


class TestClearAppData:
    """Unit tests for AppManager.clear_app_data."""

    def test_clear_by_alias(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Success"
        mock_result.returncode = 0

        apps = _make_apps(monkeypatch, mock_subprocess_run)
        apps.clear_app_data("netflix")

        args = mock_run.call_args[0][0]
        assert "pm clear com.netflix.ninja" in args[2]
