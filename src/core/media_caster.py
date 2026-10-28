"""
Media casting engine: handles local video/audio files, metadata probing,
subtitle conversion (.srt to .vtt), and range request streaming.
"""

import os
import re
import json
import logging
import subprocess
from typing import Optional, Dict, Any
from src.utils.ffmpeg_finder import find_ffprobe, find_ffmpeg
from src.core.state import app_state

logger = logging.getLogger(__name__)


class MediaCaster:
    """Manages active local media file casting and subtitle conversion."""

    def __init__(self):
        self.active_file_path: Optional[str] = None
        self.active_subtitle_path: Optional[str] = None
        self.converted_vtt_path: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def load_media(self, file_path: str, subtitle_path: Optional[str] = None) -> Dict[str, Any]:
        """Loads media file, extracts metadata and subtitle."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Medya dosyası bulunamadı: {file_path}")

        self.active_file_path = os.path.abspath(file_path)
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Probe metadata
        self.metadata = self.probe_metadata(self.active_file_path)
        self.metadata["filename"] = filename
        self.metadata["filesize"] = file_size

        # Subtitle handling
        if subtitle_path and os.path.isfile(subtitle_path):
            self.set_subtitle(subtitle_path)
        else:
            # Auto-detect matching .srt in same folder
            base_no_ext, _ = os.path.splitext(self.active_file_path)
            for sub_ext in [".srt", ".vtt", ".sub"]:
                candidate = base_no_ext + sub_ext
                if os.path.isfile(candidate):
                    self.set_subtitle(candidate)
                    break

        app_state.active_media_path = self.active_file_path
        app_state.active_media_title = filename
        app_state.active_media_duration = self.metadata.get("duration", 0.0)
        app_state.active_media_current_time = 0.0
        app_state.active_media_paused = False
        app_state.set_mode("media_casting")

        logger.info(f"Loaded media: {filename} ({self.metadata.get('duration', 0):.1f}s)")
        return self.metadata

    def set_subtitle(self, sub_path: str):
        """Converts .srt subtitle to .vtt and prepares it for the web player."""
        if not os.path.isfile(sub_path):
            return

        self.active_subtitle_path = os.path.abspath(sub_path)
        vtt_output = os.path.join(
            os.path.dirname(__file__), "..", "..", "temp_hls", "subtitle.vtt"
        )
        os.makedirs(os.path.dirname(vtt_output), exist_ok=True)

        if sub_path.lower().endswith(".vtt"):
            with open(sub_path, "r", encoding="utf-8", errors="ignore") as f_in:
                content = f_in.read()
            with open(vtt_output, "w", encoding="utf-8") as f_out:
                f_out.write(content)
        else:
            # Convert .srt to .vtt
            self.convert_srt_to_vtt(self.active_subtitle_path, vtt_output)

        self.converted_vtt_path = vtt_output
        app_state.active_subtitle_path = self.converted_vtt_path
        logger.info(f"Prepared WebVTT subtitle from: {sub_path}")

    @staticmethod
    def convert_srt_to_vtt(srt_path: str, vtt_path: str):
        """Simple and reliable SRT to WebVTT converter."""
        with open(srt_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            lines = f.readlines()

        vtt_lines = ["WEBVTT\n\n"]
        timecode_pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2}),(\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}),(\d{3})"
        )

        for line in lines:
            match = timecode_pattern.search(line)
            if match:
                # Replace commas with periods in timestamps
                formatted = f"{match.group(1)}.{match.group(2)} --> {match.group(3)}.{match.group(4)}\n"
                vtt_lines.append(formatted)
            else:
                vtt_lines.append(line)

        with open(vtt_path, "w", encoding="utf-8") as out:
            out.writelines(vtt_lines)

    @staticmethod
    def probe_metadata(file_path: str) -> Dict[str, Any]:
        """Queries audio/video duration, dimensions and codecs using ffprobe."""
        ffprobe_bin = find_ffprobe()
        meta = {
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "video_codec": None,
            "audio_codec": None,
        }

        if not ffprobe_bin:
            return meta

        try:
            cmd = [
                ffprobe_bin,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            data = json.loads(res.stdout)

            # Duration from format
            fmt = data.get("format", {})
            if "duration" in fmt:
                meta["duration"] = float(fmt["duration"])

            # Video & Audio Streams
            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type")
                if codec_type == "video" and not meta["video_codec"]:
                    meta["video_codec"] = stream.get("codec_name")
                    meta["width"] = int(stream.get("width", 0))
                    meta["height"] = int(stream.get("height", 0))
                elif codec_type == "audio" and not meta["audio_codec"]:
                    meta["audio_codec"] = stream.get("codec_name")
        except Exception as e:
            logger.warning(f"Metadata probe failed: {e}")

        return meta
