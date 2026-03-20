# Usage Examples

Practical workflows showing how to use the Android MCP server.

---

## Table of Contents

- [Visual Navigation](#visual-navigation)
- [App Management](#app-management)
- [Text Input](#text-input)
- [Scrolling and Swiping](#scrolling-and-swiping)
- [File Transfer](#file-transfer)
- [Device Information](#device-information)
- [UI Hierarchy](#ui-hierarchy)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Visual Navigation

**Goal:** See the device screen and interact with UI elements by their coordinates.

**Typical sequence:**

1. Wake the screen and take a screenshot:

    ```
    wake_screen()
    screenshot()
    ```

2. Analyze the returned image to find the element you want to interact with.

3. Tap the element at its coordinates:

    ```
    tap(540, 1200)
    ```

4. Take another screenshot to verify:

    ```
    screenshot()
    ```

This is the core workflow for all visual navigation. Always screenshot before and after interactions.

**Sample prompts to an AI assistant:**

> Take a screenshot and tell me what's on the screen.

> Tap the Chrome icon on the home screen.

> What apps are visible on the home screen right now?

---

## App Management

**Goal:** Launch, stop, install, and manage apps on the device.

**Launch an app:**

```
launch_app("com.android.chrome")
```

**Find a package name:**

```
list_packages("chrome")
```

**Force stop an app:**

```
stop_app("com.android.chrome")
```

**Install an APK:**

```
install_apk("/home/user/downloads/app.apk")
```

**Clear app data:**

```
clear_app_data("com.example.app")
```

**Sample prompts to an AI assistant:**

> Open Chrome on my phone.

> What apps do I have installed that are related to Google?

> Force stop Spotify and clear its data.

> Install the APK at `/tmp/myapp.apk` on the device.

---

## Text Input

**Goal:** Type text into input fields on the device.

**Typical sequence:**

1. Take a screenshot to see the screen:

    ```
    screenshot()
    ```

2. Tap the input field to focus it:

    ```
    tap(540, 800)
    ```

3. Type the text:

    ```
    input_text("hello world")
    ```

4. Submit with enter if needed:

    ```
    press_key("enter")
    ```

**Sample prompts to an AI assistant:**

> Open the search bar and type "weather today".

> Type my email address into the login field.

> Clear the text field and type a new message.

---

## Scrolling and Swiping

**Goal:** Scroll through content, open the app drawer, or dismiss UI elements.

**Scroll down a page:**

```
swipe(540, 1500, 540, 500, 300)
```

**Scroll up a page:**

```
swipe(540, 500, 540, 1500, 300)
```

**Open app drawer (swipe up from bottom on home screen):**

```
swipe(540, 2000, 540, 500, 300)
```

**Dismiss a notification (swipe down from top):**

```
swipe(540, 0, 540, 800, 300)
```

**Sample prompts to an AI assistant:**

> Scroll down to see more content.

> Open the app drawer and find the Settings app.

> Swipe away the notification at the top of the screen.

---

## File Transfer

**Goal:** Move files between the local machine and the Android device.

**Push a file to the device:**

```
push_file("/home/user/photo.jpg", "/sdcard/Pictures/photo.jpg")
```

**Pull a file from the device:**

```
pull_file("/sdcard/Download/document.pdf", "/tmp/document.pdf")
```

**Sample prompts to an AI assistant:**

> Copy my local file `/tmp/config.json` to the device's SD card.

> Download the photo at `/sdcard/DCIM/Camera/IMG_001.jpg` to my machine.

---

## Device Information

**Goal:** Check device status and properties.

**Get device info:**

```
get_device_info()
```

**Check screen state:**

```
screen_state()
```

**Run a shell command:**

```
shell("getprop ro.product.manufacturer")
```

**Check what activity is in the foreground:**

```
current_activity()
```

**Sample prompts to an AI assistant:**

> What phone model is connected and what Android version is it running?

> Is the screen currently on?

> What app is currently in the foreground?

> How much battery does the device have?

---

## UI Hierarchy

**Goal:** Get structured information about on-screen elements without using a vision model.

**Dump the UI tree:**

```
dump_ui()
```

Returns XML with every visible element's bounds, text, resource ID, and state. Element bounds are in the format `[left,top][right,bottom]` as pixel coordinates.

**Sample prompts to an AI assistant:**

> Dump the UI and tell me what buttons are on the screen.

> Find the search field's coordinates using the UI hierarchy.

> What text is displayed on the current screen?

---

## Sample Questions for an AI Assistant

**Navigation**
- Take a screenshot and describe what you see on my phone.
- Open Chrome, go to google.com, and search for "weather".
- Navigate to Settings and turn on Wi-Fi.
- Go back to the home screen.

**App management**
- What apps do I have installed?
- Open the Play Store and search for "Telegram".
- Force stop all Google apps.
- Install the APK I downloaded to `/tmp/app.apk`.

**Information**
- What phone is this and what version of Android is it running?
- What's the battery level?
- What app is currently open?
- Take a screenshot and read the text on the screen.

**Automation**
- Open the calculator, type 42 * 17, and tell me the result.
- Open the camera and take a photo.
- Open Messages and read my latest text.
- Open the clock app and set an alarm for 7am.
