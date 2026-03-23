# Usage Examples

Practical workflows showing how to use the Fire TV MCP server.

---

## Table of Contents

- [Watching Content](#watching-content)
- [Navigating the UI](#navigating-the-ui)
- [App Management](#app-management)
- [Searching for Content](#searching-for-content)
- [Media Playback Control](#media-playback-control)
- [Device Management](#device-management)
- [Sideloading Apps](#sideloading-apps)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Watching Content

**Goal:** Open a streaming app and start watching something.

```
launch_app("netflix")
screenshot()
# Navigate to a title
navigate("down")
navigate("down")
navigate("right")
navigate("select")
screenshot()
```

**With deep linking:**

```
open_url("netflix://title/80057281")
```

---

## Navigating the UI

**Goal:** Move through Fire TV menus using D-pad navigation.

```
wake()
screenshot()
navigate("down")
navigate("right")
navigate("select")
screenshot()
```

**Scroll through a long list:**

```
navigate_repeat("down", count=10)
screenshot()
```

**Go back or go home:**

```
navigate("back")
navigate("home")
```

---

## App Management

**Goal:** Launch, stop, and manage apps.

**Launch by friendly name:**

```
launch_app("youtube")
launch_app("prime")
launch_app("disney+")
```

**See what's running:**

```
get_current_app()
```

**Force stop an app:**

```
close_app("netflix")
```

**List installed apps:**

```
list_apps("amazon")
```

**See all supported aliases:**

```
list_app_aliases()
```

---

## Searching for Content

**Goal:** Search for movies, shows, or apps on Fire TV.

**Using built-in search:**

```
search_content("Stranger Things")
```

**Using the search UI manually:**

```
navigate("search")
input_text("The Mandalorian")
navigate("select")
screenshot()
```

**Clear and retype:**

```
clear_input()
input_text("Breaking Bad")
```

---

## Media Playback Control

**Goal:** Control what's currently playing.

**Check what's playing:**

```
now_playing()
```

**Pause/resume:**

```
media_control("play_pause")
```

**Skip forward/backward:**

```
media_control("fast_forward")
media_control("rewind")
```

**Adjust volume:**

```
volume("volume_up")
volume("volume_down")
volume("mute")
set_volume(8)
```

---

## Device Management

**Goal:** Check device status and manage settings.

**Device info:**

```
get_device_info()
get_network_info()
get_storage_info()
```

**Screen control:**

```
get_screen_state()
wake()
sleep()
set_brightness(128)
```

**Bluetooth:**

```
toggle_bluetooth(true)
toggle_bluetooth(false)
```

**Open specific settings:**

```
open_settings("network")
open_settings("display")
open_settings("apps")
```

**Reboot:**

```
reboot()
```

---

## Sideloading Apps

**Goal:** Install APKs not available on the Amazon Appstore.

```
sideload("/home/user/downloads/kodi.apk")
launch_app("kodi")
screenshot()
```

**Uninstall a sideloaded app:**

```
uninstall_app("org.xbmc.kodi")
```

---

## Sample Questions for an AI Assistant

**Navigation**
- Take a screenshot and tell me what's on my Fire TV.
- Scroll down to see more shows on the home screen.
- Go to the Netflix app and find Stranger Things.
- Navigate to Settings and check my WiFi connection.

**Media**
- What's currently playing on my Fire TV?
- Pause the movie.
- Turn the volume down to 5.
- Skip to the next episode.

**App management**
- Open YouTube on my Fire TV.
- What apps are installed on my Fire TV?
- Close all running apps.
- Sideload the APK at `/tmp/app.apk`.

**Device**
- What Fire TV model do I have?
- What's the WiFi signal strength?
- How much storage is left?
- Put the Fire TV to sleep.
