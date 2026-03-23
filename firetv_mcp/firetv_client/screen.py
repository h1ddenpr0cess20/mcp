import os
from datetime import datetime

from PIL import Image


class ScreenCapture:
    """Screenshot capture, screen recording, and screen state."""

    MAX_DIMENSION = 1024
    JPEG_QUALITY = 60

    def __init__(self, adb_client):
        self._adb = adb_client
        self.screenshot_dir = os.getenv(
            "SCREENSHOT_DIR", "/tmp/firetv_screenshots"
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _compress(self, png_path: str) -> str:
        """Resize and convert a screenshot to JPEG for vision model consumption."""
        img = Image.open(png_path)
        w, h = img.size

        scale = min(self.MAX_DIMENSION / w, self.MAX_DIMENSION / h, 1.0)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        jpeg_path = png_path.rsplit(".", 1)[0] + ".jpg"
        img.convert("RGB").save(jpeg_path, "JPEG", quality=self.JPEG_QUALITY)
        os.remove(png_path)
        return jpeg_path

    def screenshot(self, filename: str = "") -> dict:
        """Capture the device screen, compress it, and return the path."""
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

        self._adb.shell(f"rm {remote_path}")

        jpeg_path = self._compress(local_path)
        jpeg_filename = os.path.basename(jpeg_path)

        return {"path": jpeg_path, "filename": jpeg_filename}

    def screen_record(self, duration_s: int = 30, filename: str = "") -> dict:
        """Record the screen for up to duration_s seconds and pull to local dir."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenrecord_{timestamp}.mp4"

        remote_path = f"/sdcard/{filename}"
        local_path = os.path.join(self.screenshot_dir, filename)

        rec_result = self._adb.shell(
            f"screenrecord --time-limit {duration_s} {remote_path}"
        )
        if rec_result["exit_code"] != 0:
            return {"error": rec_result["stderr"], "exit_code": rec_result["exit_code"]}

        pull_result = self._adb.pull(remote_path, local_path)
        if pull_result["exit_code"] != 0:
            return {"error": pull_result["stderr"], "exit_code": pull_result["exit_code"]}

        self._adb.shell(f"rm {remote_path}")

        size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
        return {"path": local_path, "filename": filename, "size": size}

    def screen_resolution(self) -> dict:
        """Get the screen resolution."""
        return self._adb.shell("wm size")

    def screen_density(self) -> dict:
        """Get the screen density (DPI)."""
        return self._adb.shell("wm density")

    def screen_state(self) -> dict:
        """Check if the screen is on or off."""
        result = self._adb.shell("dumpsys power | grep 'Display Power'")
        if result["exit_code"] == 0:
            is_on = "state=ON" in result["stdout"]
            return {"screen_on": is_on, "raw": result["stdout"]}
        return result
