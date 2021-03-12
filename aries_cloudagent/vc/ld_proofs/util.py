from typing import Union


def create_jws(encoded_header: str, verify_data: bytes) -> bytes:
    """Compose JWS."""
    return (encoded_header + ".").encode("utf-8") + verify_data