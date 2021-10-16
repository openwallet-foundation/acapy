"""Merkle tree hasher for leaf and children nodes."""
import hashlib

from binascii import hexlify, unhexlify


class TreeHasher(object):
    """Merkle tree hasher for bytes data."""

    def __init__(self, hashfunc=hashlib.sha256):
        """Initialize TreeHasher."""
        self.hashfunc = hashfunc

    def hash_leaf(self, data):
        """Return leaf node hash."""
        hasher = self.hashfunc()
        hasher.update(b"\x00" + data)
        return hasher.digest()

    def hash_children(self, left, right):
        """Return parent node hash corresponding to 2 child nodes."""
        hasher = self.hashfunc()
        hasher.update(b"\x01" + left + right)
        return hasher.digest()


class HexTreeHasher(TreeHasher):
    """Merkle tree hasher for hex data."""

    def __init__(self, hashfunc=hashlib.sha256):
        """Initialize HexTreeHasher."""
        self.hasher = TreeHasher(hashfunc)

    def hash_leaf(self, data):
        """Return leaf node hash."""
        return hexlify(self.hasher.hash_leaf(unhexlify(data)))

    def hash_children(self, left, right):
        """Return parent node hash corresponding to 2 child nodes."""
        return hexlify(self.hasher.hash_children(unhexlify(left), unhexlify(right)))
