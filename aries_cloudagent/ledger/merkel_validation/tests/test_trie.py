import json

from asynctest import TestCase

from ..domain_txn_handler import (
    prepare_for_state_read,
    prepare_for_state_write,
    get_proof_nodes,
    extract_params_write_request,
)
from ..hasher import TreeHasher, HexTreeHasher
from ..trie import SubTrie
from ..merkel_verifier import MerkleVerifier

from test_data import (
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
    NYM_REPLY,
    ATTRIB_REPLY,
    SCHEMA_REPLY,
    CLAIM_DEF_REPLY,
    REVOC_REG_DEF_REPLY,
    REVOC_REG_REPLY,
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
    async def test_validate_nym(self):
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(NYM_REPLY)
        value = prepare_for_state_write(NYM_REPLY)
        merkle_verifier = MerkleVerifier(TreeHasher())
        calc_root_hash = await merkle_verifier.calculate_root_hash(
            value,
            leaf_index,
            decoded_audit_path[:],
            tree_size,
        )
        assert calc_root_hash == expected_root_hash

    async def test_validate_attrib(self):
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(ATTRIB_REPLY)
        key, value = prepare_for_state_write(ATTRIB_REPLY)
        merkle_verifier = MerkleVerifier(TreeHasher())
        calc_root_hash = await merkle_verifier.calculate_root_hash(
            value,
            leaf_index,
            decoded_audit_path[:],
            tree_size,
        )
        assert calc_root_hash == expected_root_hash

    async def test_validate_schema(self):
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(SCHEMA_REPLY)
        key, value = prepare_for_state_write(SCHEMA_REPLY)
        merkle_verifier = MerkleVerifier(TreeHasher())
        calc_root_hash = await merkle_verifier.calculate_root_hash(
            value,
            leaf_index,
            decoded_audit_path[:],
            tree_size,
        )
        assert calc_root_hash == expected_root_hash

    async def test_validate_claim_def(self):
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(CLAIM_DEF_REPLY)
        key, value = prepare_for_state_write(CLAIM_DEF_REPLY)
        merkle_verifier = MerkleVerifier(TreeHasher())
        calc_root_hash = await merkle_verifier.calculate_root_hash(
            value,
            leaf_index,
            decoded_audit_path[:],
            tree_size,
        )
        assert calc_root_hash == expected_root_hash

    async def test_validate_revoc_reg_def(self):
        pass

    async def test_validate_revoc_reg(self):
        pass
