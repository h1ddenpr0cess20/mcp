import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from firetv_client import ADBClient, AppManager, FileServer, MediaController, ScreenCapture

load_dotenv()

_client = ADBClient()
_client.connect()
_media = MediaController(_client)
_apps = AppManager(_client)
_screen = ScreenCapture(_client)
_file_server = FileServer()
_file_server.start()

mcp = FastMCP("firetv")


@mcp.tool
def shell(command: str) -> dict:
    """Run an adb shell command on the Fire TV.

    Use for direct device interaction: checking files, querying properties,
    managing settings, or anything not covered by other tools.

    Args:
        command: Shell command to run on the device.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.shell(command)


@mcp.tool
def navigate(direction: str) -> dict:
    """Press a D-pad or system key on the Fire TV remote.

    Common directions: up, down, left, right, select (confirm), back, home, menu.
    Media keys: play, pause, play_pause, stop, next, previous, rewind, fast_forward.
    Volume: volume_up, volume_down, mute.
    Power: sleep, wake.

    Args:
        direction: Key name, e.g. "up", "select", "back", "home", "play".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.navigate(direction)


@mcp.tool
def navigate_repeat(direction: str, count: int = 1, delay_ms: int = 100) -> dict:
    """Press a D-pad key multiple times.

    Useful for scrolling through lists or moving focus several positions.

    Args:
        direction: Key name, e.g. "down", "right".
        count: Number of times to press (default 1).
        delay_ms: Delay between presses in milliseconds (default 100).

    Returns:
        Dict with stdout (str), stderr (str), exit_code (int), and count (int).
    """
    return _media.navigate_repeat(direction, count, delay_ms)


@mcp.tool
def input_text(text: str) -> dict:
    """Type text into the currently focused input field.

    Focus a search box or text field first by navigating to it and pressing select.

    Args:
        text: Text to type. Spaces and apostrophes are escaped automatically.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.input_text(text)


@mcp.tool
def clear_input(count: int = 50) -> dict:
    """Clear the current input field by sending DEL key repeatedly.

    Args:
        count: Number of delete keypresses (default 50).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.clear_input(count)


@mcp.tool
def media_control(action: str) -> dict:
    """Send a media playback command.

    Actions: play, pause, play_pause, stop, next, previous, rewind, fast_forward.

    Args:
        action: Media action name.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.media_control(action)


@mcp.tool
def volume(action: str) -> dict:
    """Adjust volume up, down, or mute.

    Args:
        action: One of "volume_up", "volume_down", or "mute".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.volume(action)


@mcp.tool
def set_volume(level: int) -> dict:
    """Set volume to a specific level (0-15 for Fire TV).

    Args:
        level: Volume level from 0 (silent) to 15 (max).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.set_volume(level)


@mcp.tool
def now_playing() -> dict:
    """Get current media session info: app, title, artist, state, position.

    Returns:
        Dict with app (str), title (str), artist (str), album (str),
        state (str: playing/paused/stopped/buffering/unknown),
        duration_ms (int or None), position_ms (int or None).
    """
    return _media.now_playing()


@mcp.tool
def launch_app(name: str) -> dict:
    """Launch an app by friendly name or package name.

    Common names: netflix, prime, disney+, hulu, hbo max, youtube, twitch,
    peacock, paramount+, tubi, pluto tv, plex, kodi. Use list_app_aliases
    for the full list.

    Args:
        name: App name (alias or package name like "com.netflix.ninja").

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.launch_app(name)


@mcp.tool
def close_app(name: str) -> dict:
    """Force stop an app by friendly name or package name.

    Args:
        name: App name (alias or package name).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.close_app(name)


@mcp.tool
def list_apps(filter_text: str = "") -> dict:
    """List installed packages, optionally filtered by name.

    Args:
        filter_text: Optional text to filter package names (case-insensitive).

    Returns:
        Dict with packages (list of str) and count (int).
    """
    return _apps.list_apps(filter_text)


@mcp.tool
def get_current_app() -> dict:
    """Get the currently focused app and activity.

    Returns:
        Dict with stdout (str) showing the resumed activity.
    """
    return _apps.get_current_app()


@mcp.tool
def open_url(url: str) -> dict:
    """Open a URL or deep link on the Fire TV.

    Examples: "https://example.com", "netflix://title/12345".

    Args:
        url: URL or deep link to open.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.open_url(url)


@mcp.tool
def search_content(query: str) -> dict:
    """Search Fire TV for content using the built-in search.

    Args:
        query: Search query string, e.g. "Stranger Things".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.search_content(query)


@mcp.tool
def sideload(apk_path: str) -> dict:
    """Install an APK from the local host onto the Fire TV.

    Args:
        apk_path: Absolute path to the APK on the local machine.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.sideload(apk_path)


