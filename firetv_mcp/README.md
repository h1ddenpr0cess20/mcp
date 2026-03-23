# Fire TV MCP Server

FastMCP server for controlling Amazon Fire TV devices via ADB over WiFi. Screenshots are compressed and served via a built-in HTTPS file server so vision-capable models can see and navigate the TV.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r firetv_mcp/requirements.txt
python firetv_mcp/server.py
```

The server runs on HTTP transport at `127.0.0.1:9814` by default. A local HTTPS file server starts automatically on port `9815` for serving screenshots.

## Prerequisites

- `adb` (Android Debug Bridge) must be on PATH
- `openssl` must be on PATH (for auto-generating self-signed certs)
- ADB debugging enabled on the Fire TV: Settings → My Fire TV → Developer Options → ADB Debugging
- Verify with: `adb connect <firetv-ip>:5555 && adb devices`

## Tools

- **`shell`** — Run an adb shell command on the Fire TV.
- **`navigate`** — Press a D-pad or system key (up, down, left, right, select, back, home, menu).
- **`navigate_repeat`** — Press a D-pad key multiple times with configurable delay.
- **`input_text`** — Type text into the focused input field.
- **`clear_input`** — Clear the focused input field by sending DEL keys.
- **`media_control`** — Send media commands (play, pause, stop, next, previous, rewind, fast_forward).
- **`volume`** — Volume up, down, or mute.
- **`set_volume`** — Set volume to a specific level (0–15).
- **`now_playing`** — Get current media session info (app, title, artist, state, position).
- **`launch_app`** — Launch an app by friendly name or package name.
- **`close_app`** — Force stop an app.
- **`list_apps`** — List installed packages with optional filter.
- **`get_current_app`** — Get the currently focused activity.
- **`open_url`** — Open a URL or deep link.
- **`search_content`** — Search Fire TV for content.
- **`sideload`** — Install an APK from the local host.
- **`uninstall_app`** — Uninstall an app.
- **`clear_app_data`** — Clear all data for an app.
- **`list_app_aliases`** — List all known friendly name → package mappings.
- **`open_settings`** — Open Fire TV settings or a specific section.
- **`screenshot`** — Capture the Fire TV screen and return a compressed JPEG.
- **`screen_record`** — Record the screen to MP4.
- **`get_screen_state`** — Check if the screen is on or off.
- **`wake`** — Wake the Fire TV from sleep.
- **`sleep`** — Put the Fire TV to sleep.
- **`get_notifications`** — Read active notifications.
- **`dismiss_notifications`** — Dismiss all notifications.
- **`get_device_info`** — Get model, OS version, SDK level, resolution, and battery.
- **`get_network_info`** — Get WiFi SSID and IP address.
- **`get_storage_info`** — Get internal storage usage.
- **`set_brightness`** — Set screen brightness (0–255).
- **`toggle_bluetooth`** — Enable or disable Bluetooth.
- **`reboot`** — Reboot the Fire TV.

## Configuration

Copy `.env.example` to `.env` and set your Fire TV's IP address.

| Variable | Default | Description |
|---|---|---|
| `FIRETV_HOST` | *(none)* | Fire TV IP for WiFi ADB |
| `FIRETV_PORT` | `5555` | ADB port for WiFi connection |
| `ADB_TIMEOUT` | `10` | Command timeout in seconds |
| `FILE_SERVER_HOST` | `127.0.0.1` | HTTPS file server bind address |
| `FILE_SERVER_PORT` | `9815` | HTTPS file server port |
| `FILES_DIR` | `~/firetv-mcp-files` | Local directory for served files |
| `CERT_DIR` | `~/.firetv_mcp_certs` | Directory for auto-generated TLS certs |

See [docs/configuration.md](docs/configuration.md) for full details.

## Code Structure

- `firetv_client/client.py`: `ADBClient` — ADB subprocess wrapper, connect, shell, push/pull, device/network/storage info, reboot.
- `firetv_client/media.py`: `MediaController` — D-pad navigation, media playback, volume, now-playing, wake/sleep, notifications, brightness, Bluetooth.
- `firetv_client/apps.py`: `AppManager` — Launch, close, list, sideload, uninstall with 30+ friendly aliases, deep linking, settings navigation.
- `firetv_client/screen.py`: `ScreenCapture` — Screenshot and screen recording with Pillow compression (max 1024px, JPEG quality 60).
- `firetv_client/file_server.py`: `FileServer` — HTTPS file server with auto-generated self-signed certs.
- `server.py`: FastMCP tool definitions.

## Notes

- Fire TV has no touchscreen — use D-pad navigation instead of tap/swipe.
- Screenshots are compressed from raw PNG to JPEG to keep vision model token usage low.
- On first run, a self-signed certificate is auto-generated for the file server.
- App aliases support friendly names like "netflix", "prime", "disney+", "youtube". See `list_app_aliases` for the full list.
