"""Tests for Domain Txn Handling Utils."""
import base58
import json

from copy import deepcopy

from unittest import TestCase

from ..domain_txn_handler import (
    _extract_attr_typed_value,
    parse_attr_txn,
    decode_state_value,
    extract_params_write_request,
    hash_of,
    make_state_path_for_attr,
    prepare_attr_for_state,
    prepare_nym_for_state,
    prepare_revoc_reg_entry_for_state,
    prepare_schema_for_state,
    prepare_get_claim_def_for_state,
    prepare_claim_def_for_state,
    prepare_revoc_def_for_state,
    prepare_get_revoc_reg_entry_for_state,
    prepare_revoc_reg_entry_accum_for_state,
)

CLAIM_DEF_TXN = {
    "result": {
        "txn": {
            "data": {
                "ver": 1,
                "signature_type": "CL",
                "ref": 10,
                "tag": "some_tag",
                "data": {"primary": "....", "revocation": "...."},
            },
            "metadata": {
                "reqId": 1514280215504647,
                "from": "L5AD5g65TDQr1PPHHRoiGf",
                "endorser": "D6HG5g65TDQr1PPHHRoiGf",
                "digest": "6cee82226c6e276c983f46d03e3b3d10436d90b67bf33dc67ce9901b44dbc97c",
                "payloadDigest": "21f0f5c158ed6ad49ff855baf09a2ef9b4ed1a8015ac24bccc2e0106cd905685",
            },
        },
        "txnMetadata": {
            "txnTime": 1513945121,
            "seqNo": 10,
            "txnId": "HHAD5g65TDQr1PPHHRoiGf2L5AD5g65TDQr1PPHHRoiGf1|Degree1|CL|key1",
        },
    }
}

REVOC_REG_ENTRY_TXN = {
    "result": {
        "txn": {
            "data": {
                "ver": 1,
                "revocRegDefId": "L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1",
                "revocDefType": "CL_ACCUM",
                "value": {
                    "accum": "accum_value",
                    "prevAccum": "prev_acuum_value",
                    "issued": [],
                    "revoked": [10, 36, 3478],
                },
            },
        },
        "txnMetadata": {
            "txnTime": 1513945121,
            "seqNo": 10,
            "txnId": "5:L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1",
        },
    }
}