@mcp.tool
def uninstall_app(name: str) -> dict:
    """Uninstall an app by friendly name or package name.

    Args:
        name: App name (alias or package name).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.uninstall_app(name)


@mcp.tool
def clear_app_data(name: str) -> dict:
    """Clear all data for an app (cache, databases, preferences).

    Args:
        name: App name (alias or package name).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.clear_app_data(name)


@mcp.tool
def list_app_aliases() -> dict:
    """List all known app name aliases (friendly name → package name).

    Returns:
        Dict with aliases (dict mapping name to package).
    """
    return _apps.list_aliases()


@mcp.tool
def open_settings(section: str = "") -> dict:
    """Open Fire TV settings, optionally to a specific section.

    Sections: network, display, audio, controllers, apps, account, accessibility.

    Args:
        section: Settings section name, or empty for main settings.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.open_settings(section)


@mcp.tool
def screenshot(filename: str = "") -> dict:
    """Capture the Fire TV screen and return the image for visual analysis.

    Call this to see what is currently on screen. Use it before navigating
    to understand the current UI state and verify actions.

    Args:
        filename: Optional filename. Auto-generated if omitted.

    Returns:
        Dict with url (str), filename (str), size (int), and
        mime_type (str "image/jpeg"), or error details.
    """
    result = _screen.screenshot(filename)
    if "error" in result:
        return result
    size = os.path.getsize(result["path"])
    return _file_server.register(result["path"], result["filename"], size)


@mcp.tool
def screen_record(duration_s: int = 30, filename: str = "") -> dict:
    """Record the Fire TV screen for up to duration_s seconds.

    Args:
        duration_s: Recording duration in seconds (default 30, max 180).
        filename: Optional output filename. Auto-generated if omitted.

    Returns:
        Dict with path (str), filename (str), and size (int), or error details.
    """
    return _screen.screen_record(duration_s, filename)


@mcp.tool
def dump_ui() -> dict:
    """Dump the current screen's UI element tree as XML.

    Returns all visible elements with their text, content descriptions,
    resource IDs, and bounds. Use this to read what is on screen without
    needing vision — parse text content, find focusable elements, or
    determine what to navigate to next.

    Returns:
        Dict with stdout (str) containing the XML hierarchy.
    """
    _client.shell("uiautomator dump /sdcard/ui.xml")
    return _client.shell("cat /sdcard/ui.xml")


@mcp.tool
def get_screen_state() -> dict:
    """Check if the Fire TV screen is on or off.

    Returns:
        Dict with screen_on (bool) and raw output.
    """
    return _screen.screen_state()


@mcp.tool
def wake() -> dict:
    """Wake the Fire TV from sleep.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.wake()


@mcp.tool
def sleep() -> dict:
    """Put the Fire TV to sleep.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.sleep()


@mcp.tool
def get_notifications() -> dict:
    """Read active notifications on the Fire TV.

    Returns:
        Dict with stdout (str) containing notification records.
    """
    return _media.get_notifications()


@mcp.tool
def dismiss_notifications() -> dict:
    """Dismiss all notifications on the Fire TV.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.dismiss_notifications()


@mcp.tool
def get_device_info() -> dict:
    """Get Fire TV model, Android version, SDK level, resolution, and battery.

    Returns:
        Dict with model, android_version, sdk_level, resolution, and battery.
    """
    return _client.get_device_info()


@mcp.tool
def get_network_info() -> dict:
    """Get WiFi connection info: SSID and IP address.

    Returns:
        Dict with ssid (str) and ip (str).
    """
    return _client.get_network_info()


@mcp.tool
def get_storage_info() -> dict:
    """Get internal storage usage on the Fire TV.

    Returns:
        Dict with stdout (str) containing df output for /data.
    """
    return _client.get_storage_info()


@mcp.tool
def set_brightness(level: int) -> dict:
    """Set the Fire TV screen brightness (0-255).

    Args:
        level: Brightness level from 0 (dark) to 255 (max).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.set_brightness(level)


@mcp.tool
def toggle_bluetooth(enabled: bool) -> dict:
    """Enable or disable Bluetooth on the Fire TV.

    Args:
        enabled: True to enable, False to disable.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _media.toggle_bluetooth(enabled)


@mcp.tool
def discover_device() -> dict:
    """Scan the local network for a Fire TV and connect to it via ADB.

    Uses mDNS discovery first, then falls back to scanning the subnet for
    port 5555. Useful when FIRETV_HOST is not set in the environment.

    Returns:
        Dict with stdout (str) showing the connected device, or an error.
    """
    return _client._autodiscover()


@mcp.tool
def reboot() -> dict:
    """Reboot the Fire TV device.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.reboot()


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        from mcp_http_compat import serve_http

        serve_http(mcp, host="127.0.0.1", port=9814, path="/mcp")
    else:
        mcp.run()
