import json

from asynctest import TestCase

from ..domain_txn_handler import (
    prepare_for_state_read,
    get_proof_nodes,
)
from ..hasher import TreeHasher, HexTreeHasher
from ..trie import SubTrie
from ..merkel_verifier import MerkleVerifier

from .test_data import (
    GET_REVOC_REG_REPLY_A,
    GET_REVOC_REG_REPLY_B,
    GET_ATTRIB_REPLY,
    GET_CLAIM_DEF_REPLY_INVALID,
    GET_CLAIM_DEF_REPLY_A,
    GET_CLAIM_DEF_REPLY_B,
    GET_REVOC_REG_DEF_REPLY_A,
    GET_REVOC_REG_DEF_REPLY_B,
    GET_REVOC_REG_DELTA_REPLY_A,
    GET_REVOC_REG_DELTA_REPLY_B,
    GET_REVOC_REG_DELTA_REPLY_C,
    GET_NYM_REPLY,
    GET_SCHEMA_REPLY_A,
    GET_SCHEMA_REPLY_B,
    RAW_HEX_LEAF,
    SHA256_AUDIT_PATH,
)


class TestSubTrie(TestCase):
    def test_get_setter_root_hash(self):
        test_trie = SubTrie()
        test_trie.root_hash = 530343892119126197
        assert test_trie.root_hash == 530343892119126197

    def test_get_blank_node(self):
        assert SubTrie._get_node_type(b"") == 0

    async def test_verify_spv_proof_catch_exception(self):
        assert not await SubTrie.verify_spv_proof(
            expected_value="test", proof_nodes="test"
        )


class TestMPTStateProofValidation(TestCase):
    async def test_validate_get_nym(self):
        reply = GET_NYM_REPLY
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply),
            expected_value=prepare_for_state_read(reply),
        )

    async def test_validate_get_attrib(self):
        reply = GET_ATTRIB_REPLY
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply),
            expected_value=prepare_for_state_read(reply),
        )

    async def test_validate_get_schema(self):
        reply_a = GET_SCHEMA_REPLY_A
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_a),
            expected_value=prepare_for_state_read(reply_a),
        )
        reply_b = GET_SCHEMA_REPLY_B
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_b),
            expected_value=prepare_for_state_read(reply_b),
        )

    async def test_validate_get_claim_def(self):
        reply_a = GET_CLAIM_DEF_REPLY_A
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_a),
            expected_value=prepare_for_state_read(reply_a),
        )
        reply_b = GET_CLAIM_DEF_REPLY_B
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_b),
            expected_value=prepare_for_state_read(reply_b),
        )
        reply_c = GET_CLAIM_DEF_REPLY_INVALID
        assert not await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_c),
            expected_value=prepare_for_state_read(reply_c),
        )

    async def test_validate_get_revoc_reg(self):
        reply_a = GET_REVOC_REG_REPLY_A
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_a),
            expected_value=prepare_for_state_read(reply_a),
        )
        reply_b = GET_REVOC_REG_REPLY_B
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_b),
            expected_value=prepare_for_state_read(reply_b),
        )

    async def test_validate_get_revoc_reg_def(self):
        reply_a = GET_REVOC_REG_DEF_REPLY_A
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_a),
            expected_value=prepare_for_state_read(reply_a),
        )
        reply_b = GET_REVOC_REG_DEF_REPLY_B
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_b),
            expected_value=prepare_for_state_read(reply_b),
        )

    async def test_validate_get_revoc_reg_delta(self):
        reply_a = GET_REVOC_REG_DELTA_REPLY_A
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_a),
            expected_value=prepare_for_state_read(reply_a),
        )
        reply_b = GET_REVOC_REG_DELTA_REPLY_C
        assert await SubTrie.verify_spv_proof(
            proof_nodes=get_proof_nodes(reply_b),
            expected_value=prepare_for_state_read(reply_b),
        )
        reply_c = GET_REVOC_REG_DELTA_REPLY_B
        proof_nodes = get_proof_nodes(reply_c)
        expected_values = prepare_for_state_read(reply_c)
        assert await SubTrie.verify_spv_proof(
            proof_nodes=proof_nodes[0],
            expected_value=expected_values[0],
        )
        assert await SubTrie.verify_spv_proof(
            proof_nodes=proof_nodes[1],
            expected_value=expected_values[1],
        )


class TestMerkleRootHashValidation(TestCase):
    async def test_verify_leaf_inclusion_x(self):
        merkle_verifier = MerkleVerifier(HexTreeHasher())
        leaf_index = 848049
        tree_size = 3630887
        expected_root_hash = (
            b"78316a05c9bcf14a3a4548f5b854a9adfcd46a4c034401b3ce7eb7ac2f1d0ecb"
        )
        assert (
            await merkle_verifier.calculate_root_hash(
                RAW_HEX_LEAF,
                leaf_index,
                SHA256_AUDIT_PATH[:],
                tree_size,
            )
            == expected_root_hash
        )
