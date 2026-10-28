"""
Modern TV Connection, Pairing Code Hero Badge, and Network Discovery Widget.
"""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.core.base36 import ip_to_code
from src.utils.network import get_primary_local_ip
from src.core.state import app_state
from src.core.discovery import DeviceScanner
from src.utils.i18n import i18n


class ConnectionWidget(QFrame):
    """Studio Hero Card displaying pairing code, TV connection pill, and manual connect bar."""

    tv_paired = pyqtSignal(str)

    def __init__(self, port: int = 30001, parent=None):
        super().__init__(parent)
        self.setObjectName("heroCard")
        self.port = port
        self.local_ip = get_primary_local_ip()
        self.pc_code = ip_to_code(self.local_ip) or "WVC"
        self._is_connected = False
        self._connected_ip = ""

        self._init_ui()
        self._retranslate_ui()

        app_state.register_status_listener(self._on_app_state_change)
        i18n.on_change(lambda _: self._retranslate_ui())

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Top Section: Left (Status + Instructions) | Right (Big Pairing Code Box)
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        # Connection Status Pill
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("border-radius: 5px; background-color: #F59E0B;")

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #F8FAFC;")

        status_row.addWidget(self.dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        left_col.addLayout(status_row)

        # Helper instruction text
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #94A3B8; font-size: 12.5px; line-height: 1.45;")
        left_col.addWidget(self.hint_label)

        top_row.addLayout(left_col, stretch=1)

        # Right: Pairing Code Display Box
        self.code_frame = QFrame()
        self.code_frame.setObjectName("codeBox")
        self.code_frame.setFixedWidth(155)
        code_layout = QVBoxLayout(self.code_frame)
        code_layout.setContentsMargins(14, 10, 14, 10)
        code_layout.setSpacing(2)

        self.code_caption = QLabel()
        self.code_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_caption.setStyleSheet("color: #93C5FD; font-size: 10px; font-weight: 700; letter-spacing: 1.2px;")

        self.code_value = QLabel(self.pc_code)
        self.code_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_value.setStyleSheet("color: #FFFFFF; font-size: 26px; font-weight: 800; letter-spacing: 3px;")

        code_layout.addWidget(self.code_caption)
        code_layout.addWidget(self.code_value)
        top_row.addWidget(self.code_frame)

        root.addLayout(top_row)

        # Divider Line
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #1E293B;")
        root.addWidget(divider)

        # Bottom Section: Manual Connect & Network Scan
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.manual_label = QLabel()
        self.manual_label.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 12.5px;")
        bottom_row.addWidget(self.manual_label)

        self.tv_input = QLineEdit()
        self.tv_input.setMinimumWidth(220)
        bottom_row.addWidget(self.tv_input, stretch=1)

        self.connect_btn = QPushButton()
        self.connect_btn.setObjectName("primaryBtn")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.clicked.connect(self._on_manual_connect)
        bottom_row.addWidget(self.connect_btn)

        self.scan_btn = QPushButton()
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._on_scan_subnet)
        bottom_row.addWidget(self.scan_btn)

        root.addLayout(bottom_row)

    def _retranslate_ui(self):
        self.code_caption.setText(i18n.t("pairing_code_label"))
        self.hint_label.setText(
            i18n.t("pairing_hint", code=self.pc_code, ip=self.local_ip, port=self.port)
        )
        self.manual_label.setText(i18n.t("manual_ip_label"))
        self.tv_input.setPlaceholderText(i18n.t("manual_ip_placeholder"))

        if self.connect_btn.isEnabled():
            self.connect_btn.setText(i18n.t("btn_connect"))
        else:
            self.connect_btn.setText(i18n.t("btn_checking"))

        if self.scan_btn.isEnabled():
            self.scan_btn.setText(i18n.t("btn_scan"))
        else:
            self.scan_btn.setText(i18n.t("btn_scanning"))

        self._update_status_badge()

    def _update_status_badge(self):
        if self._is_connected:
            self.dot.setStyleSheet("border-radius: 5px; background-color: #10B981;")
            self.status_label.setText(i18n.t("status_connected", ip=self._connected_ip or "Smart TV"))
            self.status_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #34D399;")
        else:
            self.dot.setStyleSheet("border-radius: 5px; background-color: #F59E0B;")
            self.status_label.setText(i18n.t("status_waiting"))
            self.status_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #F8FAFC;")

    def _on_app_state_change(self, payload: dict):
        event = payload.get("event")
        if event == "tv_connection_changed":
            state = payload.get("state", {})
            self._is_connected = state.get("tv_connected", False)
            self._connected_ip = state.get("tv_client_ip", "")
            QTimer.singleShot(0, self._update_status_badge)

    def _on_manual_connect(self):
        val = self.tv_input.text().strip()
        if not val:
            QMessageBox.warning(self, i18n.t("dlg_warn_title"), i18n.t("dlg_enter_code"))
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText(i18n.t("btn_checking"))

        def _do_resolve():
            active_ip = None
            if "." in val and val.replace(".", "").isdigit():
                if DeviceScanner.test_tv_ip(val):
                    active_ip = val
            else:
                active_ip = DeviceScanner.resolve_code_to_active_ip(val)
            QTimer.singleShot(0, lambda: self._handle_resolve_result(active_ip, val))

        threading.Thread(target=_do_resolve, daemon=True).start()

    def _handle_resolve_result(self, active_ip: str, input_val: str):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText(i18n.t("btn_connect"))

        if active_ip:
            app_state.set_tv_connected(True, active_ip, "Smart TV")
            QMessageBox.information(
                self,
                i18n.t("dlg_success_title"),
                i18n.t("dlg_tv_found", ip=active_ip),
            )
            self.tv_paired.emit(active_ip)
        else:
            QMessageBox.warning(
                self,
                i18n.t("dlg_not_found_title"),
                i18n.t("dlg_not_found_msg", val=input_val, code=self.pc_code),
            )

    def _on_scan_subnet(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText(i18n.t("btn_scanning"))

        def _do_scan():
            hosts = DeviceScanner.scan_local_subnet()
            QTimer.singleShot(0, lambda: self._handle_scan_result(hosts))

        threading.Thread(target=_do_scan, daemon=True).start()

    def _handle_scan_result(self, hosts: list):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText(i18n.t("btn_scan"))

        if hosts:
            chosen = hosts[0]
            app_state.set_tv_connected(True, chosen, "Discovered TV")
            QMessageBox.information(
                self,
                i18n.t("dlg_scan_done_title"),
                i18n.t("dlg_scan_found", ip=chosen),
            )
            self.tv_paired.emit(chosen)
        else:
            QMessageBox.information(
                self,
                i18n.t("dlg_scan_done_title"),
                i18n.t("dlg_scan_none", code=self.pc_code),
            )
