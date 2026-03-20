import os
from datetime import datetime

from PIL import Image


class ScreenCapture:
    """Screenshot capture and screen information."""

    MAX_DIMENSION = 1024
    JPEG_QUALITY = 60

    def __init__(self, adb_client):
        self._adb = adb_client
        self.screenshot_dir = os.getenv(
            "SCREENSHOT_DIR", "/tmp/android_screenshots"
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _compress(self, png_path: str) -> str:
        """Resize and convert a screenshot to JPEG for vision model consumption."""
        img = Image.open(png_path)
        w, h = img.size

        # Scale down preserving aspect ratio
        scale = min(self.MAX_DIMENSION / w, self.MAX_DIMENSION / h, 1.0)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        jpeg_path = png_path.rsplit(".", 1)[0] + ".jpg"
        img.convert("RGB").save(jpeg_path, "JPEG", quality=self.JPEG_QUALITY)
        os.remove(png_path)
        return jpeg_path

    def screenshot(self, filename: str = "") -> dict:
        """Capture the device screen, compress it, and return the path.

        The screenshot is resized and converted to JPEG to keep the
        payload small enough for vision model consumption.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        remote_path = f"/sdcard/{filename}"
        local_path = os.path.join(self.screenshot_dir, filename)

        cap_result = self._adb.shell(f"screencap -p {remote_path}")
        if cap_result["exit_code"] != 0:
            return {"error": cap_result["stderr"], "exit_code": cap_result["exit_code"]}

        pull_result = self._adb.pull(remote_path, local_path)
        if pull_result["exit_code"] != 0:
            return {"error": pull_result["stderr"], "exit_code": pull_result["exit_code"]}

        # Clean up remote file
        self._adb.shell(f"rm {remote_path}")

        # Compress for vision model
        jpeg_path = self._compress(local_path)
        jpeg_filename = os.path.basename(jpeg_path)

        return {"path": jpeg_path, "filename": jpeg_filename}

    def screen_resolution(self) -> dict:
        """Get the screen resolution."""
        result = self._adb.shell("wm size")
        return result

    def screen_density(self) -> dict:
        """Get the screen density (DPI)."""
        result = self._adb.shell("wm density")
        return result

    def screen_state(self) -> dict:
        """Check if the screen is on or off."""
        result = self._adb.shell(
            "dumpsys power | grep 'Display Power'"
        )
        if result["exit_code"] == 0:
            is_on = "state=ON" in result["stdout"]
            return {"screen_on": is_on, "raw": result["stdout"]}
        return result

    def wake_screen(self) -> dict:
        """Wake the screen if it's off."""
        state = self.screen_state()
        if isinstance(state, dict) and not state.get("screen_on", True):
            return self._adb.shell("input keyevent KEYCODE_WAKEUP")
        return {"stdout": "screen already on", "stderr": "", "exit_code": 0}
