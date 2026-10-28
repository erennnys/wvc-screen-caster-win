"""
Web Video Caster Base36 Pairing Code & IP Encoder/Decoder
Implements the exact matching algorithm used by InstantBits Web Video Caster.
"""

import re
from typing import List, Optional

BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"

PRIVATE_SUBNETS = [
    {"start": 3232235520, "end": 3232301055},  # 192.168.0.0 - 192.168.255.255
    {"start": 167772160, "end": 184549375},     # 10.0.0.0 - 10.255.255.255
    {"start": 2886729728, "end": 2887778303},  # 172.16.0.0 - 172.31.255.255
]

MIN_IP = 16777216  # 1.0.0.0
REGEX_IP = re.compile(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


def ip_to_int(ip: str) -> Optional[int]:
    """Convert IPv4 string to 32-bit unsigned integer."""
    if not ip or not REGEX_IP.match(ip.strip()):
        return None
    parts = [int(p) for p in ip.strip().split(".")]
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def int_to_ip(val: int) -> str:
    """Convert 32-bit integer to IPv4 string."""
    return f"{(val >> 24) & 255}.{(val >> 16) & 255}.{(val >> 8) & 255}.{val & 255}"


def to_base36(val: int) -> str:
    """Encode integer to base36 string."""
    if val <= 0:
        return "0"
    encoded = ""
    remainder = val
    base = len(BASE36_CHARS)
    while remainder > 0:
        idx = remainder % base
        encoded = BASE36_CHARS[idx] + encoded
        remainder = (remainder - idx) // base
    return encoded


def from_base36(val: str) -> int:
    """Decode base36 string to integer."""
    if not val:
        return 0
    chars = val.lower().strip()
    decoded = 0
    base = len(BASE36_CHARS)
    for c in chars:
        idx = BASE36_CHARS.find(c)
        if idx != -1:
            decoded = (decoded * base) + idx
    return decoded


def ip_to_code(ip: str) -> Optional[str]:
    """
    Encodes an IPv4 address to Web Video Caster's short pairing code.
    If the IP is in a standard private subnet (e.g. 192.168.x.x), the subnet base
    is subtracted to yield a short 2 to 4 character code.
    """
    code_int = ip_to_int(ip)
    if code_int is None or code_int == 0:
        return None

    for subnet in PRIVATE_SUBNETS:
        if subnet["start"] < code_int < subnet["end"]:
            code_int = code_int - subnet["start"]
            break

    return to_base36(code_int).upper()


def code_to_ips(code: str, port: Optional[int] = 30001) -> List[str]:
    """
    Decodes a Web Video Caster pairing code back into candidate IPv4 addresses.
    Returns list of IP strings.
    """
    if not code:
        return []

    code_clean = code.strip()
    if "." in code_clean:
        parts = code_clean.split(".", 1)
        code_clean = parts[0]
        try:
            port = from_base36(parts[1])
            if port < 30000:
                port += 30000
        except Exception:
            port = 30001

    code_int = from_base36(code_clean)
    candidate_ints = []

    if code_int < MIN_IP:
        # It's an offset inside a private subnet
        for subnet in PRIVATE_SUBNETS:
            candidate_ints.append(code_int + subnet["start"])
    else:
        candidate_ints.append(code_int)

    ips = [int_to_ip(ci) for ci in candidate_ints]
    return ips


def get_all_code_variations(code: str) -> List[str]:
    """
    Generates variations resolving ambiguous OCR/visual characters
    (e.g. 0 <-> O, 1 <-> I).
    """
    code = code.strip().upper()
    variations = {code}

    if "0" in code:
        variations.add(code.replace("0", "O"))
    if "O" in code:
        variations.add(code.replace("O", "0"))
    if "1" in code:
        variations.add(code.replace("1", "I"))
    if "I" in code:
        variations.add(code.replace("I", "1"))

    return list(variations)
