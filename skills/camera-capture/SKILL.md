---
name: camera-capture
description: >
  Captures a live video clip or still photo from the laptop's connected camera
  (built-in FaceTime webcam or any USB/Thunderbolt camera) and delivers it
  directly into the Claude Code session via SendUserFile.

  Use this skill whenever the user asks to: "take a video", "record a clip",
  "capture from camera", "take a photo", "snap a pic", "show me what's in front
  of the camera", "shoot a quick clip", "record a few seconds of video",
  "use the webcam", "capture from the webcam", "what can you see right now",
  or any other request involving recording or snapping media from the camera.
  Even if the user doesn't say "skill" — if they want live camera footage, use this.
---

# Camera Capture

Capture a video clip or still photo from the laptop's camera and send it to the session.

## Step 1 — Decide mode and duration

| Request clues | Mode | Default duration |
|---|---|---|
| "clip", "video", "record", "footage" | `video` | 5 seconds |
| "photo", "pic", "snapshot", "image" | `photo` | N/A |

If the user specifies a duration ("3-second clip", "record for 10 seconds"), honour it.

## Step 2 — Run the capture script

```bash
bash ~/.claude/skills/camera-capture/scripts/capture.sh [mode] [duration_seconds] [device_index]
```

- `mode` — `video` (default) or `photo`
- `duration_seconds` — integer, only used in video mode (default: 5)
- `device_index` — AVFoundation device number (default: 0). Run `list` mode to see available devices

**Examples:**
```bash
bash ~/.claude/skills/camera-capture/scripts/capture.sh video 5
bash ~/.claude/skills/camera-capture/scripts/capture.sh video 5 0   # explicit device 0
bash ~/.claude/skills/camera-capture/scripts/capture.sh photo
bash ~/.claude/skills/camera-capture/scripts/capture.sh video 10
bash ~/.claude/skills/camera-capture/scripts/capture.sh list        # list available cameras
```

The script prints a single line: the path to the captured file (e.g. `/tmp/camera_clip_20260601_143022.mp4`).

## Step 3 — Send the file to the session

After the script exits successfully, call `SendUserFile` with the path it printed.
Set `status` to `"normal"` and add a caption like `"Live capture — 5-second clip"`.

## Handling errors

The most common failure is missing camera permission. If the script exits with a non-zero code or prints an error mentioning "access" or "permission":

1. Tell the user: "macOS needs camera access for the terminal. Open **System Settings → Privacy & Security → Camera** and enable access for **Terminal** (or iTerm, whichever you're using), then try again."
2. Do not retry automatically — let the user fix permissions first.

If `ffmpeg` is missing the script installs it automatically via Homebrew (takes ~30-60 seconds on first run). Let the user know it's installing so they aren't confused by the wait.

## Listing cameras

If the user asks which cameras are available, run:

```bash
bash ~/.claude/skills/camera-capture/scripts/capture.sh list
```

This prints the available AVFoundation video devices.
