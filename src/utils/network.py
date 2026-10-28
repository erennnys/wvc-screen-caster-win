"""
Network utility functions for local IP detection and interface enumeration.
"""

import socket
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def get_primary_local_ip() -> str:
    """
    Finds the primary local IPv4 address used to route traffic outside.
    Falls back to 127.0.0.1 if disconnected.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually send data over the wire
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception as e:
        logger.debug(f"Could not determine primary IP via routing socket: {e}")
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_all_local_ips() -> List[Tuple[str, str]]:
    """
    Returns list of (interface_name_or_label, ip_address) for all IPv4 interfaces.
    """
    ips = []
    primary = get_primary_local_ip()
    if primary and primary != "127.0.0.1":
        ips.append(("Varsayılan Ağ (Default LAN)", primary))

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not any(existing_ip == ip for _, existing_ip in ips):
                ips.append((f"Ağ Arayüzü ({ip})", ip))
    except Exception as e:
        logger.debug(f"Error enumerating local IPs: {e}")

    if not ips:
        ips.append(("Yerel Geri Döngü (Localhost)", "127.0.0.1"))
    return ips


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a TCP port is currently bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True
