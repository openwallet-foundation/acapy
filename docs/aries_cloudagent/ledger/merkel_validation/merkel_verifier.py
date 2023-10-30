"""Verify Leaf Inclusion."""
from .hasher import TreeHasher


class MerkleVerifier:
    """Utility class for verifying leaf inclusion."""

    def __init__(self, hasher=TreeHasher()):
        """Initialize MerkleVerifier."""
        self.hasher = hasher

    async def calculate_root_hash(
        self,
        leaf,
        leaf_index,
        audit_path,
        tree_size,
    ):
        """Calculate root hash, used to verify Merkel AuditPath.

        Reference: section 2.1.1 of RFC6962.

        Args:
            leaf: Leaf data.
            leaf_index: Index of the leaf in the tree.
            audit_path: A list of SHA-256 hashes representing the Merkle audit
            path.
            tree_size: tree size

        """
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
        """Return Least Significant Bits."""
        return x & 1
