
from android_client.client import ADBClient
from android_client.ui import UIController


def _make_ui(monkeypatch, mock_subprocess_run):
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    client = ADBClient()
    return UIController(client)


class TestTap:
    """Unit tests for UIController.tap."""

    def test_tap_sends_input_command(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.tap(100, 200)

        mock_run.assert_called_once_with(
            ["adb", "shell", "input tap 100 200"],
            capture_output=True,
            text=True,
            timeout=10,
        )


class TestSwipe:
    """Unit tests for UIController.swipe."""

    def test_swipe_sends_coordinates(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.swipe(100, 200, 300, 400, 500)

        mock_run.assert_called_once_with(
            ["adb", "shell", "input swipe 100 200 300 400 500"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_swipe_default_duration(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.swipe(0, 0, 100, 100)

        args = mock_run.call_args[0][0]
        assert "300" in args[2]


class TestInputText:
    """Unit tests for UIController.input_text."""

    def test_input_text_escapes_spaces(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.input_text("hello world")

        args = mock_run.call_args[0][0]
        # Spaces should be replaced with %s
        assert "%s" in args[2]


class TestPressKey:
    """Unit tests for UIController.press_key."""

    def test_press_key_friendly_name(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.press_key("home")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_HOME" in args[2]

    def test_press_key_raw_keycode(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.press_key("KEYCODE_ENTER")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_ENTER" in args[2]

    def test_press_key_case_insensitive(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.press_key("BACK")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_BACK" in args[2]

    def test_press_key_unknown_adds_prefix(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.press_key("space")

        args = mock_run.call_args[0][0]
        assert "KEYCODE_SPACE" in args[2]


class TestLongPress:
    """Unit tests for UIController.long_press."""

    def test_long_press_uses_swipe(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        ui.long_press(500, 600, 2000)

        args = mock_run.call_args[0][0]
        assert "input swipe 500 600 500 600 2000" in args[2]


class TestDumpUI:
    """Unit tests for UIController.dump_ui."""

    def test_dump_ui_returns_xml(self, mock_subprocess_run, monkeypatch):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = '<?xml version="1.0" ?><hierarchy></hierarchy>'
        mock_result.stderr = ""
        mock_result.returncode = 0

        ui = _make_ui(monkeypatch, mock_subprocess_run)
        result = ui.dump_ui()

        assert "hierarchy" in result["stdout"]
