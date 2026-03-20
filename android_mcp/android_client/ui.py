import shlex


class UIController:
    """UI interaction: tap, swipe, text input, key presses."""

    KEYCODES = {
        "home": "KEYCODE_HOME",
        "back": "KEYCODE_BACK",
        "menu": "KEYCODE_MENU",
        "power": "KEYCODE_POWER",
        "volume_up": "KEYCODE_VOLUME_UP",
        "volume_down": "KEYCODE_VOLUME_DOWN",
        "enter": "KEYCODE_ENTER",
        "tab": "KEYCODE_TAB",
        "delete": "KEYCODE_DEL",
        "camera": "KEYCODE_CAMERA",
        "search": "KEYCODE_SEARCH",
        "media_play_pause": "KEYCODE_MEDIA_PLAY_PAUSE",
        "media_next": "KEYCODE_MEDIA_NEXT",
        "media_previous": "KEYCODE_MEDIA_PREVIOUS",
        "dpad_up": "KEYCODE_DPAD_UP",
        "dpad_down": "KEYCODE_DPAD_DOWN",
        "dpad_left": "KEYCODE_DPAD_LEFT",
        "dpad_right": "KEYCODE_DPAD_RIGHT",
        "dpad_center": "KEYCODE_DPAD_CENTER",
        "app_switch": "KEYCODE_APP_SWITCH",
    }

    def __init__(self, adb_client):
        self._adb = adb_client

    def tap(self, x: int, y: int) -> dict:
        """Tap the screen at the given coordinates."""
        return self._adb.shell(f"input tap {x} {y}")

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> dict:
        """Swipe from one point to another."""
        return self._adb.shell(
            f"input swipe {x1} {y1} {x2} {y2} {duration_ms}"
        )

    def input_text(self, text: str) -> dict:
        """Type text into the currently focused field."""
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        return self._adb.shell(f"input text {shlex.quote(escaped)}")

    def press_key(self, key: str) -> dict:
        """Press a key by name or Android keycode.

        Accepts friendly names (home, back, volume_up, etc.) or raw
        KEYCODE_* values.
        """
        keycode = self.KEYCODES.get(key.lower(), key.upper())
        if not keycode.startswith("KEYCODE_"):
            keycode = f"KEYCODE_{keycode}"
        return self._adb.shell(f"input keyevent {keycode}")

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> dict:
        """Long press at coordinates (implemented as a zero-distance swipe)."""
        return self._adb.shell(
            f"input swipe {x} {y} {x} {y} {duration_ms}"
        )

    def dump_ui(self) -> dict:
        """Dump the current UI hierarchy as XML."""
        return self._adb.shell(
            "uiautomator dump /sdcard/ui.xml && cat /sdcard/ui.xml && rm /sdcard/ui.xml"
        )
