class AppManager:
    """App management: install, uninstall, launch, stop, list."""

    def __init__(self, adb_client):
        self._adb = adb_client

    def install_apk(self, apk_path: str, replace: bool = True) -> dict:
        """Install an APK from a host path."""
        args = ["install"]
        if replace:
            args.append("-r")
        args.append(apk_path)
        return self._adb._adb(*args)

    def uninstall_app(self, package: str) -> dict:
        """Uninstall an app by package name."""
        return self._adb._adb("uninstall", package)

    def launch_app(self, package: str) -> dict:
        """Launch an app by package name using monkey."""
        return self._adb.shell(
            f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        )

    def stop_app(self, package: str) -> dict:
        """Force stop an app by package name."""
        return self._adb.shell(f"am force-stop {package}")

    def list_packages(self, filter_text: str = "") -> dict:
        """List installed packages, optionally filtered."""
        cmd = "pm list packages"
        if filter_text:
            cmd += f" | grep -i {filter_text}"
        result = self._adb.shell(cmd)
        if result["exit_code"] == 0 and result["stdout"]:
            packages = [
                line.replace("package:", "").strip()
                for line in result["stdout"].splitlines()
                if line.strip()
            ]
            return {"packages": packages, "count": len(packages)}
        return {"packages": [], "count": 0, **result}

    def current_activity(self) -> dict:
        """Get the currently focused activity."""
        result = self._adb.shell(
            "dumpsys activity activities | grep mResumedActivity"
        )
        return result

    def clear_app_data(self, package: str) -> dict:
        """Clear all data for an app."""
        return self._adb.shell(f"pm clear {package}")
