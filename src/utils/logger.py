"""
Application logging setup with a listener queue for UI integration.
"""

import logging
import sys
from typing import Callable, Optional

log_listeners = []


class UIStreamHandler(logging.Handler):
    """Dispatches log records to subscribed UI callbacks."""

    def emit(self, record):
        try:
            msg = self.format(record)
            for listener in log_listeners:
                try:
                    listener(record.levelno, msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def add_log_listener(callback: Callable[[int, str], None]):
    """Register a callback for UI log output."""
    if callback not in log_listeners:
        log_listeners.append(callback)


def remove_log_listener(callback: Callable[[int, str], None]):
    if callback in log_listeners:
        log_listeners.remove(callback)


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configures root logger with console and UI output."""
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )

    console_h = logging.StreamHandler(sys.stdout)
    console_h.setFormatter(formatter)
    console_h.setLevel(level)
    root.addHandler(console_h)

    ui_h = UIStreamHandler()
    ui_h.setFormatter(formatter)
    ui_h.setLevel(level)
    root.addHandler(ui_h)

    return root
