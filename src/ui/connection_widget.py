"""
TV Connection, Pairing Code, and Network Discovery Widget.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.core.base36 import ip_to_code
from src.utils.network import get_primary_local_ip
from src.core.state import app_state
from src.core.discovery import DeviceScanner


class ConnectionWidget(QFrame):
    """Card widget displaying pairing code, TV connection state, and manual connection controls."""

    tv_paired = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.local_ip = get_primary_local_ip()
        self.pc_code = ip_to_code(self.local_ip) or "WVC"
        self._init_ui()

        # Subscribe to app state
        app_state.register_status_listener(self._on_app_state_change)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Top Bar: Status Badge & PC Pairing Code
        top_layout = QHBoxLayout()

        # Status badge container
        status_box = QHBoxLayout()
        self.dot = QLabel()
        self.dot.setFixedSize(14, 14)
        self.dot.setStyleSheet("border-radius: 7px; background-color: #eab308;")  # Yellow: waiting

        self.status_label = QLabel("TV Bağlantısı Bekleniyor...")
        self.status_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #f8fafc;")

        status_box.addWidget(self.dot)
        status_box.addWidget(self.status_label)
        top_layout.addLayout(status_box)

        top_layout.addStretch()

        # PC Code Badge
        code_box = QHBoxLayout()
        code_title = QLabel("Bilgisayar Eşleşme Kodunuz:")
        code_title.setStyleSheet("color: #94a3b8; font-size: 12px;")

        self.code_badge = QLabel(self.pc_code)
        self.code_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);"
            "color: #ffffff; font-size: 18px; font-weight: 800; padding: 4px 16px; border-radius: 6px;"
            "letter-spacing: 2px;"
        )

        code_box.addWidget(code_title)
        code_box.addWidget(self.code_badge)
        top_layout.addLayout(code_box)

        main_layout.addLayout(top_layout)

        # Helper Info Text
        self.info_text = QLabel(
            f"💡 Televizyonunuzdaki <b>Web Video Caster Receiver</b> uygulamasında <b>'Enter Code'</b> "
            f"kısmına yukarıdaki <b>{self.pc_code}</b> kodunu yazın (veya tarayıcıdan <i>http://{self.local_ip}:30001</i> açın)."
        )
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        main_layout.addWidget(self.info_text)

        # Bottom Bar: Manual TV Code or IP Input
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        input_bar.addWidget(QLabel("veya TV'deki Kodu / IP'yi Girin:"))

        self.tv_input = QLineEdit()
        self.tv_input.setPlaceholderText("Örn: 9K veya 192.168.1.50")
        self.tv_input.setMaximumWidth(220)
        input_bar.addWidget(self.tv_input)

        self.connect_btn = QPushButton("Bağlan")
        self.connect_btn.setProperty("class", "primary-btn")
        self.connect_btn.clicked.connect(self._on_manual_connect)
        input_bar.addWidget(self.connect_btn)

        self.scan_btn = QPushButton("Ağı Tara (SSDP/Port)")
        self.scan_btn.clicked.connect(self._on_scan_subnet)
        input_bar.addWidget(self.scan_btn)

        input_bar.addStretch()
        main_layout.addLayout(input_bar)

    def _on_app_state_change(self, payload: dict):
        event = payload.get("event")
        if event == "tv_connection_changed":
            state = payload.get("state", {})
            connected = state.get("tv_connected", False)
            ip = state.get("tv_client_ip", "")
            if connected:
                self.dot.setStyleSheet("border-radius: 7px; background-color: #22c55e;")  # Green
                self.status_label.setText(f"Televizyon Bağlandı! ({ip or 'Bağlı'})")
                self.status_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #4ade80;")
            else:
                self.dot.setStyleSheet("border-radius: 7px; background-color: #eab308;")  # Yellow
                self.status_label.setText("TV Bağlantısı Bekleniyor...")
                self.status_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #f8fafc;")

    def _on_manual_connect(self):
        val = self.tv_input.text().strip()
        if not val:
            QMessageBox.warning(self, "Uyarı", "Lütfen TV ekranında görünen kodu veya IP adresini girin.")
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Kontrol Ediliyor...")

        def _do_resolve():
            active_ip = None
            if "." in val and val.replace(".", "").isdigit():
                # Direct IP entered
                if DeviceScanner.test_tv_ip(val):
                    active_ip = val
            else:
                # Pairing code entered
                active_ip = DeviceScanner.resolve_code_to_active_ip(val)

            # Back on UI
            QTimer.singleShot(0, lambda: self._handle_resolve_result(active_ip, val))

        import threading
        threading.Thread(target=_do_resolve, daemon=True).start()

    def _handle_resolve_result(self, active_ip: str, input_val: str):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Bağlan")

        if active_ip:
            app_state.set_tv_connected(True, active_ip, "Smart TV")
            QMessageBox.information(
                self,
                "Başarılı",
                f"Televizyon bulundu: {active_ip}!\nTelevizyonunuz yayına hazır.",
            )
            self.tv_paired.emit(active_ip)
        else:
            QMessageBox.warning(
                self,
                "Bulunamadı",
                f"'{input_val}' için televizyona ulaşılamadı.\n"
                f"Lütfen televizyonunuzun aynı Wi-Fi ağına bağlı olduğundan ve TV'deki Web Video Caster "
                f"uygulamasında bu bilgisayarın eşleşme kodunun ({self.pc_code}) girildiğinden emin olun.",
            )

    def _on_scan_subnet(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Taranıyor...")

        def _do_scan():
            hosts = DeviceScanner.scan_local_subnet()
            QTimer.singleShot(0, lambda: self._handle_scan_result(hosts))

        import threading
        threading.Thread(target=_do_scan, daemon=True).start()

    def _handle_scan_result(self, hosts: list):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Ağı Tara (SSDP/Port)")

        if hosts:
            chosen = hosts[0]
            app_state.set_tv_connected(True, chosen, "Discovered TV")
            QMessageBox.information(
                self,
                "Cihaz Bulundu",
                f"Ağda Web Video Caster uyumlu televizyon bulundu: {chosen}",
            )
            self.tv_paired.emit(chosen)
        else:
            QMessageBox.information(
                self,
                "Arama Tamamlandı",
                "Ağda otomatik olarak yanıt veren TV bulunamadı.\n"
                f"En güvenilir yöntem: TV'nizdeki uygulamada 'Enter Code' kısmına bilgisayarınızın kodunu ({self.pc_code}) yazmaktır.",
            )
