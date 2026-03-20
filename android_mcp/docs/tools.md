# Tool Reference

Complete reference for all tools exposed by the Android MCP server.

---

## Table of Contents

- [shell](#shell)
- [tap](#tap)
- [swipe](#swipe)
- [input\_text](#input_text)
- [press\_key](#press_key)
- [long\_press](#long_press)
- [dump\_ui](#dump_ui)
- [screenshot](#screenshot)
- [screen\_state](#screen_state)
- [wake\_screen](#wake_screen)
- [install\_apk](#install_apk)
- [uninstall\_app](#uninstall_app)
- [launch\_app](#launch_app)
- [stop\_app](#stop_app)
- [list\_packages](#list_packages)
- [current\_activity](#current_activity)
- [clear\_app\_data](#clear_app_data)
- [get\_device\_info](#get_device_info)
- [push\_file](#push_file)
- [pull\_file](#pull_file)
- [Return Value Structure](#return-value-structure)
- [Error Handling](#error-handling)

---

## shell

Run an adb shell command on the Android device.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| command   | string | yes      | Shell command to execute on the device. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output from the command |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Run arbitrary commands on the device: `ls /sdcard`, `getprop ro.product.model`.
- Query or change system settings.
- Inspect files, logs, or processes on the device.

---

## tap

Tap the screen at the given pixel coordinates.

**Parameters**

| Parameter | Type    | Required | Description |
|-----------|---------|----------|-------------|
| x         | integer | yes      | Horizontal pixel coordinate (from left edge). |
| y         | integer | yes      | Vertical pixel coordinate (from top edge). |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Tap a button, icon, or link visible on screen.
- Select an item in a list or menu.
- Always call `screenshot` first to determine the correct coordinates.

---

## swipe

Swipe from one point to another on the screen.

**Parameters**

| Parameter   | Type    | Required | Default | Description |
|-------------|---------|----------|---------|-------------|
| x1          | integer | yes      |         | Start X coordinate. |
| y1          | integer | yes      |         | Start Y coordinate. |
| x2          | integer | yes      |         | End X coordinate. |
| y2          | integer | yes      |         | End Y coordinate. |
| duration_ms | integer | no       | `300`   | Swipe duration in milliseconds. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Scroll a page: swipe up (y1 > y2) to scroll down, swipe down (y1 < y2) to scroll up.
- Open the app drawer by swiping up from the bottom of the home screen.
- Dismiss notifications by swiping down from the top.

---

## input\_text

Type text into the currently focused input field on the device.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| text      | string | yes      | Text to type. Spaces and special characters are escaped automatically. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Type into a search bar, text field, or form input.
- Must tap the input field first to focus it.

---

## press\_key

Press a hardware or system key on the device.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| key       | string | yes      | Key name or Android keycode. Friendly names: `home`, `back`, `menu`, `power`, `volume_up`, `volume_down`, `enter`, `tab`, `delete`, `camera`, `search`, `app_switch`, `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`. Also accepts raw `KEYCODE_*` values. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Go to the home screen with `home`.
- Navigate back with `back`.
- Submit a form or search with `enter`.
- Switch between recent apps with `app_switch`.

---

## long\_press

Long press at the given coordinates.

**Parameters**

| Parameter   | Type    | Required | Default | Description |
|-------------|---------|----------|---------|-------------|
| x           | integer | yes      |         | Horizontal pixel coordinate. |
| y           | integer | yes      |         | Vertical pixel coordinate. |
| duration_ms | integer | no       | `1000`  | Hold duration in milliseconds. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Open context menus on UI elements.
- Initiate drag operations.
- Select text or trigger edit mode.

---

## dump\_ui

Dump the current screen's UI element tree as XML.

**Parameters**

None.

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | XML string containing the full UI hierarchy with element bounds, text, resource IDs, and states. |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Find precise pixel coordinates of elements via their `bounds` attribute (e.g. `[100,200][300,400]`).
- Read text content of UI elements without needing a vision model.
- Identify elements by `resource-id` or `content-desc` for reliable targeting.

---

## screenshot

Capture the device screen and return an HTTPS URL to the image.

**Parameters**

| Parameter | Type   | Required | Default         | Description |
|-----------|--------|----------|-----------------|-------------|
| filename  | string | no       | Auto-generated  | Filename for the screenshot. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| file_id   | string  | Unique identifier for the file |
| url       | string  | HTTPS URL where the image can be fetched |
| filename  | string  | Filename of the screenshot |
| size      | integer | File size in bytes |
| mime_type | string  | Always `"image/jpeg"` |

On error, returns a dict with an `error` field instead.

**Use cases**

- See what is currently displayed on the device screen.
- Determine pixel coordinates of buttons, icons, and text fields for `tap` and `swipe`.
- Verify the result of a previous interaction.
- This is the primary tool for visual navigation — always call it before interacting with the UI.

---

## screen\_state

Check if the device screen is on or off.

**Parameters**

None.

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| screen_on | boolean | `true` if the screen is on, `false` if off |
| raw       | string  | Raw output from the display power query |

**Use cases**

- Check screen state before attempting UI interactions.
- If the screen is off, call `wake_screen` first.

---

## wake\_screen

Wake the device screen if it is off.

**Parameters**

None.

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Wake the device before taking a screenshot or interacting with the UI.
- Does nothing if the screen is already on.

---

## install\_apk

Install an APK from a host file path onto the device.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| apk_path  | string | yes      | Absolute path to the APK on the local machine. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output (includes install success/failure message) |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## uninstall\_app

Uninstall an app from the device by package name.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| package   | string | yes      | Android package name, e.g. `"com.example.app"`. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## launch\_app

Launch an app on the device by package name.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| package   | string | yes      | Android package name, e.g. `"com.android.chrome"`. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Open an app by package name. Use `list_packages` to find the name if unknown.
- Call `screenshot` after launching to see the app's screen.

---

## stop\_app

Force stop an app on the device.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| package   | string | yes      | Android package name, e.g. `"com.example.app"`. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## list\_packages

List installed packages on the device.

**Parameters**

| Parameter   | Type   | Required | Default | Description |
|-------------|--------|----------|---------|-------------|
| filter_text | string | no       | `""`    | Text to filter package names (case-insensitive). |

**Returns**

| Field    | Type          | Description |
|----------|---------------|-------------|
| packages | array[string] | List of matching package names |
| count    | integer       | Number of matching packages |

---

## current\_activity

Get the currently focused activity on the device.

**Parameters**

None.

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Currently resumed activity information |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## clear\_app\_data

Clear all data for an app (cache, databases, shared preferences).

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| package   | string | yes      | Android package name, e.g. `"com.example.app"`. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## get\_device\_info

Get device model, Android version, SDK level, resolution, and battery status.

**Parameters**

None.

**Returns**

| Field           | Type   | Description |
|-----------------|--------|-------------|
| model           | string | Device model name |
| android_version | string | Android version, e.g. `"11"` |
| sdk_level       | string | SDK API level, e.g. `"30"` |
| resolution      | string | Screen resolution, e.g. `"1080x2300"` |
| battery         | string | Battery level and status |

---

## push\_file

Push a file from the host to the device.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| local_path  | string | yes      | Absolute path on the local machine. |
| remote_path | string | yes      | Destination path on the device, e.g. `"/sdcard/file.txt"`. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## pull\_file

Pull a file from the device to the host.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path on the device, e.g. `"/sdcard/photo.jpg"`. |
| local_path  | string | yes      | Destination absolute path on the local machine. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

---

## Return Value Structure

### shell / UI commands

```json
{
  "stdout": "content here\n",
  "stderr": "",
  "exit_code": 0
}
```

### screenshot

```json
{
  "file_id": "file_a1b2c3d4e5f67890",
  "url": "https://127.0.0.1:9410/files/file_a1b2c3d4e5f67890/content",
  "filename": "screenshot_20260320_114500.jpg",
  "size": 77234,
  "mime_type": "image/jpeg"
}
```

### list\_packages

```json
{
  "packages": [
    "com.android.chrome",
    "com.google.android.apps.translate"
  ],
  "count": 2
}
```

### get\_device\_info

```json
{
  "model": "moto g power",
  "android_version": "11",
  "sdk_level": "30",
  "resolution": "1080x2300",
  "battery": "85%"
}
```

---

## Error Handling

All tools propagate exceptions directly to the MCP client as tool execution errors. The `screenshot` tool returns a dict with an `error` field on failure instead of raising.

Common errors:

- `subprocess.TimeoutExpired` — ADB command exceeded `ADB_TIMEOUT` (default 30s).
- `subprocess.CalledProcessError` — ADB command failed (device disconnected, invalid command).
- `FileNotFoundError` — `adb` not found on PATH or APK path does not exist.
- `ConnectionError` — Device not reachable via WiFi ADB.
