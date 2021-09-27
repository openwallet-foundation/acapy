import hashlib

from binascii import hexlify, unhexlify


class TreeHasher(object):
    def __init__(self, hashfunc=hashlib.sha256):
        self.hashfunc = hashfunc

    def hash_leaf(self, data):
        hasher = self.hashfunc()
        hasher.update(b"\x00" + data)
        return hasher.digest()

    def hash_children(self, left, right):
        hasher = self.hashfunc()
        hasher.update(b"\x01" + left + right)
        return hasher.digest()


class HexTreeHasher(TreeHasher):
    def __init__(self, hashfunc=hashlib.sha256):
        self.hasher = TreeHasher(hashfunc)

    def hash_leaf(self, data):
        return hexlify(self.hasher.hash_leaf(unhexlify(data)))

    def hash_children(self, left, right):
        return hexlify(self.hasher.hash_children(unhexlify(left), unhexlify(right)))
