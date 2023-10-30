"""Validates State Proof."""
import json

from collections import (
    OrderedDict,
)
from rlp import (
    encode as rlp_encode,
    decode as rlp_decode,
    DecodingError,
)
from .utils import (
    sha3_256,
    NIBBLE_TERMINATOR,
    unpack_to_nibbles,
)

from .constants import (
    NODE_TYPE_BLANK,
    NODE_TYPE_LEAF,
    NODE_TYPE_EXTENSION,
    NODE_TYPE_BRANCH,
    BLANK_NODE,
)


class SubTrie:
    """Utility class for SubTrie and State Proof validation."""

    def __init__(self, root_hash=None):
        """MPT SubTrie dictionary like interface."""
        self._subtrie = OrderedDict()
        self.set_root_hash(root_hash)

    @property
    def root_hash(self):
        """Return 32 bytes string."""
        return self._root_hash

    @root_hash.setter
    def root_hash(self, value):
        self.set_root_hash(value)

    def set_root_hash(self, root_hash=None):
        """."""
        self._root_hash = root_hash

    @staticmethod
    def _get_node_type(node):
        if node == BLANK_NODE:
            return NODE_TYPE_BLANK
        if len(node) == 2:
            nibbles = unpack_to_nibbles(node[0])
            has_terminator = nibbles and nibbles[-1] == NIBBLE_TERMINATOR
            return NODE_TYPE_LEAF if has_terminator else NODE_TYPE_EXTENSION
        if len(node) == 17:
            return NODE_TYPE_BRANCH

    @staticmethod
    async def verify_spv_proof(expected_value, proof_nodes, serialized=True):
        """Verify State Proof."""
        try:
            if serialized:
                proof_nodes = rlp_decode(proof_nodes)
            new_trie = await SubTrie.get_new_trie_with_proof_nodes(proof_nodes)
            expected_value = json.loads(expected_value)
            for encoded_node in list(new_trie._subtrie.values()):
                try:
                    decoded_node = rlp_decode(encoded_node)
                    # branch node
                    if SubTrie._get_node_type(decoded_node) == NODE_TYPE_BRANCH:
                        if (
                            json.loads(rlp_decode(decoded_node[-1])[0].decode("utf-8"))
                        ) == expected_value:
                            return True
                    # leaf or extension node
                    if SubTrie._get_node_type(decoded_node) == NODE_TYPE_LEAF:
                        if (
                            json.loads(rlp_decode(decoded_node[1])[0].decode("utf-8"))
                        ) == expected_value:
                            return True
                except DecodingError:
                    continue
            return False
        except Exception:
            return False

    @staticmethod
    async def get_new_trie_with_proof_nodes(proof_nodes):
        """Return SubTrie created from proof_nodes."""
        new_trie = SubTrie()
        for node in proof_nodes:
            R = rlp_encode(node)
            H = sha3_256(R)
            new_trie._subtrie[H] = R
        return new_trie
