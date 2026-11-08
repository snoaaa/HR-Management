"""
BN-176: second authentication factor (TOTP, RFC 6238) compatible with the
usual authenticator applications (Google Authenticator, Microsoft
Authenticator, FreeOTP...). Implemented with the standard library.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

DIGITS = 6
STEP = 30


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _code(secret, counter):
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded.upper())
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def code_at(secret, timestamp=None):
    return _code(secret, int((timestamp or time.time()) // STEP))


def verify(secret, code, timestamp=None, window=1):
    """Accept the current code and the neighbouring ones (clock drift)."""
    if not secret or not code or not str(code).isdigit():
        return False
    counter = int((timestamp or time.time()) // STEP)
    return any(
        hmac.compare_digest(_code(secret, counter + delta), str(code).zfill(DIGITS))
        for delta in range(-window, window + 1)
    )


def provisioning_uri(secret, username, issuer="Saint Jean HRMS"):
    label = quote(f"{issuer}:{username}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"