class TestDomainTxnHandler(TestCase):
    """Domain Txn Handler Tests"""

    def test_extract_attr_typed_value(self):
        test_txn_data = {"test": {...}}
        with self.assertRaises(ValueError) as cm:
            _extract_attr_typed_value(test_txn_data)
            assert "ATTR should have one" in cm
        test_txn_data = {
            "raw": {...},
            "enc": {...},
            "hash": {...},
        }
        with self.assertRaises(ValueError) as cm:
            _extract_attr_typed_value(test_txn_data)
            assert "ATTR should have only one" in cm

    def test_parse_attr_txn(self):
        test_txn_data = {"raw": '{"name": "Alice"}'}
        assert parse_attr_txn(test_txn_data) == ("raw", "name", '{"name": "Alice"}')
        test_txn_data = {"enc": "test"}
        assert parse_attr_txn(test_txn_data) == ("enc", "test", "test")
        test_txn_data = {"hash": "test"}
        assert parse_attr_txn(test_txn_data) == ("hash", "test", None)

    def test_decode_state_value(self):
        test_value = "test_value"
        test_lsn = "100"
        test_lut = "test_lut"
        test_encoded = {"val": test_value, "lsn": test_lsn, "lut": test_lut}
        assert decode_state_value(json.dumps(test_encoded)) == (
            test_value,
            test_lsn,
            test_lut,
        )

    def test_hash_of(self):
        test = {"test": "test"}
        assert hash_of(test)
        test = "123"
        assert hash_of(test)
        test = b"234"
        assert hash_of(test)

    def test_make_state_path_for_attr(self):
        assert b"did1:1:attrName1" == make_state_path_for_attr(
            "did1", "attrName1", attr_is_hash=True
        )
        assert (
            b"did1:1:677a81e8649df8f1a1e8af7709a5ece1d965cb684b2c185272114c5cc3b7ec49"
            == make_state_path_for_attr("did1", "attrName1", attr_is_hash=False)
        )
        assert (
            b"did1:1:677a81e8649df8f1a1e8af7709a5ece1d965cb684b2c185272114c5cc3b7ec49"
            == make_state_path_for_attr("did1", "attrName1")
        )

    def test_prepare_attr_for_state(self):
        txn = {
            "result": {
                "txn": {
                    "data": {
                        "ver": 1,
                        "dest": "N22KY2Dyvmuu2PyyqSFKue",
                        "raw": '{"name":"Alice"}',
                    },
                },
                "txnMetadata": {
                    "txnTime": 1513945121,
                    "seqNo": 10,
                    "txnId": "N22KY2Dyvmuu2PyyqSFKue|02",
                },
            }
        }
        txn = txn.get("result")
        path, value_bytes = prepare_attr_for_state(txn)
        assert (
            path
            == b"N22KY2Dyvmuu2PyyqSFKue:1:82a3537ff0dbce7eec35d69edc3a189ee6f17d82f353a553f9aa96cb0be3ce89"
        )
        assert (
            value_bytes
            == b'{"lsn": 10, "lut": 1513945121, "val": "6d4a333838d0ef96756cccc680af2531075c512502fb68c5503c63d93de859b3"}'
        )
        path = prepare_attr_for_state(txn, path_only=True)
        assert (
            path
            == b"N22KY2Dyvmuu2PyyqSFKue:1:82a3537ff0dbce7eec35d69edc3a189ee6f17d82f353a553f9aa96cb0be3ce89"
        )

    def test_prepare_nym_for_state(self):
        txn = {
            "result": {
                "txn": {
                    "data": {
                        "dest": "N22KY2Dyvmuu2PyyqSFKue",
                    },
                },
            }
        }
        txn = txn.get("result")
        assert prepare_nym_for_state(txn)

    def test_prepare_schema_for_state(self):
        txn = {
            "result": {
                "txn": {
                    "type": "101",
                    "protocolVersion": 2,
                    "data": {
                        "ver": 1,
                        "data": {
                            "name": "Degree",
                            "version": "1.0",
                            "attr_names": [
                                "undergrad",
                                "last_name",
                                "first_name",
                                "birth_date",
                                "postgrad",
                                "expiry_date",
                            ],
                        },
                    },
                    "metadata": {
                        "reqId": 1514280215504647,
                        "from": "L5AD5g65TDQr1PPHHRoiGf",
                        "endorser": "D6HG5g65TDQr1PPHHRoiGf",
                        "digest": "6cee82226c6e276c983f46d03e3b3d10436d90b67bf33dc67ce9901b44dbc97c",
                        "payloadDigest": "21f0f5c158ed6ad49ff855baf09a2ef9b4ed1a8015ac24bccc2e0106cd905685",
                    },
                },
                "txnMetadata": {
                    "txnTime": 1513945121,
                    "seqNo": 10,
                    "txnId": "L5AD5g65TDQr1PPHHRoiGf1|Degree|1.0",
                },
            }
        }
        txn = txn.get("result")
        path, value_bytes = prepare_schema_for_state(txn)
        assert path == b"L5AD5g65TDQr1PPHHRoiGf:2:Degree:1.0"
        assert (
            prepare_schema_for_state(txn, path_only=True)
            == b"L5AD5g65TDQr1PPHHRoiGf:2:Degree:1.0"
        )

    def test_prepare_get_claim_def_for_state(self):
        txn = deepcopy(CLAIM_DEF_TXN)
        txn.get("result").get("txn").get("data").pop("ref")
        with self.assertRaises(ValueError) as cm:
            prepare_get_claim_def_for_state(txn)
            assert "ref field is absent, but it must contain schema seq no" in cm

    def test_prepare_claim_def_for_state(self):
        txn = deepcopy(CLAIM_DEF_TXN.get("result"))
        txn.get("txn").get("data").pop("ref")
        with self.assertRaises(ValueError) as cm:
            prepare_claim_def_for_state(txn)
            assert "ref field is absent, but it must contain schema seq no" in cm

        txn = deepcopy(CLAIM_DEF_TXN.get("result"))
        txn.get("txn").get("data").pop("data")
        with self.assertRaises(ValueError) as cm:
            prepare_claim_def_for_state(txn)
            assert "data field is absent, but it must contain components of keys" in cm

        txn = deepcopy(CLAIM_DEF_TXN.get("result"))
        path, value_bytes = prepare_claim_def_for_state(txn)
        assert path == b"L5AD5g65TDQr1PPHHRoiGf:3:CL:10:some_tag"
        assert (
            prepare_claim_def_for_state(txn, path_only=True)
            == b"L5AD5g65TDQr1PPHHRoiGf:3:CL:10:some_tag"
        )

    def test_prepare_revoc_def_for_state(self):
        txn = {
            "result": {
                "txn": {
                    "type": "113",
                    "protocolVersion": 2,
                    "data": {
                        "ver": 1,
                        "id": "L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1",
                        "credDefId": "FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag",
                        "revocDefType": "CL_ACCUM",
                        "tag": "tag1",
                        "value": {
                            "maxCredNum": 1000000,
                            "tailsHash": "6619ad3cf7e02fc29931a5cdc7bb70ba4b9283bda3badae297",
                            "tailsLocation": "http://tails.location.com",
                            "issuanceType": "ISSUANCE_BY_DEFAULT",
                            "publicKeys": {},
                        },
                    },
                    "metadata": {
                        "reqId": 1514280215504647,
                        "from": "L5AD5g65TDQr1PPHHRoiGf",
                        "endorser": "D6HG5g65TDQr1PPHHRoiGf",
                        "digest": "6cee82226c6e276c983f46d03e3b3d10436d90b67bf33dc67ce9901b44dbc97c",
                        "payloadDigest": "21f0f5c158ed6ad49ff855baf09a2ef9b4ed1a8015ac24bccc2e0106cd905685",
                    },
                },
                "txnMetadata": {
                    "txnTime": 1513945121,
                    "seqNo": 10,
                    "txnId": "L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1",
                },
            },
        }
        txn = txn.get("result")
        path, value_bytes = prepare_revoc_def_for_state(txn)
        assert (
            path
            == b"L5AD5g65TDQr1PPHHRoiGf:4:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )
        assert (
            prepare_revoc_def_for_state(txn, path_only=True)
            == b"L5AD5g65TDQr1PPHHRoiGf:4:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )

    def test_prepare_get_revoc_reg_entry_for_state(self):
        assert prepare_get_revoc_reg_entry_for_state(REVOC_REG_ENTRY_TXN)
        assert prepare_get_revoc_reg_entry_for_state(REVOC_REG_ENTRY_TXN.get("result"))

    def test_prepare_revoc_reg_entry_for_state(self):
        path, value_bytes = prepare_revoc_reg_entry_for_state(
            REVOC_REG_ENTRY_TXN.get("result")
        )
        assert (
            path
            == b"5:L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )
        assert (
            prepare_revoc_reg_entry_for_state(
                REVOC_REG_ENTRY_TXN.get("result"), path_only=True
            )
            == b"5:L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )

    def test_prepare_revoc_reg_entry_accum_for_state(self):
        path, value_bytes = prepare_revoc_reg_entry_accum_for_state(REVOC_REG_ENTRY_TXN)
        assert (
            path
            == b"6:L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )
        path, value_bytes = prepare_revoc_reg_entry_accum_for_state(
            REVOC_REG_ENTRY_TXN.get("result")
        )
        assert (
            path
            == b"6:L5AD5g65TDQr1PPHHRoiGf:3:FC4aWomrA13YyvYC1Mxw7:3:CL:14:some_tag:CL_ACCUM:tag1"
        )

    def test_extract_params_write_request(self):
        write_request = {
            "result": {
                "txn": {
                    "data": {
                        "data": {
                            "attr_names": ["axuall_proof_id"],
                            "name": "manual_issuance",
                            "version": "4.1.0",
                        }
                    },
                    "metadata": {
                        "digest": "f440da62ab1c38601e41b5e148370b64af3183a2428f327cfb8ac83ca4cbc698",
                        "from": "F72i3Y3Q4i466efjYJYCHM",
                        "payloadDigest": "0ecfd475ed34635b6623bcbcda422ff90dee53f66de20a7441bca04ba0632670",
                        "reqId": 1634854863739554300,
                        "taaAcceptance": {
                            "mechanism": "for_session",
                            "taaDigest": "8cee5d7a573e4893b08ff53a0761a22a1607df3b3fcd7e75b98696c92879641f",
                            "time": 1600300800,
                        },
                    },
                    "protocolVersion": 2,
                    "type": "101",
                },
                "txnMetadata": {
                    "seqNo": 75335,
                    "txnId": "F72i3Y3Q4i466efjYJYCHM:2:manual_issuance:4.1.0",
                    "txnTime": 1634854863,
                },
                "ver": "1",
                "auditPath": [
                    "DhzuS5ZkyxUrQbRzbCfq3NDcTnTzFcJHYJYyTAqgMymT",
                    "AtYz5H13m1ZyFiGVVLwRL7au8muhCMwikeQrMwJBJ5d9",
                    "3GpqpZw4jymXDFm8Mf5gSMHSJ8r1wXutiZ1x26kxwWBE",
                    "EQyUpv9z64prPmDqkb8n2SzBtor3tGaNw4qZP2psG2wD",
                    "9fbpJjWbDuNbCrC7GQxjVxDGJ48k7rdBDf5ATu7PXVx3",
                    "CRbATGbi9DbN1pphXMcREVZTUUqsQbD9mN5ikKm1FkSc",
                    "E19R3Cty6iLtWBoxSqHLrxTSJSKpBtj3wJEdD98pS9g8",
                ],
                "ledgerSize": 75335,
                "reqSignature": {
                    "type": "ED25519",
                    "values": [
                        {
                            "from": "F72i3Y3Q4i466efjYJYCHM",
                            "value": "29sKMwQjm6r2BjpbJdFi1TGvowaxbi9nnAPP9LwPHhuBzwtfWwqJFg4Ur2xAWBLYfPLnMNNSgwwNesRSb1C1L72d",
                        }
                    ],
                },
                "rootHash": "4aM6yCpamk82Uqb414mNRpEdYkwdSMhi3HkXgN7YvRaX",
            }
        }
        txn = deepcopy(write_request)
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(txn)

        given_audit_path = [
            "DhzuS5ZkyxUrQbRzbCfq3NDcTnTzFcJHYJYyTAqgMymT",
            "AtYz5H13m1ZyFiGVVLwRL7au8muhCMwikeQrMwJBJ5d9",
            "3GpqpZw4jymXDFm8Mf5gSMHSJ8r1wXutiZ1x26kxwWBE",
            "EQyUpv9z64prPmDqkb8n2SzBtor3tGaNw4qZP2psG2wD",
            "9fbpJjWbDuNbCrC7GQxjVxDGJ48k7rdBDf5ATu7PXVx3",
            "CRbATGbi9DbN1pphXMcREVZTUUqsQbD9mN5ikKm1FkSc",
            "E19R3Cty6iLtWBoxSqHLrxTSJSKpBtj3wJEdD98pS9g8",
        ]
        expected_audit_path = [
            base58.b58decode(hash_str.encode("utf-8")) for hash_str in given_audit_path
        ]
        expected_hash = base58.b58decode(
            "4aM6yCpamk82Uqb414mNRpEdYkwdSMhi3HkXgN7YvRaX".encode("utf-8")
        )
        assert tree_size == 75335
        assert leaf_index == 75334
        assert expected_root_hash == expected_hash
        assert decoded_audit_path == expected_audit_path

        txn = deepcopy(write_request)
        txn = txn.get("result")
        (
            tree_size,
            leaf_index,
            decoded_audit_path,
            expected_root_hash,
        ) = extract_params_write_request(txn)

        assert tree_size == 75335
        assert leaf_index == 75334
        assert expected_root_hash == expected_hash
        assert decoded_audit_path == expected_audit_path

        txn = deepcopy(write_request)
        txn["result"]["txnMetadata"]["seqNo"] = 1000
        with self.assertRaises(Exception) as cm:
            extract_params_write_request(txn)
            assert "auditPath length does not match with given seqNo" in cm
