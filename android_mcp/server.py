import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from android_client import ADBClient, AppManager, FileServer, ScreenCapture, UIController

load_dotenv()

_client = ADBClient()
_client.connect()
_ui = UIController(_client)
_apps = AppManager(_client)
_screen = ScreenCapture(_client)
_file_server = FileServer()
_file_server.start()

mcp = FastMCP("android")


@mcp.tool
def shell(command: str) -> dict:
    """Run an adb shell command on the Android device.

    Use for any direct device interaction: checking files, running commands,
    querying system properties, managing settings, or anything not covered
    by other tools. Example: "ls /sdcard", "getprop ro.product.model".

    Args:
        command: Shell command to run on the device.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.shell(command)


@mcp.tool
def tap(x: int, y: int) -> dict:
    """Tap the screen at the given pixel coordinates.

    IMPORTANT: You must call `screenshot` first to see the screen, then
    determine the x/y coordinates of the element you want to tap from the
    image. After tapping, call `screenshot` again to verify the result.

    Args:
        x: Horizontal pixel coordinate (from left edge of screen).
        y: Vertical pixel coordinate (from top edge of screen).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _ui.tap(x, y)


@mcp.tool
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> dict:
    """Swipe from one point to another on the screen.

    Use for scrolling, opening the app drawer, dismissing notifications, etc.
    Call `screenshot` first to see the screen and determine coordinates.
    Swipe up to scroll down, swipe down to scroll up.

    Args:
        x1: Start X coordinate.
        y1: Start Y coordinate.
        x2: End X coordinate.
        y2: End Y coordinate.
        duration_ms: Swipe duration in milliseconds (default 300).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _ui.swipe(x1, y1, x2, y2, duration_ms)


@mcp.tool
def input_text(text: str) -> dict:
    """Type text into the currently focused input field on the device.

    You must first tap on an input field to focus it, then call this tool.
    Use `screenshot` to find the input field and `tap` to focus it.

    Args:
        text: The text to type. Spaces and special characters are escaped
            automatically.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _ui.input_text(text)


@mcp.tool
def press_key(key: str) -> dict:
    """Press a hardware/system key on the device.

    Common keys: home (go to home screen), back (go back), enter (submit),
    app_switch (recent apps), volume_up, volume_down, delete (backspace).
    Also accepts raw KEYCODE_* values.

    Args:
        key: Key name or Android keycode, e.g. "home", "back", "enter".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _ui.press_key(key)


@mcp.tool
def long_press(x: int, y: int, duration_ms: int = 1000) -> dict:
    """Long press at the given coordinates (for context menus, drag, etc.).

    Call `screenshot` first to find the target coordinates.

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        duration_ms: Hold duration in milliseconds (default 1000).

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _ui.long_press(x, y, duration_ms)


@mcp.tool
def dump_ui() -> dict:
    """Dump the current screen's UI element tree as XML.

    Returns clickable elements with their bounds (pixel coordinates),
    text labels, and resource IDs. Use this as an alternative to
    `screenshot` when you need precise element coordinates or text
    content without analyzing an image.

    Returns:
        Dict with stdout (str) containing the XML hierarchy, stderr (str),
        and exit_code (int).
    """
    return _ui.dump_ui()


@mcp.tool
def screenshot(filename: str = "") -> dict:
    """Capture the device screen and return the image for visual analysis.

    THIS IS YOUR PRIMARY WAY TO SEE THE DEVICE. Always call this FIRST
    before tapping, swiping, or typing — you need to see where things are.
    The returned image shows the current screen. Look at it to find buttons,
    text fields, icons, and their pixel coordinates for use with tap/swipe.

    Workflow: screenshot → analyze image → tap/swipe/type → screenshot again
    to verify the result.

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
def screen_state() -> dict:
    """Check if the device screen is on or off.

    Call this before interacting with the device. If the screen is off,
    call `wake_screen` first.

    Returns:
        Dict with screen_on (bool) and raw output.
    """
    return _screen.screen_state()


@mcp.tool
def wake_screen() -> dict:
    """Wake the device screen if it is off.

    Call this before taking screenshots or interacting with the device
    when the screen might be off. Does nothing if already awake.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _screen.wake_screen()


@mcp.tool
def install_apk(apk_path: str) -> dict:
    """Install an APK from a host file path onto the device.

    Args:
        apk_path: Absolute path to the APK on the local machine,
            e.g. "/home/user/app.apk".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.install_apk(apk_path)


@mcp.tool
def uninstall_app(package: str) -> dict:
    """Uninstall an app from the device by package name.

    Args:
        package: Android package name, e.g. "com.example.app".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.uninstall_app(package)


@mcp.tool
def launch_app(package: str) -> dict:
    """Launch an app on the device by package name.

    Use `list_packages` to find the package name if you don't know it.
    After launching, call `screenshot` to see the app's screen.

    Args:
        package: Android package name, e.g. "com.android.chrome".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.launch_app(package)


@mcp.tool
def stop_app(package: str) -> dict:
    """Force stop an app on the device.

    Args:
        package: Android package name, e.g. "com.example.app".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.stop_app(package)


@mcp.tool
def list_packages(filter_text: str = "") -> dict:
    """List installed packages on the device.

    Args:
        filter_text: Optional text to filter package names (case-insensitive).

    Returns:
        Dict with packages (list of str) and count (int).
    """
    return _apps.list_packages(filter_text)


@mcp.tool
def current_activity() -> dict:
    """Get the currently focused activity on the device.

    Returns:
        Dict with stdout (str) showing the resumed activity, stderr (str),
        and exit_code (int).
    """
    return _apps.current_activity()


@mcp.tool
def clear_app_data(package: str) -> dict:
    """Clear all data for an app (cache, databases, shared prefs).

    Args:
        package: Android package name, e.g. "com.example.app".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _apps.clear_app_data(package)


@mcp.tool
def get_device_info() -> dict:
    """Get device model, Android version, SDK level, resolution, and battery.

    Returns:
        Dict with model, android_version, sdk_level, resolution, and battery.
    """
    return _client.get_device_info()


@mcp.tool
def push_file(local_path: str, remote_path: str) -> dict:
    """Push a file from the host to the device.

    Args:
        local_path: Absolute path on the local machine.
        remote_path: Destination path on the device, e.g. "/sdcard/file.txt".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.push(local_path, remote_path)


@mcp.tool
def pull_file(remote_path: str, local_path: str) -> dict:
    """Pull a file from the device to the host.

    Args:
        remote_path: Path on the device, e.g. "/sdcard/photo.jpg".
        local_path: Destination absolute path on the local machine.

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _client.pull(remote_path, local_path)


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9402, path="/mcp")
    else:
        mcp.run()
