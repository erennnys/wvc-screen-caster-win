#!/usr/bin/env python3
"""
Web Video Caster - Windows Ekran ve Medya Yansıtıcı
Main Application Entry Point.
"""

import sys
import os
import signal
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.utils.logger import setup_logger
from src.utils.network import is_port_in_use, get_primary_local_ip
from src.core.base36 import ip_to_code
from src.core.server import CasterServer
from src.core.streamer import ScreenStreamer
from src.core.media_caster import MediaCaster
from src.ui.main_window import MainWindow

logger = setup_logger(logging.INFO)


def main():
    # Windows DPI awareness & high-resolution screen support
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WVC Screen & Media Caster")
    app.setOrganizationName("WVC Community")

    # Determine Port
    port = 30001
    if is_port_in_use(port):
        logger.warning(f"Port {port} is in use, trying 30002...")
        port = 30002
        if is_port_in_use(port):
            logger.warning(f"Port {port} is in use, falling back to 30003...")
            port = 30003

    local_ip = get_primary_local_ip()
    pc_code = ip_to_code(local_ip) or "WVC"
    logger.info("=" * 60)
    logger.info("  Web Video Caster - PC Screen & Media Caster")
    logger.info(f"  Yerel IP: {local_ip}")
    logger.info(f"  Sunucu Portu: {port}")
    logger.info(f"  Eşleşme Kodu (Pairing Code): {pc_code}")
    logger.info(f"  Web Alıcı URL: http://{local_ip}:{port}/web-receiver/index.html")
    logger.info("=" * 60)

    # Initialize Core Engines
    server = CasterServer(host="0.0.0.0", port=port)
    server.start()

    streamer = ScreenStreamer()
    media_caster = MediaCaster()

    # Create & Show Main Window
    window = MainWindow(server, streamer, media_caster)
    window.show()

    # Enable Ctrl+C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    exit_code = app.exec()

    # Cleanup
    streamer.stop()
    server.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
