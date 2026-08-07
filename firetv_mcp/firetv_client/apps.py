
DEFAULT_APP_ALIASES = {
    # Streaming
    "netflix": "com.netflix.ninja",
    "prime": "com.amazon.avod.thirdpartyclient",
    "prime video": "com.amazon.avod.thirdpartyclient",
    "amazon": "com.amazon.avod.thirdpartyclient",
    "disney": "com.disney.disneyplus",
    "disney+": "com.disney.disneyplus",
    "hulu": "com.hulu.plus",
    "hbo": "com.hbo.hbonow",
    "hbo max": "com.hbo.hbonow",
    "max": "com.hbo.hbonow",
    "apple tv": "com.apple.atve.amazon.appletv",
    "apple": "com.apple.atve.amazon.appletv",
    "peacock": "com.peacocktv.peacockandroid",
    "paramount": "com.cbs.app",
    "paramount+": "com.cbs.app",
    "espn": "com.espn.score_center",
    "youtube": "com.google.android.youtube.tv",
    "youtube tv": "com.google.android.youtube.tvunplugged",
    "twitch": "tv.twitch.android.app",
    "pluto": "tv.pluto.android",
    "pluto tv": "tv.pluto.android",
    "tubi": "com.tubitv",
    "crunchyroll": "com.ellation.crunchyroll",
    "discovery+": "com.discovery.discoveryplus",
    "amc+": "com.amcplus.amcnetworks",
    # System & utilities
    "settings": "com.amazon.tv.settings.v2",
    "home": "com.amazon.firetv.home",
    "silk": "com.amazon.cloud9",
    "browser": "com.amazon.cloud9",
    "firetv": "com.amazon.firetv.home",
    "alexa": "com.amazon.dee.app",
    "music": "com.amazon.mp3",
    "amazon music": "com.amazon.mp3",
    "audible": "com.audible.application.amazon",
    "photos": "com.amazon.photos",
    "plex": "com.plexapp.android",
    "kodi": "org.xbmc.kodi",
    "vlc": "org.videolan.vlc",
}

_SETTINGS_SECTIONS = {
    "network": "com.amazon.tv.settings.v2/.tv.network.NetworkActivity",
    "display": "com.amazon.tv.settings.v2/.tv.display_sounds.DisplayAndSoundsActivity",
    "audio": "com.amazon.tv.settings.v2/.tv.display_sounds.DisplayAndSoundsActivity",
    "controllers": "com.amazon.tv.settings.v2/.tv.controllers_bluetooth_devices.ControllersAndBluetoothActivity",
    "bluetooth": "com.amazon.tv.settings.v2/.tv.controllers_bluetooth_devices.ControllersAndBluetoothActivity",
    "apps": "com.amazon.tv.settings.v2/.tv.applications.ApplicationsActivity",
    "account": "com.amazon.tv.settings.v2/.tv.my_account.MyAccountActivity",
    "device": "com.amazon.tv.settings.v2/.tv.device.DeviceActivity",
    "preferences": "com.amazon.tv.settings.v2/.tv.preferences.PreferencesActivity",
}


class AppManager:
    """App management with human-friendly aliases, deep linking, and sideloading."""

    def __init__(self, adb_client, extra_aliases: dict | None = None):
        self._adb = adb_client
        self._aliases = {**DEFAULT_APP_ALIASES}
        if extra_aliases:
            self._aliases.update({k.lower(): v for k, v in extra_aliases.items()})

    def _resolve(self, name: str) -> str:
        """Resolve a friendly name or package name to a package name."""
        return self._aliases.get(name.lower(), name)

    def launch_app(self, name: str) -> dict:
        """Launch an app by friendly name or package name."""
        package = self._resolve(name)
        # Fire TV apps use LEANBACK_LAUNCHER; fall back to standard LAUNCHER
        result = self._adb.shell(
            f"monkey -p {package} -c android.intent.category.LEANBACK_LAUNCHER 1"
        )
        if result["exit_code"] != 0 or "No activities found" in result["stdout"]:
            result = self._adb.shell(
                f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
            )
        return result

    def close_app(self, name: str) -> dict:
        """Force stop an app by friendly name or package name."""
        package = self._resolve(name)
        return self._adb.shell(f"am force-stop {package}")

    def list_apps(self, filter_text: str = "") -> dict:
        """List installed packages, optionally filtered by name."""
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

    def get_current_app(self) -> dict:
        """Get the currently focused app/activity."""
        return self._adb.shell(
            "dumpsys activity activities | grep mResumedActivity"
        )

    def open_url(self, url: str) -> dict:
        """Open a URL or deep link on the Fire TV."""
        return self._adb.shell(
            f"am start -a android.intent.action.VIEW -d '{url}'"
        )

    def search_content(self, query: str) -> dict:
        """Search Fire TV for content using the built-in search."""
        import time
        self._adb.shell("input keyevent KEYCODE_SEARCH")
        time.sleep(0.8)
        escaped = query.replace(" ", "%s").replace("'", "\\'")
        self._adb.shell(f"input text '{escaped}'")
        time.sleep(0.5)
        self._adb.shell("uiautomator dump /sdcard/ui.xml")
        ui = self._adb.shell("cat /sdcard/ui.xml")
        return {
            "query": query,
            "stdout": ui["stdout"],
            "stderr": ui["stderr"],
            "exit_code": ui["exit_code"],
        }

    def sideload(self, apk_path: str) -> dict:
        """Install an APK from the local host onto the Fire TV."""
        return self._adb._adb("install", "-r", apk_path, timeout=120)

    def uninstall_app(self, name: str) -> dict:
        """Uninstall an app by friendly name or package name."""
        package = self._resolve(name)
        return self._adb._adb("uninstall", package)

    def clear_app_data(self, name: str) -> dict:
        """Clear all data for an app (cache, databases, preferences)."""
        package = self._resolve(name)
        return self._adb.shell(f"pm clear {package}")

    def list_aliases(self) -> dict:
        """List all known app name aliases."""
        return {"aliases": self._aliases}

    def open_settings(self, section: str = "") -> dict:
        """Open Fire TV settings, optionally to a specific section.

        Valid sections: network, display, audio, controllers, apps, account, accessibility.
        """
        if section and section.lower() in _SETTINGS_SECTIONS:
            return self._adb.shell(
                f"am start -n {_SETTINGS_SECTIONS[section.lower()]}"
            )
        return self._adb.shell(
            "am start -n com.amazon.tv.settings.v2/.tv.MainSettingsActivity"
        )
