from typing import List

from .hasher import TreeHasher


class MerkleVerifier(object):
    def __init__(self, hasher=TreeHasher()):
        self.hasher = hasher

    async def calculate_root_hash(
        self,
        leaf,
        leaf_index,
        audit_path,
        tree_size,
    ):
        leaf_hash = self.hasher.hash_leaf(leaf)
        if leaf_index >= tree_size or leaf_index < 0:
            return False
        fn, sn = leaf_index, tree_size - 1
        r = leaf_hash
        for p in audit_path:
            if self.lsb(fn) or (fn == sn):
                r = self.hasher.hash_children(p, r)
                while not ((fn == 0) or self.lsb(fn)):
                    fn >>= 1
                    sn >>= 1
            else:
                r = self.hasher.hash_children(r, p)
            fn >>= 1
            sn >>= 1
        return r

    def lsb(self, x):
        return x & 1
