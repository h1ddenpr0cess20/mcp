# Tool Reference

Complete reference for all tools exposed by the Fire TV MCP server.

---

## Table of Contents

- [Navigation](#navigation)
  - [navigate](#navigate)
  - [navigate\_repeat](#navigate_repeat)
  - [input\_text](#input_text)
  - [clear\_input](#clear_input)
- [Media](#media)
  - [media\_control](#media_control)
  - [volume](#volume)
  - [set\_volume](#set_volume)
  - [now\_playing](#now_playing)
- [App Management](#app-management)
  - [launch\_app](#launch_app)
  - [close\_app](#close_app)
  - [list\_apps](#list_apps)
  - [get\_current\_app](#get_current_app)
  - [open\_url](#open_url)
  - [search\_content](#search_content)
  - [sideload](#sideload)
  - [uninstall\_app](#uninstall_app)
  - [clear\_app\_data](#clear_app_data)
  - [list\_app\_aliases](#list_app_aliases)
  - [open\_settings](#open_settings)
- [Screen](#screen)
  - [screenshot](#screenshot)
  - [screen\_record](#screen_record)
  - [get\_screen\_state](#get_screen_state)
  - [wake](#wake)
  - [sleep](#sleep)
- [Notifications](#notifications)
  - [get\_notifications](#get_notifications)
  - [dismiss\_notifications](#dismiss_notifications)
- [Device](#device)
  - [shell](#shell)
  - [get\_device\_info](#get_device_info)
  - [get\_network\_info](#get_network_info)
  - [get\_storage\_info](#get_storage_info)
  - [set\_brightness](#set_brightness)
  - [toggle\_bluetooth](#toggle_bluetooth)
  - [reboot](#reboot)

---

## Navigation

### navigate

Press a D-pad or system key on the Fire TV remote.

| Parameter | Type | Required | Description |
|---|---|---|---|
| direction | string | yes | Key name: `up`, `down`, `left`, `right`, `select`, `back`, `home`, `menu`, or any media/volume key. |

### navigate\_repeat

Press a D-pad key multiple times with a delay between presses.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| direction | string | yes | | Key name. |
| count | integer | no | `1` | Number of presses. |
| delay_ms | integer | no | `100` | Delay between presses in ms. |

Returns standard result plus `count` field.

### input\_text

Type text into the currently focused input field.

| Parameter | Type | Required | Description |
|---|---|---|---|
| text | string | yes | Text to type. Spaces and apostrophes are escaped automatically. |

### clear\_input

Clear the focused input field by sending DEL key repeatedly.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| count | integer | no | `50` | Number of delete keypresses. |

---

## Media

### media\_control

Send a media playback command.

| Parameter | Type | Required | Description |
|---|---|---|---|
| action | string | yes | `play`, `pause`, `play_pause`, `stop`, `next`, `previous`, `rewind`, `fast_forward`. |

### volume

Adjust volume.

| Parameter | Type | Required | Description |
|---|---|---|---|
| action | string | yes | `volume_up`, `volume_down`, or `mute`. |

### set\_volume

Set volume to a specific level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| level | integer | yes | Volume level from 0 (silent) to 15 (max). |

### now\_playing

Get current media session info. No parameters.

**Returns**

| Field | Type | Description |
|---|---|---|
| app | string | Package name of the media app |
| title | string | Track/show title |
| artist | string | Artist name |
| album | string | Album name |
| state | string | `playing`, `paused`, `stopped`, `buffering`, or `unknown` |
| duration_ms | integer/null | Total duration in milliseconds |
| position_ms | integer/null | Current position in milliseconds |

---

## App Management

### launch\_app

Launch an app by friendly name or package name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| name | string | yes | App alias (e.g. `netflix`, `prime`, `disney+`) or package name. |

### close\_app

Force stop an app.

| Parameter | Type | Required | Description |
|---|---|---|---|
| name | string | yes | App alias or package name. |

### list\_apps

List installed packages.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| filter_text | string | no | `""` | Filter by package name substring. |

Returns `{ packages: [...], count: N }`.

### get\_current\_app

Get the currently focused activity. No parameters.

### open\_url

Open a URL or deep link.

| Parameter | Type | Required | Description |
|---|---|---|---|
| url | string | yes | URL or deep link, e.g. `https://example.com` or `netflix://title/12345`. |

### search\_content

Search Fire TV for content using the built-in search.

| Parameter | Type | Required | Description |
|---|---|---|---|
| query | string | yes | Search query, e.g. `Stranger Things`. |

### sideload

Install an APK from the local host.

| Parameter | Type | Required | Description |
|---|---|---|---|
| apk_path | string | yes | Absolute path to the APK on the local machine. |

### uninstall\_app

Uninstall an app.

| Parameter | Type | Required | Description |
|---|---|---|---|
| name | string | yes | App alias or package name. |

### clear\_app\_data

Clear all data (cache, databases, preferences) for an app.

| Parameter | Type | Required | Description |
|---|---|---|---|
| name | string | yes | App alias or package name. |

### list\_app\_aliases

List all friendly name → package name mappings. No parameters.

### open\_settings

Open Fire TV settings.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| section | string | no | `""` | `network`, `display`, `audio`, `controllers`, `apps`, `account`, `accessibility`, or empty for main settings. |

---

## Screen

### screenshot

Capture the Fire TV screen and return an HTTPS URL to the compressed JPEG.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| filename | string | no | Auto-generated | Filename for the screenshot. |

**Returns**

| Field | Type | Description |
|---|---|---|
| file_id | string | Unique identifier |
| url | string | HTTPS URL to the image |
| filename | string | Filename |
| size | integer | File size in bytes |
| mime_type | string | Always `image/jpeg` |

### screen\_record

Record the screen to MP4.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| duration_s | integer | no | `30` | Recording duration in seconds (max 180). |
| filename | string | no | Auto-generated | Output filename. |

Returns `{ path, filename, size }`.

### get\_screen\_state

Check if the screen is on or off. No parameters.

Returns `{ screen_on: bool, raw: string }`.

### wake

Wake the Fire TV from sleep. No parameters.

### sleep

Put the Fire TV to sleep. No parameters.

---

## Notifications

### get\_notifications

Read active notifications. No parameters.

### dismiss\_notifications

Dismiss all notifications. No parameters.

---

## Device

### shell

Run any adb shell command.

| Parameter | Type | Required | Description |
|---|---|---|---|
| command | string | yes | Shell command to execute on the device. |

### get\_device\_info

Get model, Android version, SDK level, resolution, and battery. No parameters.

### get\_network\_info

Get WiFi SSID and IP address. No parameters.

Returns `{ ssid: string, ip: string }`.

### get\_storage\_info

Get internal storage usage (`df /data`). No parameters.

### set\_brightness

Set screen brightness.

| Parameter | Type | Required | Description |
|---|---|---|---|
| level | integer | yes | Brightness from 0 (dark) to 255 (max). |

### toggle\_bluetooth

Enable or disable Bluetooth.

| Parameter | Type | Required | Description |
|---|---|---|---|
| enabled | boolean | yes | `true` to enable, `false` to disable. |

### reboot

Reboot the Fire TV device. No parameters.

---

## Return Value Structure

Most tools return:

```json
{
  "stdout": "output here",
  "stderr": "",
  "exit_code": 0
}
```

On timeout, returns `exit_code: 1` with `stderr: "adb command timed out"`.

## Error Handling

- `subprocess.TimeoutExpired` — ADB command exceeded `ADB_TIMEOUT` (handled gracefully, returns error dict).
- `FileNotFoundError` — `adb` not found on PATH.
- Device disconnected — ADB commands fail with non-zero exit codes.
