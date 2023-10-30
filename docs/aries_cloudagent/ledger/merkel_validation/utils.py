"""Merkel Validation Utils."""
from binascii import hexlify
import hashlib

hash_function = hashlib.sha256()

NIBBLE_TERMINATOR = 16
hti = {c: i for i, c in enumerate("0123456789abcdef")}


def sha3_256(x):
    """Return 256 bit digest."""
    return hashlib.sha3_256(x).digest()


def encode_hex(b):
    """Return bytes object for string or hexadecimal rep for bytes input.

    Args:
        b: string or bytes

    """
    if isinstance(b, str):
        b = bytes(b, "utf-8")
    if isinstance(b, bytes):
        return str(hexlify(b), "utf-8")
    raise TypeError("Value must be an instance of str or bytes")


def bin_to_nibbles(s):
    """Convert string s to nibbles (half-bytes)."""
    return [hti[c] for c in encode_hex(s)]


def unpack_to_nibbles(bindata):
    """Unpack packed binary data to nibbles.

    Args:
        bindata: binary packed from nibbles

    """

    o = bin_to_nibbles(bindata)
    flags = o[0]
    if flags & 2:
        o.append(NIBBLE_TERMINATOR)
    if flags & 1 == 1:
        o = o[1:]
    else:
        o = o[2:]
    return o


def audit_path_length(index: int, tree_size: int):
    """Return AuditPath length.

    Args:
        index: Leaf index
        tree_size: Tree size

    """
    length = 0
    last_node = tree_size - 1
    while last_node > 0:
        if index % 2 or index < last_node:
            length += 1
        index //= 2
        last_node //= 2

    return length


def ascii_chr(value):
    """Return bytes object."""
    return bytes([value])
