import os

from PIL import Image as PILImage

from firetv_client.client import ADBClient
from firetv_client.screen import ScreenCapture


def _make_screen(monkeypatch, mock_subprocess_run, tmp_path):
    monkeypatch.delenv("FIRETV_HOST", raising=False)
    monkeypatch.delenv("ADB_HOST", raising=False)
    monkeypatch.delenv("ADB_SERIAL", raising=False)
    monkeypatch.setenv("ADB_TIMEOUT", "10")
    monkeypatch.setenv("SCREENSHOT_DIR", str(tmp_path))
    client = ADBClient()
    return ScreenCapture(client)


def _create_test_png(path):
    """Create a small test PNG so _compress has a real file to process."""
    img = PILImage.new("RGB", (1920, 1080), color=(50, 50, 50))
    img.save(str(path), "PNG")


class TestScreenshot:
    """Unit tests for ScreenCapture.screenshot."""

    def test_screenshot_returns_compressed_jpeg(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        _create_test_png(tmp_path / "test.png")

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screenshot("test.png")

        assert result["path"] == str(tmp_path / "test.jpg")
        assert result["filename"] == "test.jpg"
        assert os.path.exists(result["path"])
        assert not os.path.exists(str(tmp_path / "test.png"))

    def test_screenshot_generates_timestamp_name(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)

        original_compress = screen._compress
        def mock_compress(png_path):
            _create_test_png(png_path)
            return original_compress(png_path)
        screen._compress = mock_compress

        result = screen.screenshot()

        assert result["filename"].startswith("screenshot_")
        assert result["filename"].endswith(".jpg")

    def test_screenshot_calls_screencap_pull_and_rm(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        _create_test_png(tmp_path / "capture.png")

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        screen.screenshot("capture.png")

        assert mock_run.call_count == 3

        first_args = mock_run.call_args_list[0][0][0]
        assert "screencap" in first_args[2]

        second_args = mock_run.call_args_list[1][0][0]
        assert second_args[1] == "pull"

        third_args = mock_run.call_args_list[2][0][0]
        assert "rm" in third_args[2]

    def test_screenshot_returns_error_on_capture_failure(
        self, mock_subprocess_run, monkeypatch, tmp_path
    ):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = "screencap failed"
        mock_result.returncode = 1

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screenshot("fail.png")

        assert "error" in result
        assert result["exit_code"] == 1


class TestScreenRecord:
    """Unit tests for ScreenCapture.screen_record."""

    def test_screen_record_calls_screenrecord_and_pull(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        screen.screen_record(10, "test.mp4")

        assert mock_run.call_count == 3

        first_args = mock_run.call_args_list[0][0][0]
        assert "screenrecord" in first_args[2]
        assert "--time-limit 10" in first_args[2]

        second_args = mock_run.call_args_list[1][0][0]
        assert second_args[1] == "pull"

    def test_screen_record_generates_timestamp_name(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screen_record()

        assert result["filename"].startswith("screenrecord_")
        assert result["filename"].endswith(".mp4")

    def test_screen_record_returns_error_on_failure(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = ""
        mock_result.stderr = "screenrecord failed"
        mock_result.returncode = 1

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screen_record(10, "fail.mp4")

        assert "error" in result
        assert result["exit_code"] == 1


class TestCompress:
    """Unit tests for ScreenCapture._compress."""

    def test_compress_converts_to_jpeg(self, mock_subprocess_run, monkeypatch, tmp_path):
        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        png_path = str(tmp_path / "img.png")
        _create_test_png(png_path)

        jpeg_path = screen._compress(png_path)

        assert jpeg_path.endswith(".jpg")
        assert os.path.exists(jpeg_path)
        assert not os.path.exists(png_path)

    def test_compress_resizes_large_images(self, mock_subprocess_run, monkeypatch, tmp_path):
        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        png_path = str(tmp_path / "big.png")
        _create_test_png(png_path)

        jpeg_path = screen._compress(png_path)

        img = PILImage.open(jpeg_path)
        assert max(img.size) <= ScreenCapture.MAX_DIMENSION


class TestScreenState:
    """Unit tests for ScreenCapture.screen_state."""

    def test_screen_on(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Display Power: state=ON"
        mock_result.returncode = 0

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screen_state()

        assert result["screen_on"] is True

    def test_screen_off(self, mock_subprocess_run, monkeypatch, tmp_path):
        mock_run, mock_result = mock_subprocess_run
        mock_result.stdout = "Display Power: state=OFF"
        mock_result.returncode = 0

        screen = _make_screen(monkeypatch, mock_subprocess_run, tmp_path)
        result = screen.screen_state()

        assert result["screen_on"] is False
