"""
Screen Mirroring Tab Widget with resolution, FPS, audio loopback, and hardware acceleration controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from src.core.streamer import ScreenStreamer
from src.core.server import CasterServer
from src.core.state import app_state
from src.utils.ffmpeg_finder import find_ffmpeg, get_available_encoders, get_dshow_audio_devices


class ScreenTab(QWidget):
    """Screen Mirroring controller tab."""

    def __init__(self, streamer: ScreenStreamer, server: CasterServer, parent=None):
        super().__init__(parent)
        self.streamer = streamer
        self.server = server
        self.stream_seconds = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stream_timer)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Settings Card
        settings_group = QGroupBox("Yayın Ayarları (Stream Settings)")
        grid = QGridLayout(settings_group)
        grid.setSpacing(12)

        # 1. Resolution
        grid.addWidget(QLabel("Çözünürlük:"), 0, 0)
        self.res_combo = QComboBox()
        self.res_combo.addItems([
            "1920x1080 (Full HD - Önerilen)",
            "1280x720 (HD - Düşük Gecikme)",
            "2560x1440 (2K QHD)",
            "3840x2160 (4K UHD)",
        ])
        grid.addWidget(self.res_combo, 0, 1)

        # 2. Framerate
        grid.addWidget(QLabel("Kare Hızı (FPS):"), 0, 2)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems([
            "30 FPS (Standart & Kararlı)",
            "60 FPS (Yüksek Akıcılık)",
            "24 FPS (Film Modu)",
        ])
        grid.addWidget(self.fps_combo, 0, 3)

        # 3. Audio Loopback
        self.audio_check = QCheckBox("Bilgisayar Masaüstü Sesini de İlet (Audio Loopback)")
        self.audio_check.setChecked(True)
        grid.addWidget(self.audio_check, 1, 0, 1, 2)

        # 4. Encoder / Hardware Acceleration
        grid.addWidget(QLabel("Video Kodlayıcı (Encoder):"), 1, 2)
        self.encoder_combo = QComboBox()
        ffmpeg_bin = find_ffmpeg()
        if ffmpeg_bin:
            encoders = get_available_encoders(ffmpeg_bin)
            for enc_id, desc in encoders:
                self.encoder_combo.addItem(desc, enc_id)
        else:
            self.encoder_combo.addItem("Yazılımsal (libx264)", "libx264")
        grid.addWidget(self.encoder_combo, 1, 3)

        layout.addWidget(settings_group)

        # Live Status Card
        status_group = QGroupBox("Yayın Durumu (Stream Status)")
        status_layout = QHBoxLayout(status_group)

        self.status_text = QLabel("Durum: Yayın Kapalı")
        self.status_text.setStyleSheet("font-size: 14px; font-weight: 600; color: #94a3b8;")

        self.timer_text = QLabel("Süre: 00:00:00")
        self.timer_text.setStyleSheet("font-family: monospace; font-size: 14px; color: #38bdf8;")

        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        status_layout.addWidget(self.timer_text)
        layout.addWidget(status_group)

        # Big Action Button
        self.action_btn = QPushButton("📺  Ekran Yansıtmayı Başlat")
        self.action_btn.setProperty("class", "primary-btn")
        self.action_btn.setFixedHeight(54)
        self.action_btn.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.action_btn.clicked.connect(self._toggle_mirroring)
        layout.addWidget(self.action_btn)

        layout.addStretch()

    def _toggle_mirroring(self):
        if self.streamer.is_running:
            self.stop_mirroring()
        else:
            self.start_mirroring()

    def start_mirroring(self):
        res_raw = self.res_combo.currentText().split(" ")[0]
        fps_raw = int(self.fps_combo.currentText().split(" ")[0])
        audio_enabled = self.audio_check.isChecked()
        encoder = self.encoder_combo.currentData() or "libx264"

        try:
            self.streamer.start(
                fps=fps_raw,
                resolution=res_raw,
                audio_enabled=audio_enabled,
                encoder=encoder,
            )
            # Notify TV to load live HLS stream
            self.server.broadcast_command({
                "action": "play_stream",
                "url": "/live/stream.m3u8",
                "title": "Ekran Yansıtma",
            })

            self.action_btn.setText("⏹️  Ekran Yansıtmayı Durdur")
            self.action_btn.setProperty("class", "danger-btn")
            self.action_btn.setStyle(self.action_btn.style())  # Refresh QSS style

            self.status_text.setText("Durum: Canlı Yayın Yapılıyor 🔴")
            self.status_text.setStyleSheet("font-size: 14px; font-weight: 700; color: #22c55e;")

            self.stream_seconds = 0
            self.timer.start(1000)
            self._update_stream_timer()
        except Exception as e:
            self.status_text.setText(f"Hata: {e}")
            self.status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #ef4444;")

    def stop_mirroring(self):
        self.timer.stop()
        self.streamer.stop()

        # Tell TV to return to splash screen
        self.server.broadcast_command({"action": "stop"})

        self.action_btn.setText("📺  Ekran Yansıtmayı Başlat")
        self.action_btn.setProperty("class", "primary-btn")
        self.action_btn.setStyle(self.action_btn.style())

        self.status_text.setText("Durum: Yayın Kapalı")
        self.status_text.setStyleSheet("font-size: 14px; font-weight: 600; color: #94a3b8;")
        self.timer_text.setText("Süre: 00:00:00")

    def _update_stream_timer(self):
        self.stream_seconds += 1
        hrs = self.stream_seconds // 3600
        mins = (self.stream_seconds % 3600) // 60
        secs = self.stream_seconds % 60
        self.timer_text.setText(f"Süre: {hrs:02d}:{mins:02d}:{secs:02d}")
