"""
Silent-friendly application logging setup (handles windowless pyw.exe execution cleanly).
"""

import logging
import sys
from typing import Callable

log_listeners = []


class UIStreamHandler(logging.Handler):
    """Dispatches log records to subscribed callbacks."""

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
    if callback not in log_listeners:
        log_listeners.append(callback)


def remove_log_listener(callback: Callable[[int, str], None]):
    if callback in log_listeners:
        log_listeners.remove(callback)


def setup_logger(level: int = logging.WARNING) -> logging.Logger:
    """Configures root logger without noisy console output."""
    root = logging.getLogger()
    root.setLevel(level)

    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )

    if sys.stdout is not None:
        console_h = logging.StreamHandler(sys.stdout)
        console_h.setFormatter(formatter)
        console_h.setLevel(level)
        root.addHandler(console_h)

    # Silence aiohttp access logs
    logging.getLogger("aiohttp.access").setLevel(logging.ERROR)

    return root
