"""
Modern Studio Main Window integrating Header Bar with TR/EN Switcher,
Hero Connection Card, Screen Mirroring Tab, and Media Player Tab.
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from src.ui.styles import DARK_THEME_QSS
from src.ui.connection_widget import ConnectionWidget
from src.ui.screen_tab import ScreenTab
from src.ui.media_tab import MediaTab
from src.core.streamer import ScreenStreamer
from src.core.media_caster import MediaCaster
from src.core.server import CasterServer
from src.utils.network import get_primary_local_ip
from src.utils.i18n import i18n

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self, server: CasterServer, streamer: ScreenStreamer, media_caster: MediaCaster):
        super().__init__()
        self.server = server
        self.streamer = streamer
        self.media_caster = media_caster
        self.local_ip = get_primary_local_ip()

        self.resize(980, 680)
        self.setMinimumSize(920, 620)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        self._retranslate_ui()
        i18n.on_change(lambda _: self._retranslate_ui())

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 20, 24, 16)
        root_layout.setSpacing(16)

        # 1. Top Studio Header Bar (Brand Title + Language Toggle Button)
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.3px;")

        self.subtitle_label = QLabel()
        self.subtitle_label.setStyleSheet("font-size: 12.5px; color: #64748B; font-weight: 500;")

        brand_col.addWidget(self.title_label)
        brand_col.addWidget(self.subtitle_label)
        header_row.addLayout(brand_col)
        header_row.addStretch()

        # Language Switcher Pill
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("langBtn")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.clicked.connect(self._toggle_language)
        header_row.addWidget(self.lang_btn, alignment=Qt.AlignmentFlag.AlignTop)

        root_layout.addLayout(header_row)

        # 2. Hero Connection Card (Pairing Code & TV Status)
        self.connection_widget = ConnectionWidget(port=self.server.port, parent=self)
        root_layout.addWidget(self.connection_widget)

        # 3. Clean Feature Tabs (No verbose log tab)
        self.tabs = QTabWidget()

        self.screen_tab = ScreenTab(self.streamer, self.server, self)
        self.tabs.addTab(self.screen_tab, "")

        self.media_tab = MediaTab(self.media_caster, self.server, self)
        self.tabs.addTab(self.media_tab, "")

        root_layout.addWidget(self.tabs, stretch=1)

        # 4. Minimal Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.sb_status_label = QLabel()
        self.sb_status_label.setStyleSheet("color: #64748B; font-weight: 500; padding-left: 6px;")
        self.status_bar.addWidget(self.sb_status_label)

        self.sb_port_label = QLabel()
        self.sb_port_label.setStyleSheet("color: #64748B; font-family: 'Consolas', monospace; padding-right: 8px;")
        self.status_bar.addPermanentWidget(self.sb_port_label)

    def _toggle_language(self):
        next_lang = "en" if i18n.lang == "tr" else "tr"
        i18n.set_lang(next_lang)

    def _retranslate_ui(self):
        self.setWindowTitle(i18n.t("app_title"))
        self.title_label.setText(i18n.t("app_title"))
        self.subtitle_label.setText(i18n.t("app_subtitle"))

        if i18n.lang == "tr":
            self.lang_btn.setText("🌐  TR  |  EN")
        else:
            self.lang_btn.setText("🌐  EN  |  TR")

        self.tabs.setTabText(0, i18n.t("tab_screen"))
        self.tabs.setTabText(1, i18n.t("tab_media"))

        self.sb_status_label.setText(i18n.t("sb_ready"))
        self.sb_port_label.setText(i18n.t("sb_server_port", ip=self.local_ip, port=self.server.port))

    def closeEvent(self, event):
        """Clean shutdown when application window is closed."""
        try:
            self.streamer.stop()
            self.server.stop()
        except Exception:
            pass
        event.accept()
