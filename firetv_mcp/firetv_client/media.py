import re
import time


FIRETV_KEYS = {
    # Navigation
    "up": "KEYCODE_DPAD_UP",
    "down": "KEYCODE_DPAD_DOWN",
    "left": "KEYCODE_DPAD_LEFT",
    "right": "KEYCODE_DPAD_RIGHT",
    "select": "KEYCODE_DPAD_CENTER",
    "back": "KEYCODE_BACK",
    "home": "KEYCODE_HOME",
    "menu": "KEYCODE_MENU",
    # Media
    "play": "KEYCODE_MEDIA_PLAY",
    "pause": "KEYCODE_MEDIA_PAUSE",
    "play_pause": "KEYCODE_MEDIA_PLAY_PAUSE",
    "stop": "KEYCODE_MEDIA_STOP",
    "next": "KEYCODE_MEDIA_NEXT",
    "previous": "KEYCODE_MEDIA_PREVIOUS",
    "rewind": "KEYCODE_MEDIA_REWIND",
    "fast_forward": "KEYCODE_MEDIA_FAST_FORWARD",
    # Volume
    "volume_up": "KEYCODE_VOLUME_UP",
    "volume_down": "KEYCODE_VOLUME_DOWN",
    "mute": "KEYCODE_VOLUME_MUTE",
    # Power
    "sleep": "KEYCODE_SLEEP",
    "wake": "KEYCODE_WAKEUP",
    "power": "KEYCODE_POWER",
    # Input
    "delete": "KEYCODE_DEL",
    "enter": "KEYCODE_ENTER",
    "tab": "KEYCODE_TAB",
    "search": "KEYCODE_SEARCH",
}


class MediaController:
    """D-pad navigation, media playback, volume, and now-playing info."""

    def __init__(self, adb_client):
        self._adb = adb_client

    def _key(self, key: str) -> dict:
        keycode = FIRETV_KEYS.get(key.lower(), key.upper())
        if not keycode.startswith("KEYCODE_"):
            keycode = f"KEYCODE_{keycode}"
        return self._adb.shell(f"input keyevent {keycode}")

    def navigate(self, direction: str) -> dict:
        """Press a D-pad or system key."""
        return self._key(direction)

    def navigate_repeat(self, direction: str, count: int = 1, delay_ms: int = 100) -> dict:
        """Press a D-pad key multiple times."""
        keycode = FIRETV_KEYS.get(direction.lower(), direction.upper())
        if not keycode.startswith("KEYCODE_"):
            keycode = f"KEYCODE_{keycode}"
        results = []
        for i in range(count):
            result = self._adb.shell(f"input keyevent {keycode}")
            results.append(result)
            if i < count - 1 and delay_ms > 0:
                time.sleep(delay_ms / 1000)
        last = results[-1] if results else {"stdout": "", "stderr": "", "exit_code": 0}
        return {**last, "count": count}

    def input_text(self, text: str) -> dict:
        """Type text into the focused input field."""
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        return self._adb.shell(f"input text '{escaped}'")

    def clear_input(self, count: int = 50) -> dict:
        """Clear the current input field by sending DEL key repeatedly."""
        keycodes = " ".join(["KEYCODE_DEL"] * count)
        return self._adb.shell(f"input keyevent {keycodes}")

    def media_control(self, action: str) -> dict:
        """Send a media playback command."""
        return self._key(action)

    def volume(self, action: str) -> dict:
        """Volume up, down, or mute."""
        return self._key(action)

    def set_volume(self, level: int) -> dict:
        """Set volume to a specific level (0–15 for Fire TV)."""
        level = max(0, min(15, level))
        # Get current volume first
        current_raw = self._adb.shell("dumpsys audio | grep 'STREAM_MUSIC' | head -1")["stdout"]
        current = 0
        match = re.search(r'(\d+)', current_raw)
        if match:
            current = int(match.group(1))
        diff = level - current
        key = "volume_up" if diff > 0 else "volume_down"
        for _ in range(abs(diff)):
            self._key(key)
        return {"stdout": f"volume set to {level}", "stderr": "", "exit_code": 0}

    def sleep(self) -> dict:
        """Put the Fire TV to sleep."""
        return self._key("sleep")

    def wake(self) -> dict:
        """Wake the Fire TV."""
        return self._key("wake")

    def now_playing(self) -> dict:
        """Return current media session info: app, title, artist, state, position."""
        result = self._adb.shell("dumpsys media_session")
        if result["exit_code"] != 0:
            return result

        raw = result["stdout"]
        info = {
            "app": "",
            "title": "",
            "artist": "",
            "album": "",
            "state": "unknown",
            "duration_ms": None,
            "position_ms": None,
        }

        # Package name
        m = re.search(r'package=([^\s,]+)', raw)
        if m:
            info["app"] = m.group(1)

        # Metadata fields
        for field, key in [("title", "title"), ("artist", "artist"), ("album", "album")]:
            m = re.search(rf'{field}=([^\n]+)', raw, re.IGNORECASE)
            if m:
                info[key] = m.group(1).strip()

        # Playback state
        if "state=PlaybackState {state=3" in raw:
            info["state"] = "playing"
        elif "state=PlaybackState {state=2" in raw:
            info["state"] = "paused"
        elif "state=PlaybackState {state=1" in raw:
            info["state"] = "stopped"
        elif "state=PlaybackState {state=6" in raw:
            info["state"] = "buffering"

        # Duration and position
        m = re.search(r'position=(\d+)', raw)
        if m:
            info["position_ms"] = int(m.group(1))
        m = re.search(r'duration=(\d+)', raw)
        if m:
            info["duration_ms"] = int(m.group(1))

        return info

    def get_notifications(self) -> dict:
        """Read active notifications."""
        return self._adb.shell("dumpsys notification --noredact | grep -A3 'NotificationRecord'")

    def dismiss_notifications(self) -> dict:
        """Dismiss all notifications."""
        return self._adb.shell("service call notification 1")

    def set_brightness(self, level: int) -> dict:
        """Set screen brightness (0–255)."""
        level = max(0, min(255, level))
        return self._adb.shell(f"settings put system screen_brightness {level}")

    def toggle_bluetooth(self, enabled: bool) -> dict:
        """Enable or disable Bluetooth."""
        # cmd bluetooth_manager works on Android 12+ / Fire OS 7+
        # Fall back to settings put global for older versions
        action = "enable" if enabled else "disable"
        result = self._adb.shell(f"cmd bluetooth_manager {action}")
        if result["exit_code"] != 0 or "Unknown" in result["stderr"]:
            val = "1" if enabled else "0"
            result = self._adb.shell(f"settings put global bluetooth_on {val}")
        return result
