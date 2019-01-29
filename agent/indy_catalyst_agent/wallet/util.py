"""
Wallet utility functions
"""

import base64

import base58


def b64_to_bytes(val: str, urlsafe=False) -> bytes:
    if urlsafe:
        return base64.urlsafe_b64decode(val)
    return base64.b64decode(val)

def bytes_to_b64(val: bytes, urlsafe=False) -> str:
    if urlsafe:
        return base64.urlsafe_b64encode(val).decode('ascii')
    return base64.b64encode(val).decode('ascii')

def b58_to_bytes(val: str) -> bytes:
    return base58.b58decode(val)

def bytes_to_b58(val: bytes) -> str:
    return base58.b58encode(val).decode('ascii')
