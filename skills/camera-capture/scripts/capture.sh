#!/usr/bin/env bash
# Camera capture script for camera-capture skill
# Usage: capture.sh [mode] [duration_seconds] [device_index]
#   mode:         video (default) | photo | list
#   duration_seconds: integer (default: 5, video only)
#   device_index: AVFoundation device number (default: 0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-video}"
DURATION="${2:-5}"
DEVICE="${3:-0}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── list devices ──────────────────────────────────────────────────────────────
if [[ "$MODE" == "list" ]]; then
    if ! command -v ffmpeg &>/dev/null; then
        echo "ffmpeg not installed. Install with: brew install ffmpeg" >&2
        exit 1
    fi
    ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -E "AVFoundation video|^\[AVFoundation.*\[[0-9]\]" || true
    exit 0
fi

# ── ensure dependencies ───────────────────────────────────────────────────────
if ! python3 -c "import AVFoundation, AppKit" 2>/dev/null; then
    echo "Installing pyobjc dependencies..." >&2
    pip3 install pyobjc-framework-AVFoundation pyobjc-framework-Cocoa >&2
fi

# ── build the .app bundle (once) ─────────────────────────────────────────────
APP_DIR="$SCRIPT_DIR/CameraCapture.app/Contents/MacOS"
if [[ ! -x "$APP_DIR/CameraCapture" ]]; then
    mkdir -p "$APP_DIR"
    cat > "$APP_DIR/CameraCapture" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$SCRIPT_DIR/capture_av.py" "$@"
LAUNCHER
    chmod +x "$APP_DIR/CameraCapture"

    cat > "$SCRIPT_DIR/CameraCapture.app/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CameraCapture</string>
    <key>CFBundleIdentifier</key>
    <string>com.claude.cameracapture</string>
    <key>LSBackgroundOnly</key>
    <true/>
    <key>NSCameraUsageDescription</key>
    <string>Camera capture for Claude Code</string>
</dict>
</plist>
PLIST
fi

# ── capture ───────────────────────────────────────────────────────────────────
if [[ "$MODE" == "photo" ]]; then
    OUTPUT="/tmp/camera_photo_${TIMESTAMP}.jpg"
else
    OUTPUT="/tmp/camera_clip_${TIMESTAMP}.mp4"
fi

# Launch as a .app bundle via open — this gives the process a proper GUI session
# required for AVFoundation to deliver camera frames.
# -W waits for exit, -g prevents stealing focus (invisible to user).
if ! open -W -g "$SCRIPT_DIR/CameraCapture.app" --args "$DURATION" "$OUTPUT" 2>/dev/null; then
    echo "ERROR: Capture failed." >&2
    exit 1
fi

if [[ -s "$OUTPUT" ]]; then
    echo "$OUTPUT" | tee /tmp/camera_capture_last.txt
else
    echo "ERROR: Output file is empty or missing." >&2
    exit 1
fi
