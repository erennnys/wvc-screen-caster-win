"""
Thread-safe application state, settings, and event dispatching.
"""

import threading
from typing import Callable, Dict, Any, Optional, List


class AppState:
    """Manages active streaming mode, TV connection state, and media progress."""

    def __init__(self):
        self._lock = threading.Lock()

        # TV Connection Status
        self.tv_connected: bool = False
        self.tv_client_ip: Optional[str] = None
        self.tv_user_agent: Optional[str] = None

        # Mode: 'idle', 'screen_mirroring', 'media_casting'
        self.current_mode: str = "idle"

        # Active media info
        self.active_media_path: Optional[str] = None
        self.active_media_title: str = ""
        self.active_media_duration: float = 0.0
        self.active_media_current_time: float = 0.0
        self.active_media_paused: bool = False
        self.active_subtitle_path: Optional[str] = None

        # Settings
        self.http_port: int = 30001
        self.screen_fps: int = 30
        self.screen_resolution: str = "1920x1080"
        self.audio_enabled: bool = True
        self.audio_device: Optional[str] = None
        self.encoder: str = "libx264"
        self.hardware_accel: bool = True

        # Listeners
        self._status_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def register_status_listener(self, cb: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if cb not in self._status_listeners:
                self._status_listeners.append(cb)

    def unregister_status_listener(self, cb: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if cb in self._status_listeners:
                self._status_listeners.remove(cb)

    def notify_status(self, event_name: str, data: Optional[Dict[str, Any]] = None):
        payload = {"event": event_name, "state": self.to_dict(), "data": data or {}}
        for cb in self._status_listeners:
            try:
                cb(payload)
            except Exception:
                pass

    def set_tv_connected(self, connected: bool, client_ip: Optional[str] = None, user_agent: Optional[str] = None):
        with self._lock:
            self.tv_connected = connected
            self.tv_client_ip = client_ip
            self.tv_user_agent = user_agent
        self.notify_status("tv_connection_changed", {"connected": connected, "ip": client_ip})

    def set_mode(self, mode: str):
        with self._lock:
            self.current_mode = mode
        self.notify_status("mode_changed", {"mode": mode})

    def update_media_progress(self, current_time: float, duration: float):
        with self._lock:
            self.active_media_current_time = current_time
            if duration > 0:
                self.active_media_duration = duration
        self.notify_status("media_progress", {"current_time": current_time, "duration": duration})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tv_connected": self.tv_connected,
            "tv_client_ip": self.tv_client_ip,
            "current_mode": self.current_mode,
            "active_media_title": self.active_media_title,
            "active_media_current_time": self.active_media_current_time,
            "active_media_duration": self.active_media_duration,
            "active_media_paused": self.active_media_paused,
            "http_port": self.http_port,
        }


# Global singleton instance
app_state = AppState()
