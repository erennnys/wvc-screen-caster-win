#!/usr/bin/env python3
"""
Web Video Caster - Windows Screen & Media Caster
Main Application Entry Point (Hides background console window automatically on Windows).
"""

import sys
import os
import signal
import logging

# Hide Windows console window immediately if launched via python.exe / py.exe
if sys.platform == "win32":
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.utils.logger import setup_logger
from src.utils.network import is_port_in_use
from src.core.server import CasterServer
from src.core.streamer import ScreenStreamer
from src.core.media_caster import MediaCaster
from src.ui.main_window import MainWindow

logger = setup_logger(logging.WARNING)


def main():
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WVC Studio")
    app.setOrganizationName("WVC Community")

    # Determine Port
    port = 30001
    if is_port_in_use(port):
        port = 30002
        if is_port_in_use(port):
            port = 30003

    # Initialize Core Engines
    server = CasterServer(host="0.0.0.0", port=port)
    server.start()

    streamer = ScreenStreamer()
    media_caster = MediaCaster()

    # Create & Show Main Window
    window = MainWindow(server, streamer, media_caster)
    window.show()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    exit_code = app.exec()

    # Cleanup
    streamer.stop()
    server.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
