"""
Wallet utility functions
"""

import base64

import base58


def b64_to_bytes(val: str, urlsafe=False) -> bytes:
    """Convert a base 64 string to bytes

    :param val: str: 
    :param urlsafe:  (Default value = False)

    """
    if urlsafe:
        return base64.urlsafe_b64decode(val)
    return base64.b64decode(val)


def bytes_to_b64(val: bytes, urlsafe=False) -> str:
    """Convert a byte string to base 64

    :param val: bytes: 
    :param urlsafe:  (Default value = False)

    """
    if urlsafe:
        return base64.urlsafe_b64encode(val).decode("ascii")
    return base64.b64encode(val).decode("ascii")


def b58_to_bytes(val: str) -> bytes:
    """Convert a base 58 string to bytes

    :param val: str: 

    """
    return base58.b58decode(val)


def bytes_to_b58(val: bytes) -> str:
    """Convert a byte string to base 58

    :param val: bytes: 

    """
    return base58.b58encode(val).decode("ascii")
