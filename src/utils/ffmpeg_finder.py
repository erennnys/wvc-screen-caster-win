"""
FFmpeg detection, hardware acceleration check, and Windows capture device inspection.
"""

import os
import shutil
import subprocess
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


def find_ffmpeg() -> Optional[str]:
    """
    Locates the FFmpeg executable.
    Checks:
    1. System PATH
    2. Local application bin/ folder
    3. Common Windows installation paths
    """
    # 1. System PATH
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    path = shutil.which(exe_name)
    if path and os.path.isfile(path):
        return path

    path = shutil.which("ffmpeg")
    if path and os.path.isfile(path):
        return path

    # 2. Alongside application or in bin folder
    current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [
        os.path.join(current_dir, "bin", exe_name),
        os.path.join(current_dir, exe_name),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", exe_name),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "ffmpeg", "bin", exe_name),
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


def find_ffprobe() -> Optional[str]:
    """Locates ffprobe executable."""
    exe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    path = shutil.which(exe_name) or shutil.which("ffprobe")
    if path and os.path.isfile(path):
        return path

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        probe_path = os.path.join(os.path.dirname(ffmpeg_path), exe_name)
        if os.path.isfile(probe_path):
            return probe_path

    return None


def get_available_encoders(ffmpeg_bin: str) -> List[str]:
    """
    Queries FFmpeg for available H.264 video encoders.
    Returns list such as ['h264_nvenc', 'libx264'].
    """
    encoders = []
    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        output = proc.stdout
        # Priority order: NVIDIA NVENC -> Intel QuickSync -> AMD AMF -> CPU libx264
        check_list = [
            ("h264_nvenc", "NVIDIA NVENC (GPU Hızlandırma)"),
            ("h264_qsv", "Intel QuickSync (GPU Hızlandırma)"),
            ("h264_amf", "AMD AMF (GPU Hızlandırma)"),
            ("libx264", "Yazılımsal CPU (libx264 - En Uyumlu)"),
        ]
        for enc, desc in check_list:
            if enc in output:
                encoders.append((enc, desc))
    except Exception as e:
        logger.warning(f"Error querying ffmpeg encoders: {e}")

    if not encoders:
        encoders.append(("libx264", "Yazılımsal CPU (libx264 - En Uyumlu)"))

    return encoders


def get_dshow_audio_devices(ffmpeg_bin: str) -> List[str]:
    """
    On Windows, lists DirectShow audio devices that can capture desktop audio.
    """
    if os.name != "nt":
        return ["default"]

    devices = []
    try:
        cmd = [ffmpeg_bin, "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        output = proc.stderr
        in_audio_section = False
        for line in output.splitlines():
            if "DirectShow audio devices" in line:
                in_audio_section = True
                continue
            if "DirectShow video devices" in line:
                in_audio_section = False
            if in_audio_section and '"' in line:
                # Extracts device name inside quotes
                dev_name = line.split('"')[1]
                if dev_name not in devices and not dev_name.startswith("@"):
                    devices.append(dev_name)
    except Exception as e:
        logger.warning(f"Error enumerating dshow devices: {e}")

    return devices
