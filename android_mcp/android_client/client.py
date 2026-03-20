import os
import shlex
import subprocess


class ADBClient:
    """ADB client that shells out to the adb CLI."""

    def __init__(self, host=None, port=None, serial=None):
        self.host = host or os.getenv("ADB_HOST")
        self.port = int(port or os.getenv("ADB_PORT", 5555))
        self.serial = serial or os.getenv("ADB_SERIAL")
        self.timeout = int(os.getenv("ADB_TIMEOUT", 30))

    def _adb(self, *args, timeout=None) -> dict:
        """Run an adb command and return stdout, stderr, exit_code."""
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout or self.timeout
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
        }

    def connect(self) -> dict:
        """Connect to a device over WiFi ADB."""
        if self.host:
            return self._adb("connect", f"{self.host}:{self.port}")
        return {"stdout": "no host configured, using USB/emulator", "stderr": "", "exit_code": 0}

    def shell(self, command: str) -> dict:
        """Run a shell command on the device."""
        return self._adb("shell", command)

    def get_device_info(self) -> dict:
        """Get device model, Android version, SDK level, and screen resolution."""
        model = self.shell("getprop ro.product.model")["stdout"]
        android_version = self.shell("getprop ro.build.version.release")["stdout"]
        sdk = self.shell("getprop ro.build.version.sdk")["stdout"]
        resolution = self.shell("wm size")["stdout"]
        battery = self.shell("dumpsys battery | grep level")["stdout"]
        return {
            "model": model,
            "android_version": android_version,
            "sdk_level": sdk,
            "resolution": resolution,
            "battery": battery,
        }

    def push(self, local_path: str, remote_path: str) -> dict:
        """Push a file from host to device."""
        return self._adb("push", local_path, remote_path)

    def pull(self, remote_path: str, local_path: str) -> dict:
        """Pull a file from device to host."""
        return self._adb("pull", remote_path, local_path)
