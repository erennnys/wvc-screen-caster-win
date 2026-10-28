"""
Modern Media Casting Tab Widget: File selection, metadata preview,
interactive remote playback controls (seek, jump -10s/+10s, volume/mute),
and bilingual (TR/EN) support.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QSlider, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from src.core.media_caster import MediaCaster
from src.core.server import CasterServer
from src.core.state import app_state
from src.utils.i18n import i18n


class ClickableSlider(QSlider):
    """Horizontal Slider that supports direct click-to-seek and accurate dragging."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = max(1, self.width())
            click_x = event.position().x()
            ratio = max(0.0, min(1.0, click_x / w))
            new_val = self.minimum() + int((self.maximum() - self.minimum()) * ratio)
            self.setValue(new_val)
            self.sliderMoved.emit(new_val)
            self.sliderReleased.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class MediaTab(QWidget):
    """Local media file casting and remote playback controller."""

    def __init__(self, media_caster: MediaCaster, server: CasterServer, parent=None):
        super().__init__(parent)
        self.media_caster = media_caster
        self.server = server
        self.is_seeking = False
        self.is_playing = False
        self.is_muted = False
        self._last_meta = {}
        self._last_volume = 100

        self._init_ui()
        self._retranslate_ui()

        app_state.register_status_listener(self._on_app_state_change)
        i18n.on_change(lambda _: self._retranslate_ui())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(14)

        # 1. File Selection Surface Card
        self.file_card = QFrame()
        self.file_card.setObjectName("surfaceCard")
        file_layout = QVBoxLayout(self.file_card)
        file_layout.setContentsMargins(20, 18, 20, 18)
        file_layout.setSpacing(12)

        # Header
        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        self.card_title = QLabel()
        self.card_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        self.card_desc = QLabel()
        self.card_desc.setStyleSheet("font-size: 12.5px; color: #94A3B8;")
        header_col.addWidget(self.card_title)
        header_col.addWidget(self.card_desc)
        file_layout.addLayout(header_col)

        # File Picker Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.select_file_btn = QPushButton()
        self.select_file_btn.setObjectName("primaryBtn")
        self.select_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_file_btn.clicked.connect(self._choose_file)
        btn_row.addWidget(self.select_file_btn)

        self.select_sub_btn = QPushButton()
        self.select_sub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_sub_btn.clicked.connect(self._choose_subtitle)
        btn_row.addWidget(self.select_sub_btn)
        btn_row.addStretch()

        file_layout.addLayout(btn_row)

        # File Info Badge
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.file_label = QLabel()
        self.file_label.setStyleSheet("color: #F1F5F9; font-weight: 700; font-size: 13.5px; margin-top: 2px;")
        info_col.addWidget(self.file_label)

        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        info_col.addWidget(self.meta_label)
        file_layout.addLayout(info_col)

        layout.addWidget(self.file_card)

        # 2. Remote Playback Controls Card
        self.ctrl_card = QFrame()
        self.ctrl_card.setObjectName("surfaceCard")
        ctrl_layout = QVBoxLayout(self.ctrl_card)
        ctrl_layout.setContentsMargins(20, 16, 20, 16)
        ctrl_layout.setSpacing(14)

        self.ctrl_title = QLabel()
        self.ctrl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #CBD5E1;")
        ctrl_layout.addWidget(self.ctrl_title)

        # Seek Bar & Time Display
        seek_row = QHBoxLayout()
        seek_row.setSpacing(14)

        self.seek_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 13px; font-weight: 600; color: #38BDF8; min-width: 120px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        seek_row.addWidget(self.seek_slider, stretch=1)
        seek_row.addWidget(self.time_label)
        ctrl_layout.addLayout(seek_row)

        # Transport & Volume Row
        transport_row = QHBoxLayout()
        transport_row.setSpacing(8)

        # Jump Back -10s
        self.rewind_btn = QPushButton("⏪ -10s")
        self.rewind_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rewind_btn.setFixedWidth(75)
        self.rewind_btn.clicked.connect(lambda: self._jump_relative(-10))
        transport_row.addWidget(self.rewind_btn)

        # Main Play / Pause Button
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("primaryBtn")
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setMinimumWidth(125)
        self.play_btn.clicked.connect(self._toggle_play_pause)
        transport_row.addWidget(self.play_btn)

        # Jump Forward +10s
        self.forward_btn = QPushButton("⏩ +10s")
        self.forward_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forward_btn.setFixedWidth(75)
        self.forward_btn.clicked.connect(lambda: self._jump_relative(10))
        transport_row.addWidget(self.forward_btn)

        # Stop Button
        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setFixedWidth(90)
        self.stop_btn.clicked.connect(self._stop_media)
        transport_row.addWidget(self.stop_btn)

        transport_row.addStretch()

        # Mute Toggle
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setFixedWidth(42)
        self.mute_btn.clicked.connect(self._toggle_mute)
        transport_row.addWidget(self.mute_btn)

        # Volume Slider
        self.vol_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        transport_row.addWidget(self.vol_slider)

        self.vol_label = QLabel("100%")
        self.vol_label.setStyleSheet("color: #CBD5E1; font-weight: 600; min-width: 40px;")
        transport_row.addWidget(self.vol_label)

        # Big Cast / Re-cast Button on right
        self.cast_btn = QPushButton()
        self.cast_btn.setObjectName("primaryBtn")
        self.cast_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cast_btn.setFixedHeight(38)
        self.cast_btn.setMinimumWidth(170)
        self.cast_btn.setStyleSheet("font-size: 13px; font-weight: 700; padding: 0 16px; margin-left: 6px;")
        self.cast_btn.clicked.connect(self._start_casting)
        transport_row.addWidget(self.cast_btn)

        ctrl_layout.addLayout(transport_row)
        layout.addWidget(self.ctrl_card)
        layout.addStretch()

    def _retranslate_ui(self):
        self.card_title.setText(i18n.t("media_card_title"))
        self.card_desc.setText(i18n.t("media_card_desc"))
        self.select_file_btn.setText(f"📁  {i18n.t('btn_select_video')}")
        self.select_sub_btn.setText(f"💬  {i18n.t('btn_select_sub')}")
        self.ctrl_title.setText(i18n.t("player_card_title"))
        self.stop_btn.setText(f"⏹  {i18n.t('btn_stop')}")
        self.cast_btn.setText(f"🚀  {i18n.t('btn_cast_media')}")

        self._update_play_button_text()
        self._refresh_file_labels()

    def _update_play_button_text(self):
        if not self.is_playing:
            if app_state.current_mode == "media_casting" and app_state.active_media_paused:
                self.play_btn.setText(f"▶  {i18n.t('btn_resume')}")
            else:
                self.play_btn.setText(f"▶  {i18n.t('btn_play')}")
        else:
            self.play_btn.setText(f"⏸  {i18n.t('btn_pause')}")

    def _refresh_file_labels(self):
        if not self.media_caster.active_file_path:
            self.file_label.setText(i18n.t("no_file_selected"))
            self.meta_label.setText(
                i18n.t("meta_template", dur="--:--", res="--", vcodec="--", acodec="--", sub="")
            )
            return

        name = os.path.basename(self.media_caster.active_file_path)
        self.file_label.setText(i18n.t("selected_file", name=name))

        dur = self._last_meta.get("duration", 0.0)
        dur_str = self._format_time(dur)
        w = self._last_meta.get("width", 0)
        h = self._last_meta.get("height", 0)
        res_str = f"{w}x{h}" if w and h else i18n.t("meta_audio_only")
        vcodec = self._last_meta.get("video_codec") or "-"
        acodec = self._last_meta.get("audio_codec") or "-"
        sub_info = i18n.t("meta_sub_ready") if self.media_caster.converted_vtt_path else ""

        self.meta_label.setText(
            i18n.t(
                "meta_template",
                dur=dur_str,
                res=res_str,
                vcodec=vcodec,
                acodec=acodec,
                sub=sub_info,
            )
        )

    def _choose_file(self):
        file_filter = "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.ts *.mp3 *.flac *.wav *.aac);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, i18n.t("btn_select_video"), "", file_filter)
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self._last_meta = self.media_caster.load_media(path)
        self._refresh_file_labels()
        dur = self._last_meta.get("duration", 0.0)
        self.seek_slider.setValue(0)
        self.time_label.setText(f"00:00 / {self._format_time(dur)}")
        self.is_playing = False
        self._update_play_button_text()

    def _choose_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n.t("btn_select_sub"), "", "Subtitles (*.srt *.vtt)")
        if path:
            self.media_caster.set_subtitle(path)
            self._refresh_file_labels()

    def _start_casting(self):
        if not self.media_caster.active_file_path:
            self._choose_file()
            if not self.media_caster.active_file_path:
                return

        subtitle_url = "/media/subtitle.vtt" if self.media_caster.converted_vtt_path else None
        self.server.broadcast_command({
            "action": "play_media",
            "url": "/media/stream.mp4",
            "title": os.path.basename(self.media_caster.active_file_path),
            "subtitle": subtitle_url,
        })
        self.is_playing = True
        self._update_play_button_text()

    def _toggle_play_pause(self):
        if not self.media_caster.active_file_path:
            self._choose_file()
            if not self.media_caster.active_file_path:
                return

        # If not yet casting on TV, start casting immediately
        if app_state.current_mode != "media_casting":
            self._start_casting()
            return

        if self.is_playing:
            self.server.broadcast_command({"action": "pause"})
            self.is_playing = False
        else:
            self.server.broadcast_command({"action": "play"})
            self.is_playing = True

        self._update_play_button_text()

    def _stop_media(self):
        self.server.broadcast_command({"action": "stop"})
        self.is_playing = False
        self._update_play_button_text()
        self.seek_slider.setValue(0)
        dur = app_state.active_media_duration or self._last_meta.get("duration", 0.0)
        self.time_label.setText(f"00:00 / {self._format_time(dur)}")

    def _jump_relative(self, delta_seconds: float):
        if app_state.current_mode != "media_casting":
            return
        dur = app_state.active_media_duration or self._last_meta.get("duration", 0.0)
        curr = app_state.active_media_current_time
        target = max(0.0, min(dur, curr + delta_seconds))
        self.server.broadcast_command({"action": "seek", "time": target})
        if dur > 0:
            self.seek_slider.setValue(int((target / dur) * 1000))
            self.time_label.setText(f"{self._format_time(target)} / {self._format_time(dur)}")

    def _on_slider_pressed(self):
        self.is_seeking = True

    def _on_slider_moved(self, val: int):
        dur = app_state.active_media_duration or self._last_meta.get("duration", 0.0)
        if dur > 0:
            preview_sec = (val / 1000.0) * dur
            self.time_label.setText(f"{self._format_time(preview_sec)} / {self._format_time(dur)}")

    def _on_slider_released(self):
        self.is_seeking = False
        dur = app_state.active_media_duration or self._last_meta.get("duration", 0.0)
        if dur > 0:
            target_time = (self.seek_slider.value() / 1000.0) * dur
            self.server.broadcast_command({"action": "seek", "time": target_time})

    def _on_volume_changed(self, val: int):
        self.vol_label.setText(f"{val}%")
        self._last_volume = val
        self.is_muted = (val == 0)
        self.mute_btn.setText("🔇" if self.is_muted else "🔊")
        self.server.broadcast_command({"action": "volume", "level": val / 100.0})

    def _toggle_mute(self):
        if self.is_muted:
            self.is_muted = False
            self.mute_btn.setText("🔊")
            restore_val = self._last_volume if self._last_volume > 0 else 80
            self.vol_slider.setValue(restore_val)
            self.server.broadcast_command({"action": "volume", "level": restore_val / 100.0})
        else:
            self.is_muted = True
            self.mute_btn.setText("🔇")
            self.server.broadcast_command({"action": "volume", "level": 0.0})

    def _on_app_state_change(self, payload: dict):
        event = payload.get("event")
        if event == "media_progress" and not self.is_seeking:
            data = payload.get("data", {})
            curr = data.get("current_time", 0.0)
            dur = data.get("duration", 0.0) or app_state.active_media_duration or self._last_meta.get("duration", 0.0)
            if dur > 0:
                pos = int(max(0.0, min(1.0, curr / dur)) * 1000)
                QTimer.singleShot(0, lambda: self.seek_slider.setValue(pos))
                QTimer.singleShot(0, lambda: self.time_label.setText(f"{self._format_time(curr)} / {self._format_time(dur)}"))
        elif event == "media_pause_changed":
            is_paused = payload.get("data", {}).get("paused", False)
            self.is_playing = not is_paused
            QTimer.singleShot(0, self._update_play_button_text)
        elif event == "mode_changed":
            mode = payload.get("data", {}).get("mode")
            if mode != "media_casting":
                self.is_playing = False
                QTimer.singleShot(0, self._update_play_button_text)
                dur = self._last_meta.get("duration", 0.0)
                QTimer.singleShot(0, lambda: self.seek_slider.setValue(0))
                QTimer.singleShot(0, lambda: self.time_label.setText(f"00:00 / {self._format_time(dur)}"))

    @staticmethod
    def _format_time(seconds: float) -> str:
        s = int(max(0.0, seconds))
        hrs = s // 3600
        mins = (s % 3600) // 60
        secs = s % 60
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
