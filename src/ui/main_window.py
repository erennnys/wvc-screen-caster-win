"""
Main Application Window integrating Connection Widget, Screen Mirroring Tab,
Media Casting Tab, and Live Log Console.
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QPlainTextEdit, QStatusBar, QLabel, QPushButton
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt, QTimer
from src.ui.styles import DARK_THEME_QSS
from src.ui.connection_widget import ConnectionWidget
from src.ui.screen_tab import ScreenTab
from src.ui.media_tab import MediaTab
from src.core.streamer import ScreenStreamer
from src.core.media_caster import MediaCaster
from src.core.server import CasterServer
from src.utils.logger import add_log_listener
from src.core.state import app_state

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self, server: CasterServer, streamer: ScreenStreamer, media_caster: MediaCaster):
        super().__init__()
        self.server = server
        self.streamer = streamer
        self.media_caster = media_caster

        self.setWindowTitle("Web Video Caster - Windows Ekran ve Medya Yansıtıcı")
        self.resize(850, 680)
        self.setMinimumSize(780, 600)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        add_log_listener(self._append_log)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        # 1. Connection Widget (Pairing Code & TV Status)
        self.connection_widget = ConnectionWidget(self)
        root_layout.addWidget(self.connection_widget)

        # 2. Tabs
        self.tabs = QTabWidget()

        # Tab 1: Screen Mirroring
        self.screen_tab = ScreenTab(self.streamer, self.server, self)
        self.tabs.addTab(self.screen_tab, "🖥️  Ekran Yansıtma")

        # Tab 2: Media Casting
        self.media_tab = MediaTab(self.media_caster, self.server, self)
        self.tabs.addTab(self.media_tab, "🎬  Medya Yayını")

        # Tab 3: Live Log Console
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.setContentsMargins(10, 10, 10, 10)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)

        clear_btn = QPushButton("Günlüğü Temizle")
        clear_btn.setFixedWidth(130)
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabs.addTab(self.log_tab, "📋  Günlük (Log)")

        root_layout.addWidget(self.tabs)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.sb_port_label = QLabel(f"Sunucu Portu: {self.server.port}")
        self.sb_port_label.setStyleSheet("color: #64748b; margin-right: 12px;")
        self.status_bar.addPermanentWidget(self.sb_port_label)

        self.sb_status_label = QLabel("Hazır")
        self.sb_status_label.setStyleSheet("color: #94a3b8;")
        self.status_bar.addWidget(self.sb_status_label)

    def _append_log(self, levelno: int, msg: str):
        # Thread-safe log append to QPlainTextEdit
        QTimer.singleShot(0, lambda: self.log_text.appendPlainText(msg))

    def closeEvent(self, event):
        """Clean shutdown when application window is closed."""
        logger.info("Closing application...")
        try:
            self.streamer.stop()
            self.server.stop()
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")
        event.accept()
