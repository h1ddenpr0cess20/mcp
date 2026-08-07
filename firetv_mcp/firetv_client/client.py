import os
import subprocess


class ADBClient:
    """ADB client that shells out to the adb CLI."""

    def __init__(self, host=None, port=None, serial=None):
        self.host = host or os.getenv("FIRETV_HOST") or os.getenv("ADB_HOST")
        self.port = int(port or os.getenv("FIRETV_PORT") or os.getenv("ADB_PORT", 5555))
        self.serial = serial or os.getenv("ADB_SERIAL")
        self.timeout = int(os.getenv("ADB_TIMEOUT", 10))

    def _adb(self, *args, timeout=None) -> dict:
        """Run an adb command and return stdout, stderr, exit_code."""
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout or self.timeout
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "adb command timed out", "exit_code": 1}

    def connect(self) -> dict:
        """Connect to a device over WiFi ADB.

        If no host is configured this returns immediately without touching the
        network — run the ``discover_device`` tool (``_autodiscover``) to scan.
        """
        if self.host:
            return self._adb("connect", f"{self.host}:{self.port}")
        return {
            "stdout": "no host configured — set FIRETV_HOST or run discover_device",
            "stderr": "",
            "exit_code": 0,
        }

    def _autodiscover(self) -> dict:
        """Try to find and connect to a Fire TV via mDNS, then network scan."""
        # Try adb mdns (requires ADB 30+)
        mdns = self._adb("mdns", "services")
        if mdns["exit_code"] == 0 and mdns["stdout"]:
            for line in mdns["stdout"].splitlines():
                if "adb" in line.lower() or "android" in line.lower() or "amazon" in line.lower():
                    parts = line.split()
                    # Format: <name> <type> <address:port>
                    for part in parts:
                        if ":" in part and not part.startswith("_"):
                            result = self._adb("connect", part)
                            if result["exit_code"] == 0 and "connected" in result["stdout"].lower():
                                return result

        # Fall back: scan subnet for port 5555
        import socket
        import concurrent.futures

        gateway = self._get_gateway()
        if not gateway:
            return {"stdout": "no device found — set FIRETV_HOST in .env", "stderr": "", "exit_code": 1}

        subnet = ".".join(gateway.split(".")[:3])

        def try_connect(ip):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex((ip, 5555)) == 0:
                    s.close()
                    r = self._adb("connect", f"{ip}:5555")
                    if r["exit_code"] == 0 and "connected" in r["stdout"].lower():
                        return r
            except Exception:
                # This IP is only a candidate from the subnet sweep; an unreachable
                # host or a refused ADB handshake just means it is not the device.
                pass
            return None

        ips = [f"{subnet}.{i}" for i in range(1, 255)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
            for result in ex.map(try_connect, ips):
                if result:
                    return result

        return {"stdout": "no Fire TV found on network — set FIRETV_HOST in .env", "stderr": "", "exit_code": 1}

    def _get_gateway(self) -> str | None:
        """Get the default gateway IP."""
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5
            )
            for part in result.stdout.split():
                if part.count(".") == 3:
                    return part
        except Exception:
            # No default route, no `ip` binary, or unparseable output -- the
            # caller falls back to an explicitly configured address.
            pass
        return None

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

    def get_network_info(self) -> dict:
        """Get WiFi connection info: SSID and IP address."""
        ssid = self.shell("dumpsys wifi | grep 'mWifiInfo'")["stdout"]
        ip = self.shell("ip addr show wlan0 | grep 'inet '")["stdout"]
        return {"ssid": ssid, "ip": ip}

    def get_storage_info(self) -> dict:
        """Get internal storage usage."""
        return self.shell("df /data")

    def reboot(self) -> dict:
        """Reboot the Fire TV device."""
        return self._adb("reboot")

    def push(self, local_path: str, remote_path: str) -> dict:
        """Push a file from host to device."""
        return self._adb("push", local_path, remote_path)

    def pull(self, remote_path: str, local_path: str) -> dict:
        """Pull a file from device to host."""
        return self._adb("pull", remote_path, local_path)
