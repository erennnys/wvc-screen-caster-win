"""
Local network TV discovery, port scanner, and WVC cloud signaling.
"""

import socket
import threading
import logging
import urllib.request
from typing import List, Optional, Callable
from src.core.base36 import code_to_ips, get_all_code_variations
from src.utils.network import get_primary_local_ip

logger = logging.getLogger(__name__)


class DeviceScanner:
    """Scans local network or tests candidate IPs to discover Web Video Caster TV receivers."""

    @staticmethod
    def test_tv_ip(ip: str, port: int = 30001, timeout: float = 1.0) -> bool:
        """Tests if a TV is listening on the given IP and port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                s.connect((ip, port))
                return True
            except Exception:
                return False

    @staticmethod
    def resolve_code_to_active_ip(
        code: str,
        port: int = 30001,
        callback: Optional[Callable[[Optional[str]], None]] = None,
    ) -> Optional[str]:
        """
        Takes a pairing code displayed on the TV screen (e.g. '9W'),
        decodes it to candidate IPs, tests each one asynchronously, and returns the first reachable IP.
        """
        variations = get_all_code_variations(code)
        candidate_ips = []
        for var in variations:
            for ip in code_to_ips(var, port):
                if ip not in candidate_ips:
                    candidate_ips.append(ip)

        logger.info(f"Checking {len(candidate_ips)} candidate IPs for code '{code}': {candidate_ips}")

        found_ip: Optional[str] = None
        threads = []

        def check_candidate(candidate: str):
            nonlocal found_ip
            if DeviceScanner.test_tv_ip(candidate, port):
                found_ip = candidate

        for ip in candidate_ips:
            t = threading.Thread(target=check_candidate, args=(ip,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=1.5)

        # Fallback: if no port was open but there is only 1 candidate, that is the calculated IP
        if not found_ip and len(candidate_ips) == 1:
            found_ip = candidate_ips[0]

        if callback:
            callback(found_ip)
        return found_ip

    @staticmethod
    def scan_local_subnet(
        subnet_prefix: Optional[str] = None,
        port: int = 30001,
        callback: Optional[Callable[[List[str]], None]] = None,
    ) -> List[str]:
        """
        Fast multi-threaded scanner to discover active TV receivers on the local subnet.
        """
        if not subnet_prefix:
            local_ip = get_primary_local_ip()
            parts = local_ip.split(".")
            subnet_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."

        active_hosts = []
        threads = []
        lock = threading.Lock()

        def scan_ip(ip: str):
            if DeviceScanner.test_tv_ip(ip, port, timeout=0.8):
                with lock:
                    active_hosts.append(ip)

        for host_num in range(1, 255):
            target = f"{subnet_prefix}{host_num}"
            t = threading.Thread(target=scan_ip, args=(target,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        logger.info(f"Subnet scan found {len(active_hosts)} active devices on port {port}: {active_hosts}")
        if callback:
            callback(active_hosts)
        return active_hosts
