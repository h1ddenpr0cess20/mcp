# Android MCP Server (FastMCP)

FastMCP server for controlling an Android device via ADB. Screenshots are compressed and served via a built-in HTTPS file server so vision-capable models can see and navigate the device.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r android_mcp/requirements.txt
python android_mcp/server.py
```

The server runs on HTTP transport at `127.0.0.1:9700` by default. A local HTTPS file server starts automatically on port `9701` for serving screenshots.

## Prerequisites

- `adb` (Android Debug Bridge) must be on PATH
- `openssl` must be on PATH (for auto-generating self-signed certs)
- A connected device with USB debugging enabled, or an emulator running
- Verify with: `adb devices`

## Tools

- **`shell`** — Run an adb shell command on the device; returns stdout, stderr, and exit_code.
- **`tap`** — Tap the screen at x,y pixel coordinates. Call `screenshot` first to find targets.
- **`swipe`** — Swipe from one point to another with configurable duration.
- **`long_press`** — Long press at x,y coordinates for context menus, drag, etc.
- **`input_text`** — Type text into the currently focused input field.
- **`press_key`** — Press a key by name (home, back, enter, volume_up, etc.) or raw keycode.
- **`dump_ui`** — Dump the current UI element tree as XML with bounds, text, and resource IDs.
- **`screenshot`** — Capture the device screen and return an HTTPS URL to the compressed JPEG image.
- **`screen_state`** — Check if the screen is on or off.
- **`wake_screen`** — Wake the screen if it is off.
- **`install_apk`** — Install an APK from a host file path.
- **`uninstall_app`** — Uninstall an app by package name.
- **`launch_app`** — Launch an app by package name.
- **`stop_app`** — Force stop an app.
- **`list_packages`** — List installed packages with optional filter.
- **`current_activity`** — Get the currently focused activity.
- **`clear_app_data`** — Clear all data for an app.
- **`get_device_info`** — Get device model, Android version, SDK level, resolution, and battery.
- **`push_file`** — Push a file from the host to the device.
- **`pull_file`** — Pull a file from the device to the host.

## Configuration

Copy `.env.example` to `.env` and fill in values.

| Variable | Default | Description |
|---|---|---|
| `ADB_HOST` | *(none)* | Device IP for WiFi ADB (leave blank for USB/emulator) |
| `ADB_PORT` | `5555` | ADB port for WiFi connection |
| `ADB_SERIAL` | *(none)* | Device serial (for multiple devices) |
| `ADB_TIMEOUT` | `30` | Command timeout in seconds |
| `SCREENSHOT_DIR` | `/tmp/android_screenshots` | Local directory for saved screenshots |
| `FILE_SERVER_HOST` | `127.0.0.1` | HTTPS file server bind address |
| `FILE_SERVER_PORT` | `9701` | HTTPS file server port |
| `FILES_DIR` | `~/mcp-files` | Local directory for served files |
| `CERT_DIR` | `~/.android_mcp_certs` | Directory for auto-generated TLS certs |

## Code Structure

- `android_client/client.py`: `ADBClient` — Core ADB subprocess wrapper, shell execution, push/pull, device info.
- `android_client/ui.py`: `UIController` — Tap, swipe, text input, key presses, long press, UI dump.
- `android_client/apps.py`: `AppManager` — Install, uninstall, launch, stop, list, clear data.
- `android_client/screen.py`: `ScreenCapture` — Screenshot capture with Pillow compression (max 1024px, JPEG quality 60).
- `android_client/file_server.py`: `FileServer` — HTTPS file server with auto-generated self-signed certs.
- `server.py`: FastMCP tool definitions.

## Notes

- For WiFi ADB, first connect via USB and run `adb tcpip 5555`, then set `ADB_HOST` to the device IP.
- Screenshots are compressed from raw PNG (~4MB) to JPEG (~50-100KB) to keep vision model token usage reasonable.
- On first run, a self-signed certificate is auto-generated. Browser-based clients may need to visit `https://127.0.0.1:9701` once to accept the cert.
- The `dump_ui` tool is useful for finding element coordinates and resource IDs without needing a vision model.
- See `server.py` for transport options (stdio, HTTP, SSE).
