#!/usr/bin/env python3
"""Camera capture using AVFoundation via pyobjc.

Usage: python3 capture_av.py <duration_seconds> <output_path>

Must be launched via the CameraCapture.app bundle (open -W -g) so the process
has a GUI session — required for AVFoundation to deliver camera frames.
"""
import sys
import os
import time

import AVFoundation
import CoreMedia
import Foundation
import AppKit
import objc
from dispatch import dispatch_get_main_queue

duration = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/camera_capture.mp4"

if os.path.exists(output_path):
    os.remove(output_path)

app = AppKit.NSApplication.sharedApplication()


class VideoWriter(Foundation.NSObject):
    def initWithPath_duration_(self, path, dur):
        self = objc.super(VideoWriter, self).init()
        if self is None:
            return None
        self.path = path
        self.duration = dur
        self.writer = None
        self.writer_input = None
        self.started = False
        self.done = False
        self.start_time = None
        self.frame_count = 0
        return self

    def setupWriterWithFormat_(self, format_desc):
        dims = CoreMedia.CMVideoFormatDescriptionGetDimensions(format_desc)

        url = Foundation.NSURL.fileURLWithPath_(self.path)
        result = AVFoundation.AVAssetWriter.assetWriterWithURL_fileType_error_(
            url, AVFoundation.AVFileTypeMPEG4, None
        )
        self.writer = result[0] if isinstance(result, tuple) else result

        video_settings = {
            AVFoundation.AVVideoCodecKey: AVFoundation.AVVideoCodecTypeH264,
            AVFoundation.AVVideoWidthKey: dims.width,
            AVFoundation.AVVideoHeightKey: dims.height,
        }
        self.writer_input = AVFoundation.AVAssetWriterInput.assetWriterInputWithMediaType_outputSettings_(
            AVFoundation.AVMediaTypeVideo, video_settings
        )
        self.writer_input.setExpectsMediaDataInRealTime_(True)

        if self.writer.canAddInput_(self.writer_input):
            self.writer.addInput_(self.writer_input)

        self.writer.startWriting()

    def captureOutput_didOutputSampleBuffer_fromConnection_(self, output, sample_buffer, connection):
        if self.done:
            return

        if self.writer is None:
            format_desc = CoreMedia.CMSampleBufferGetFormatDescription(sample_buffer)
            if format_desc is None:
                return
            self.setupWriterWithFormat_(format_desc)

        if not self.started:
            pts = CoreMedia.CMSampleBufferGetPresentationTimeStamp(sample_buffer)
            self.writer.startSessionAtSourceTime_(pts)
            self.started = True
            self.start_time = time.time()

        if self.writer_input.isReadyForMoreMediaData():
            self.writer_input.appendSampleBuffer_(sample_buffer)
            self.frame_count += 1

        elapsed = time.time() - self.start_time if self.start_time else 0
        if elapsed >= self.duration:
            self.finish()

    def finish(self):
        if self.done:
            return
        self.done = True
        if self.writer_input:
            self.writer_input.markAsFinished()
        if self.writer:
            self.writer.finishWritingWithCompletionHandler_(lambda: None)
            time.sleep(0.3)


def capture():
    session = AVFoundation.AVCaptureSession.alloc().init()
    session.setSessionPreset_(AVFoundation.AVCaptureSessionPresetHigh)

    device = AVFoundation.AVCaptureDevice.defaultDeviceWithMediaType_(
        AVFoundation.AVMediaTypeVideo
    )
    if device is None:
        print("ERROR: No camera device found.", file=sys.stderr)
        sys.exit(1)

    input_device, error = AVFoundation.AVCaptureDeviceInput.deviceInputWithDevice_error_(
        device, None
    )
    if input_device is None or error is not None:
        print(f"ERROR: Cannot access camera: {error}", file=sys.stderr)
        sys.exit(1)

    if session.canAddInput_(input_device):
        session.addInput_(input_device)

    video_output = AVFoundation.AVCaptureVideoDataOutput.alloc().init()
    video_output.setAlwaysDiscardsLateVideoFrames_(True)

    writer = VideoWriter.alloc().initWithPath_duration_(output_path, duration)
    video_output.setSampleBufferDelegate_queue_(writer, dispatch_get_main_queue())

    if session.canAddOutput_(video_output):
        session.addOutput_(video_output)

    session.startRunning()
    time.sleep(0.3)

    if not session.isRunning():
        print("ERROR: Camera session failed to start.", file=sys.stderr)
        sys.exit(1)

    deadline = time.time() + duration + 5.0
    while not writer.done and time.time() < deadline:
        Foundation.NSRunLoop.mainRunLoop().runUntilDate_(
            Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.05)
        )

    if not writer.done:
        writer.finish()

    session.stopRunning()
    time.sleep(0.2)

    if writer.frame_count == 0:
        print("ERROR: No frames captured — camera not delivering video.", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(output_path)
    else:
        print("ERROR: Output file is empty or missing.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    capture()
