"""
Screen Mirroring & Audio Capture Pipeline using FFmpeg for low-latency HLS streaming.
"""

import os
import shutil
import subprocess
import threading
import logging
import time
from typing import Optional, Tuple
from src.utils.ffmpeg_finder import find_ffmpeg, get_available_encoders
from src.core.state import app_state

logger = logging.getLogger(__name__)


class ScreenStreamer:
    """Manages the FFmpeg screen & audio capture process producing live HLS segments."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "temp_hls")
        )
        self.process: Optional[subprocess.Popen] = None
        self._is_running = False
        self._monitor_thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._is_running and self.process is not None and self.process.poll() is None

    @property
    def playlist_path(self) -> str:
        return os.path.join(self.output_dir, "stream.m3u8")

    def _prepare_output_directory(self):
        """Clean and re-create the HLS chunk directory."""
        if os.path.exists(self.output_dir):
            try:
                shutil.rmtree(self.output_dir)
            except Exception as e:
                logger.warning(f"Could not remove old HLS directory: {e}")
        os.makedirs(self.output_dir, exist_ok=True)

    def build_ffmpeg_command(
        self,
        fps: int = 30,
        resolution: str = "1920x1080",
        audio_enabled: bool = True,
        audio_device: Optional[str] = None,
        encoder: str = "libx264",
    ) -> list[str]:
        """Constructs platform-optimized FFmpeg command line."""
        ffmpeg_bin = find_ffmpeg()
        if not ffmpeg_bin:
            raise FileNotFoundError("FFmpeg bulunamadı! Lütfen FFmpeg'i kurun veya PATH'e ekleyin.")

        cmd = [ffmpeg_bin, "-y"]

        # 1. Video Input
        if os.name == "nt":
            # Windows GDI desktop grab
            cmd.extend([
                "-f", "gdigrab",
                "-framerate", str(fps),
                "-offset_x", "0",
                "-offset_y", "0",
                "-i", "desktop",
            ])
        else:
            # Linux X11 desktop grab (for testing/development)
            display = os.environ.get("DISPLAY", ":0.0")
            cmd.extend([
                "-f", "x11grab",
                "-framerate", str(fps),
                "-i", display,
            ])

        # 2. Audio Input
        has_audio_input = False
        if audio_enabled:
            if os.name == "nt" and audio_device:
                cmd.extend([
                    "-f", "dshow",
                    "-i", f"audio={audio_device}",
                ])
                has_audio_input = True
            elif os.name != "nt":
                # PulseAudio / ALSA on Linux
                if shutil.which("pactl"):
                    cmd.extend(["-f", "pulse", "-i", "default"])
                    has_audio_input = True

        if not has_audio_input:
            # Generate silent audio track so video and audio containers match
            cmd.extend([
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            ])

        # 3. Video Filters (Scaling)
        if resolution and "x" in resolution:
            w, h = resolution.split("x")
            cmd.extend(["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"])

        # 4. Video Encoding
        keyframe_interval = fps  # 1 keyframe per second
        cmd.extend([
            "-c:v", encoder,
            "-pix_fmt", "yuv420p",
            "-g", str(keyframe_interval),
            "-keyint_min", str(keyframe_interval),
        ])

        if encoder == "libx264":
            cmd.extend(["-preset", "ultrafast", "-tune", "zerolatency"])
        elif encoder == "h264_nvenc":
            cmd.extend(["-preset", "p1", "-tune", "ull"])
        elif encoder == "h264_qsv":
            cmd.extend(["-preset", "veryfast", "-low_power", "1"])

        # 5. Audio Encoding
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
        ])

        # 6. HLS Low-Latency Multiplexing
        cmd.extend([
            "-f", "hls",
            "-hls_time", "1",
            "-hls_list_size", "3",
            "-hls_flags", "delete_segments+split_by_time",
            "-hls_segment_type", "mpegts",
            "-hls_segment_filename", os.path.join(self.output_dir, "segment_%04d.ts"),
            self.playlist_path,
        ])

        return cmd

    def start(
        self,
        fps: int = 30,
        resolution: str = "1920x1080",
        audio_enabled: bool = True,
        audio_device: Optional[str] = None,
        encoder: str = "libx264",
    ):
        """Starts live screen capture and HLS segmentation."""
        if self.is_running:
            logger.info("ScreenStreamer is already running.")
            return

        self._prepare_output_directory()
        cmd = self.build_ffmpeg_command(fps, resolution, audio_enabled, audio_device, encoder)
        logger.info(f"Starting FFmpeg streamer: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._is_running = True
        app_state.set_mode("screen_mirroring")

        # Monitor thread to read stderr and catch crashes
        def monitor_process():
            while self._is_running and self.process and self.process.poll() is None:
                line = self.process.stderr.readline()
                if line:
                    if "error" in line.lower() or "fatal" in line.lower():
                        logger.warning(f"[FFmpeg] {line.strip()}")
            rc = self.process.poll() if self.process else -1
            if rc != 0 and self._is_running:
                logger.error(f"FFmpeg process exited unexpectedly with code {rc}")
            self._is_running = False

        self._monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        self._monitor_thread.start()

        # Wait briefly for the first playlist file to appear
        for _ in range(30):
            if os.path.exists(self.playlist_path):
                logger.info("HLS stream is ready for playback!")
                break
            time.sleep(0.2)

    def stop(self):
        """Terminates the FFmpeg capture process and cleans up."""
        if not self._is_running and not self.process:
            return

        logger.info("Stopping ScreenStreamer...")
        self._is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if app_state.current_mode == "screen_mirroring":
            app_state.set_mode("idle")
        logger.info("ScreenStreamer stopped.")
