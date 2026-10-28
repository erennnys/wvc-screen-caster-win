"""
Modern Screen Mirroring Tab Widget with resolution, FPS, audio loopback,
hardware acceleration controls, and bilingual (TR/EN) support.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from src.core.streamer import ScreenStreamer
from src.core.server import CasterServer
from src.utils.ffmpeg_finder import find_ffmpeg, get_available_encoders
from src.utils.i18n import i18n


class ScreenTab(QWidget):
    """Screen Mirroring controller tab."""

    def __init__(self, streamer: ScreenStreamer, server: CasterServer, parent=None):
        super().__init__(parent)
        self.streamer = streamer
        self.server = server
        self.stream_seconds = 0
        self._error_msg = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stream_timer)

        self._init_ui()
        self._retranslate_ui()
        i18n.on_change(lambda _: self._retranslate_ui())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(14)

        # 1. Configuration Surface Card
        self.settings_card = QFrame()
        self.settings_card.setObjectName("surfaceCard")
        card_layout = QVBoxLayout(self.settings_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        # Header
        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        self.card_title = QLabel()
        self.card_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        self.card_desc = QLabel()
        self.card_desc.setStyleSheet("font-size: 12.5px; color: #94A3B8;")
        header_col.addWidget(self.card_title)
        header_col.addWidget(self.card_desc)
        card_layout.addLayout(header_col)

        # Grid Form
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        # Resolution
        self.lbl_res = QLabel()
        self.lbl_res.setStyleSheet("color: #CBD5E1; font-weight: 600;")
        self.res_combo = QComboBox()
        grid.addWidget(self.lbl_res, 0, 0)
        grid.addWidget(self.res_combo, 1, 0)

        # FPS
        self.lbl_fps = QLabel()
        self.lbl_fps.setStyleSheet("color: #CBD5E1; font-weight: 600;")
        self.fps_combo = QComboBox()
        grid.addWidget(self.lbl_fps, 0, 1)
        grid.addWidget(self.fps_combo, 1, 1)

        # Encoder
        self.lbl_enc = QLabel()
        self.lbl_enc.setStyleSheet("color: #CBD5E1; font-weight: 600;")
        self.encoder_combo = QComboBox()
        ffmpeg_bin = find_ffmpeg()
        if ffmpeg_bin:
            encoders = get_available_encoders(ffmpeg_bin)
            for enc_id, desc in encoders:
                self.encoder_combo.addItem(desc, enc_id)
        else:
            self.encoder_combo.addItem("Software (libx264)", "libx264")
        grid.addWidget(self.lbl_enc, 0, 2)
        grid.addWidget(self.encoder_combo, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        card_layout.addLayout(grid)

        # Audio Checkbox
        self.audio_check = QCheckBox()
        self.audio_check.setChecked(True)
        self.audio_check.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self.audio_check)

        layout.addWidget(self.settings_card)

        # 2. Live Status Strip + Action Button Card
        self.status_card = QFrame()
        self.status_card.setObjectName("surfaceCard")
        status_card_layout = QHBoxLayout(self.status_card)
        status_card_layout.setContentsMargins(20, 16, 20, 16)
        status_card_layout.setSpacing(16)

        status_info_col = QVBoxLayout()
        status_info_col.setSpacing(4)

        self.status_caption = QLabel()
        self.status_caption.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.8px;")

        status_badge_row = QHBoxLayout()
        status_badge_row.setSpacing(8)
        self.live_dot = QLabel()
        self.live_dot.setFixedSize(10, 10)
        self.live_dot.setStyleSheet("border-radius: 5px; background-color: #64748B;")

        self.status_text = QLabel()
        self.status_text.setStyleSheet("font-size: 14px; font-weight: 700; color: #CBD5E1;")

        self.timer_text = QLabel()
        self.timer_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 13px; font-weight: 600; color: #38BDF8; margin-left: 10px;")

        status_badge_row.addWidget(self.live_dot)
        status_badge_row.addWidget(self.status_text)
        status_badge_row.addWidget(self.timer_text)
        status_badge_row.addStretch()

        status_info_col.addWidget(self.status_caption)
        status_info_col.addLayout(status_badge_row)

        status_card_layout.addLayout(status_info_col, stretch=1)

        # Action Button
        self.action_btn = QPushButton()
        self.action_btn.setObjectName("primaryBtn")
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setFixedHeight(46)
        self.action_btn.setMinimumWidth(230)
        self.action_btn.setStyleSheet("font-size: 14px; font-weight: 700; padding: 0 24px;")
        self.action_btn.clicked.connect(self._toggle_mirroring)
        status_card_layout.addWidget(self.action_btn)

        layout.addWidget(self.status_card)
        layout.addStretch()

    def _retranslate_ui(self):
        self.card_title.setText(i18n.t("screen_card_title"))
        self.card_desc.setText(i18n.t("screen_card_desc"))
        self.lbl_res.setText(i18n.t("lbl_resolution"))
        self.lbl_fps.setText(i18n.t("lbl_fps"))
        self.lbl_enc.setText(i18n.t("lbl_encoder"))
        self.audio_check.setText(i18n.t("lbl_audio"))
        self.status_caption.setText(i18n.t("stream_status_title"))

        # Preserve combo indices
        res_idx = max(0, self.res_combo.currentIndex())
        self.res_combo.clear()
        self.res_combo.addItems([
            i18n.t("res_1080p"),
            i18n.t("res_720p"),
            i18n.t("res_1440p"),
            i18n.t("res_4k"),
        ])
        self.res_combo.setCurrentIndex(res_idx)

        fps_idx = max(0, self.fps_combo.currentIndex())
        self.fps_combo.clear()
        self.fps_combo.addItems([
            i18n.t("fps_30"),
            i18n.t("fps_60"),
            i18n.t("fps_24"),
        ])
        self.fps_combo.setCurrentIndex(fps_idx)

        self._refresh_status_labels()

    def _refresh_status_labels(self):
        hrs = self.stream_seconds // 3600
        mins = (self.stream_seconds % 3600) // 60
        secs = self.stream_seconds % 60
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.timer_text.setText(i18n.t("stream_duration", time=time_str))

        if self.streamer.is_running:
            self.action_btn.setText(f"⏹   {i18n.t('btn_stop_screen')}")
            self.action_btn.setObjectName("dangerBtn")
            self.action_btn.setStyle(self.action_btn.style())
            self.live_dot.setStyleSheet("border-radius: 5px; background-color: #EF4444;")
            self.status_text.setText(i18n.t("stream_status_live"))
            self.status_text.setStyleSheet("font-size: 14px; font-weight: 700; color: #34D399;")
        elif self._error_msg:
            self.action_btn.setText(f"📺   {i18n.t('btn_start_screen')}")
            self.action_btn.setObjectName("primaryBtn")
            self.action_btn.setStyle(self.action_btn.style())
            self.live_dot.setStyleSheet("border-radius: 5px; background-color: #EF4444;")
            self.status_text.setText(self._error_msg)
            self.status_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #F87171;")
        else:
            self.action_btn.setText(f"📺   {i18n.t('btn_start_screen')}")
            self.action_btn.setObjectName("primaryBtn")
            self.action_btn.setStyle(self.action_btn.style())
            self.live_dot.setStyleSheet("border-radius: 5px; background-color: #64748B;")
            self.status_text.setText(i18n.t("stream_status_idle"))
            self.status_text.setStyleSheet("font-size: 14px; font-weight: 700; color: #CBD5E1;")

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
        self._error_msg = ""

        try:
            self.streamer.start(
                fps=fps_raw,
                resolution=res_raw,
                audio_enabled=audio_enabled,
                encoder=encoder,
            )
            self.server.broadcast_command({
                "action": "play_stream",
                "url": "/live/stream.m3u8",
                "title": "PC Screen Mirroring",
            })

            self.stream_seconds = 0
            self.timer.start(1000)
            self._refresh_status_labels()
        except Exception as e:
            self._error_msg = str(e)
            self._refresh_status_labels()

    def stop_mirroring(self):
        self.timer.stop()
        self.streamer.stop()
        self.server.broadcast_command({"action": "stop"})
        self.stream_seconds = 0
        self._error_msg = ""
        self._refresh_status_labels()

    def _update_stream_timer(self):
        self.stream_seconds += 1
        self._refresh_status_labels()
