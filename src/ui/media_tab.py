"""
Media Casting Tab Widget: File selection, metadata preview, and remote player controls.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QSlider, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.core.media_caster import MediaCaster
from src.core.server import CasterServer
from src.core.state import app_state


class MediaTab(QWidget):
    """Local media file casting and remote playback controller."""

    def __init__(self, media_caster: MediaCaster, server: CasterServer, parent=None):
        super().__init__(parent)
        self.media_caster = media_caster
        self.server = server
        self.is_seeking = False
        self.is_playing = False

        self._init_ui()
        app_state.register_status_listener(self._on_app_state_change)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # File Selection Card
        file_group = QGroupBox("Medya Dosyası (Media File)")
        file_layout = QVBoxLayout(file_group)

        btn_row = QHBoxLayout()
        self.select_file_btn = QPushButton("📁  Video veya Ses Dosyası Seç")
        self.select_file_btn.setProperty("class", "primary-btn")
        self.select_file_btn.clicked.connect(self._choose_file)
        btn_row.addWidget(self.select_file_btn)

        self.select_sub_btn = QPushButton("💬  Altyazı Seç (.srt/.vtt)")
        self.select_sub_btn.clicked.connect(self._choose_subtitle)
        btn_row.addWidget(self.select_sub_btn)

        file_layout.addLayout(btn_row)

        # Selected Info Box
        self.file_label = QLabel("Seçilen Dosya: Henüz dosya seçilmedi")
        self.file_label.setStyleSheet("color: #cbd5e1; font-weight: 600; margin-top: 4px;")
        file_layout.addWidget(self.file_label)

        self.meta_label = QLabel("Süre: --:-- | Çözünürlük: -- | Codec: --")
        self.meta_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        file_layout.addWidget(self.meta_label)

        layout.addWidget(file_group)

        # Remote Control Card
        control_group = QGroupBox("Oynatıcı Kontrolleri (Player Controls)")
        ctrl_layout = QVBoxLayout(control_group)
        ctrl_layout.setSpacing(12)

        # Seek Bar & Time Display
        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-family: monospace; color: #38bdf8; min-width: 110px;")

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)

        seek_row.addWidget(self.seek_slider)
        seek_row.addWidget(self.time_label)
        ctrl_layout.addLayout(seek_row)

        # Buttons Row: Play/Pause, Stop, Volume
        btn_row2 = QHBoxLayout()

        self.play_btn = QPushButton("▶  Oynat")
        self.play_btn.setProperty("class", "primary-btn")
        self.play_btn.setFixedWidth(130)
        self.play_btn.clicked.connect(self._toggle_play_pause)
        btn_row2.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹  Durdur")
        self.stop_btn.setProperty("class", "danger-btn")
        self.stop_btn.setFixedWidth(110)
        self.stop_btn.clicked.connect(self._stop_media)
        btn_row2.addWidget(self.stop_btn)

        btn_row2.addStretch()

        # Volume Slider
        btn_row2.addWidget(QLabel("Ses:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(120)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        btn_row2.addWidget(self.vol_slider)

        self.vol_label = QLabel("100%")
        self.vol_label.setFixedWidth(40)
        btn_row2.addWidget(self.vol_label)

        ctrl_layout.addLayout(btn_row2)
        layout.addWidget(control_group)

        # Cast Action Button
        self.cast_btn = QPushButton("🚀  Televizyonda Yayını Başlat")
        self.cast_btn.setProperty("class", "primary-btn")
        self.cast_btn.setFixedHeight(50)
        self.cast_btn.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.cast_btn.clicked.connect(self._start_casting)
        layout.addWidget(self.cast_btn)

        layout.addStretch()

    def _choose_file(self):
        file_filter = "Medya Dosyaları (*.mp4 *.mkv *.avi *.mov *.webm *.ts *.mp3 *.flac *.wav *.aac);;Tüm Dosyalar (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Medya Dosyası Seç", "", file_filter)
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        meta = self.media_caster.load_media(path)
        self.file_label.setText(f"Seçilen Dosya: {os.path.basename(path)}")

        dur = meta.get("duration", 0.0)
        dur_str = self._format_time(dur)
        w = meta.get("width", 0)
        h = meta.get("height", 0)
        res_str = f"{w}x{h}" if w and h else "Ses Dosyası"
        vcodec = meta.get("video_codec") or "Yok"
        acodec = meta.get("audio_codec") or "Yok"

        sub_info = f" (Altyazı Hazır)" if self.media_caster.converted_vtt_path else ""
        self.meta_label.setText(f"Süre: {dur_str} | Çözünürlük: {res_str} | Video: {vcodec} | Ses: {acodec}{sub_info}")

    def _choose_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(self, "Altyazı Dosyası Seç", "", "Altyazı (*.srt *.vtt)")
        if path:
            self.media_caster.set_subtitle(path)
            self.meta_label.setText(self.meta_label.text() + " | Altyazı Eklendi ✓")

    def _start_casting(self):
        if not self.media_caster.active_file_path:
            return

        subtitle_url = "/media/subtitle.vtt" if self.media_caster.converted_vtt_path else None
        self.server.broadcast_command({
            "action": "play_media",
            "url": "/media/stream",
            "title": os.path.basename(self.media_caster.active_file_path),
            "subtitle": subtitle_url,
        })
        self.is_playing = True
        self.play_btn.setText("⏸  Duraklat")

    def _toggle_play_pause(self):
        if not self.media_caster.active_file_path:
            return

        if self.is_playing:
            self.server.broadcast_command({"action": "pause"})
            self.play_btn.setText("▶  Oynat")
            self.is_playing = False
        else:
            self.server.broadcast_command({"action": "resume"})
            self.play_btn.setText("⏸  Duraklat")
            self.is_playing = True

    def _stop_media(self):
        self.server.broadcast_command({"action": "stop"})
        self.is_playing = False
        self.play_btn.setText("▶  Oynat")
        self.seek_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")

    def _on_slider_pressed(self):
        self.is_seeking = True

    def _on_slider_released(self):
        self.is_seeking = False
        duration = app_state.active_media_duration
        if duration > 0:
            target_time = (self.seek_slider.value() / 1000.0) * duration
            self.server.broadcast_command({"action": "seek", "time": target_time})

    def _on_volume_changed(self, val: int):
        self.vol_label.setText(f"{val}%")
        self.server.broadcast_command({"action": "volume", "level": val / 100.0})

    def _on_app_state_change(self, payload: dict):
        event = payload.get("event")
        if event == "media_progress" and not self.is_seeking:
            data = payload.get("data", {})
            curr = data.get("current_time", 0.0)
            dur = data.get("duration", 0.0) or app_state.active_media_duration
            if dur > 0:
                self.seek_slider.setValue(int((curr / dur) * 1000))
                self.time_label.setText(f"{self._format_time(curr)} / {self._format_time(dur)}")

    @staticmethod
    def _format_time(seconds: float) -> str:
        s = int(seconds)
        hrs = s // 3600
        mins = (s % 3600) // 60
        secs = s % 60
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
