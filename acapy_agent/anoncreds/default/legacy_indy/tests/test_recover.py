"""Test Recover."""

import hashlib
from unittest import IsolatedAsyncioTestCase

import aiohttp
import base58
import indy_vdr
import pytest
from anoncreds import RevocationRegistryDefinition

from .....revocation_anoncreds.models.issuer_cred_rev_record import IssuerCredRevRecord

from .....connections.models.conn_record import ConnRecord
from .....ledger.base import BaseLedger
from .....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from .....messaging.responder import BaseResponder
from .....protocols.endorse_transaction.v1_0.manager import TransactionManager
from .....tests import mock
from .....utils.testing import create_test_profile
from ....models.revocation import RevList, RevRegDef, RevRegDefValue
from ..recover import (
    RevocRecoveryException,
    _check_tails_hash_for_inconsistency,
    _get_endorser_info,
    _get_genesis_transactions,
    _get_ledger_accumulator,
    _get_revoked_discrepancies,
    _send_txn,
    _track_retry,
    fetch_transaction_and_revoked_credentials_from_ledger,
    fix_ledger_entry,
    generate_ledger_revocation_registry_recovery_txn,
)

GENESIS = '{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node1","blskey":"4N8aUNHSgjQVgkpm8nhNEfDf6txHznoYREg9kirmJrkivgL4oSEimFF6nsQ6M41QvhM2Z33nves5vfSn9n1UwNFJBYtWVnHYMATn76vLuL3zU88KyeAYcHfsih3He6UHcXDxcaecHVz6jhCYz1P2UZn2bDVruL5wXpehgBfBaLKm3Ba","blskey_pop":"RahHYiCvoNCtPTrVtP7nMC5eTYrsUA8WjXbdhNc8debh1agE9bGiJxWBXYNFbnJXoXhWFMvyqhqhRoq737YQemH5ik9oL7R4NTTCz2LEZhkgLJzB3QRQqJyBNyv7acbdHrAT8nQ9UkLbaVL9NBpnWXBTw4LEMePaSHEw66RzPNdAX1","client_ip":"172.17.0.2","client_port":9702,"node_ip":"172.17.0.2","node_port":9701,"services":["VALIDATOR"]},"dest":"Gw6pDLhcBcoQesN72qfotTgFa7cbuqZpkX3Xo6pLhPhv"},"metadata":{"from":"Th7MpTaRZVRYnPiabds81Y"},"type":"0"},"txnMetadata":{"seqNo":1,"txnId":"fea82e10e894419fe2bea7d96296a6d46f50f93f9eeda954ec461b2ed2950b62"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node2","blskey":"37rAPpXVoxzKhz7d9gkUe52XuXryuLXoM6P6LbWDB7LSbG62Lsb33sfG7zqS8TK1MXwuCHj1FKNzVpsnafmqLG1vXN88rt38mNFs9TENzm4QHdBzsvCuoBnPH7rpYYDo9DZNJePaDvRvqJKByCabubJz3XXKbEeshzpz4Ma5QYpJqjk","blskey_pop":"Qr658mWZ2YC8JXGXwMDQTzuZCWF7NK9EwxphGmcBvCh6ybUuLxbG65nsX4JvD4SPNtkJ2w9ug1yLTj6fgmuDg41TgECXjLCij3RMsV8CwewBVgVN67wsA45DFWvqvLtu4rjNnE9JbdFTc1Z4WCPA3Xan44K1HoHAq9EVeaRYs8zoF5","client_ip":"172.17.0.2","client_port":9704,"node_ip":"172.17.0.2","node_port":9703,"services":["VALIDATOR"]},"dest":"8ECVSk179mjsjKRLWiQtssMLgp6EPhWXtaYyStWPSGAb"},"metadata":{"from":"EbP4aYNeTHL6q385GuVpRV"},"type":"0"},"txnMetadata":{"seqNo":2,"txnId":"1ac8aece2a18ced660fef8694b61aac3af08ba875ce3026a160acbc3a3af35fc"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node3","blskey":"3WFpdbg7C5cnLYZwFZevJqhubkFALBfCBBok15GdrKMUhUjGsk3jV6QKj6MZgEubF7oqCafxNdkm7eswgA4sdKTRc82tLGzZBd6vNqU8dupzup6uYUf32KTHTPQbuUM8Yk4QFXjEf2Usu2TJcNkdgpyeUSX42u5LqdDDpNSWUK5deC5","blskey_pop":"QwDeb2CkNSx6r8QC8vGQK3GRv7Yndn84TGNijX8YXHPiagXajyfTjoR87rXUu4G4QLk2cF8NNyqWiYMus1623dELWwx57rLCFqGh7N4ZRbGDRP4fnVcaKg1BcUxQ866Ven4gw8y4N56S5HzxXNBZtLYmhGHvDtk6PFkFwCvxYrNYjh","client_ip":"172.17.0.2","client_port":9706,"node_ip":"172.17.0.2","node_port":9705,"services":["VALIDATOR"]},"dest":"DKVxG2fXXTU8yT5N7hGEbXB3dfdAnYv1JczDUHpmDxya"},"metadata":{"from":"4cU41vWW82ArfxJxHkzXPG"},"type":"0"},"txnMetadata":{"seqNo":3,"txnId":"7e9f355dffa78ed24668f0e0e369fd8c224076571c51e2ea8be5f26479edebe4"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node4","blskey":"2zN3bHM1m4rLz54MJHYSwvqzPchYp8jkHswveCLAEJVcX6Mm1wHQD1SkPYMzUDTZvWvhuE6VNAkK3KxVeEmsanSmvjVkReDeBEMxeDaayjcZjFGPydyey1qxBHmTvAnBKoPydvuTAqx5f7YNNRAdeLmUi99gERUU7TD8KfAa6MpQ9bw","blskey_pop":"RPLagxaR5xdimFzwmzYnz4ZhWtYQEj8iR5ZU53T2gitPCyCHQneUn2Huc4oeLd2B2HzkGnjAff4hWTJT6C7qHYB1Mv2wU5iHHGFWkhnTX9WsEAbunJCV2qcaXScKj4tTfvdDKfLiVuU2av6hbsMztirRze7LvYBkRHV3tGwyCptsrP","client_ip":"172.17.0.2","client_port":9708,"node_ip":"172.17.0.2","node_port":9707,"services":["VALIDATOR"]},"dest":"4PS3EDQ3dW1tci1Bp6543CfuuebjFrg36kLAUcskGfaA"},"metadata":{"from":"TWwCRQRZ2ZHMJFn9TzLp7W"},"type":"0"},"txnMetadata":{"seqNo":4,"txnId":"aa5e817d7cc626170eca175822029339a444eb0ee8f0bd20d3b0b76e566fb008"},"ver":"1"}'


rev_reg_def = RevRegDef(
    tag="tag",
    cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
    value=RevRegDefValue(
        max_cred_num=100,
        public_keys={
            "accum_key": {"z": "1 0BB...386"},
        },
        tails_hash="58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
        tails_location="http://tails-server.com",
    ),
    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
    type="CL_ACCUM",
)


@pytest.mark.anoncreds
class TestLegacyIndyRecover(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.get_revoc_reg_delta = mock.CoroutineMock(
            return_value=(
                {"value": {"revoked": [1], "accum": "accum"}},
                1234567890,
            )
        )
        mock_ledger.pool = mock.MagicMock(
            genesis_txns="dummy genesis transactions",
        )

        self.ledger = mock_ledger

        self.profile = await create_test_profile()
        self.profile._context.injector.bind_instance(BaseLedger, self.ledger)

        mock_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile._context.injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_executor
        )

    @mock.patch.object(
        indy_vdr,
        "open_pool",
        mock.CoroutineMock(
            return_value=mock.MagicMock(
                submit_request=mock.CoroutineMock(return_value={"data": {}})
            )
        ),
    )
    async def test_fetch_txns_empty_data_from_ledger(self, *_):
        with self.assertRaises(RevocRecoveryException):
            await fetch_transaction_and_revoked_credentials_from_ledger(
                GENESIS,
                "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                "CsQY9MGeD3CQP4EyuVFo5m",
            )

    @mock.patch.object(
        RevocationRegistryDefinition,
        "load",
        return_value=rev_reg_def.value,
    )
    @mock.patch.object(
        indy_vdr,
        "open_pool",
        mock.CoroutineMock(
            return_value=mock.MagicMock(
                submit_request=mock.CoroutineMock(
                    return_value={
                        "data": {
                            "ver": "1.0",
                            "value": {
                                "accum_to": {},
                                "revoked": [1, 0, 1, 0],
                            },
                        }
                    }
                )
            )
        ),
    )
    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover._check_tails_hash_for_inconsistency"
    )
    async def test_fetch_txns(self, *_):
        result = await fetch_transaction_and_revoked_credentials_from_ledger(
            GENESIS,
            "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            "CsQY9MGeD3CQP4EyuVFo5m",
        )
        assert isinstance(result, tuple)

    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.fetch_transaction_and_revoked_credentials_from_ledger",
        mock.CoroutineMock(
            return_value=(
                {
                    "ver": "1.0",
                    "value": {
                        "accum": "2 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C"
                    },
                },
                {0, 1, 2},
            )
        ),
    )
    async def test_generate_ledger_revocation_registry_recovery_txn(self):
        # Has updates
        result = await generate_ledger_revocation_registry_recovery_txn(
            GENESIS,
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[1, 1, 1, 1],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
        )
        assert result != {}
        # Doesn't have updates
        result = await generate_ledger_revocation_registry_recovery_txn(
            GENESIS,
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[1, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
        )
        assert result == {}

        # Logs warning when ledger has revoked indexes not in wallet
        with mock.patch(
            "acapy_agent.anoncreds.default.legacy_indy.recover.LOGGER"
        ) as mock_logger:
            result = await generate_ledger_revocation_registry_recovery_txn(
                GENESIS,
                RevList(
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                    revocation_list=[1, 0, 0, 0],
                    timestamp=1669640864487,
                    rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                ),
            )
            assert mock_logger.warning.called
            assert result == {}

    @mock.patch.object(
        aiohttp,
        "ClientSession",
        mock.MagicMock(
            return_value=mock.MagicMock(
                get=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        read=mock.CoroutineMock(return_value=b"some data")
                    )
                )
            )
        ),
    )
    @mock.patch.object(
        base58,
        "b58encode",
        side_effect=[
            b"58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
            b"58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxz",
        ],
    )
    @mock.patch.object(
        hashlib,
        "sha256",
        return_value=mock.MagicMock(digest=mock.MagicMock()),
    )
    async def test_check_tails_hash_for_inconsistency(self, *_):
        # Matches
        await _check_tails_hash_for_inconsistency(
            "http://tails-server.com", "58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt"
        )
        # Mismatch
        with self.assertRaises(RevocRecoveryException):
            await _check_tails_hash_for_inconsistency(
                "http://tails-server.com",
                "58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
            )

    async def test_track_retry_no_cache(self):
        # Should not raise
        await _track_retry(None, "accum")

    async def test_track_retry_first_time(self):
        cache = mock.MagicMock()
        cache.get = mock.CoroutineMock(return_value=None)
        cache.set = mock.CoroutineMock()

        await _track_retry(cache, "accum")

        cache.set.assert_called_once_with("accum", 5)

    async def test_track_retry_decrement(self):
        cache = mock.MagicMock()
        cache.get = mock.CoroutineMock(return_value=3)
        cache.set = mock.CoroutineMock()

        await _track_retry(cache, "accum")

        cache.set.assert_called_once_with("accum", 2)

    async def test_track_retry_exhausted(self):
        cache = mock.MagicMock()
        cache.get = mock.CoroutineMock(return_value=0)
        cache.set = mock.CoroutineMock()

        with mock.patch(
            "acapy_agent.anoncreds.default.legacy_indy.recover.LOGGER"
        ) as logger:
            await _track_retry(cache, "accum")

            logger.error.assert_called_once()

    def test_get_revoked_discrepancies(self):
        rec1 = mock.MagicMock(
            state=IssuerCredRevRecord.STATE_REVOKED,
            cred_rev_id="1",
            rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
        )
        rec2 = mock.MagicMock(
            state=IssuerCredRevRecord.STATE_REVOKED,
            cred_rev_id="2",
            rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
        )
        rec3 = mock.MagicMock(
            state="active",
            cred_rev_id="3",
            rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
        )

        rev_reg_delta = {"value": {"revoked": [1]}}

        revoked_ids, rec_count = _get_revoked_discrepancies(
            [rec1, rec2, rec3], rev_reg_delta
        )

        assert revoked_ids == [1, 2]
        assert rec_count == 1  # only "2" missing from ledger

    async def test_get_ledger_accum(self):
        result = await _get_ledger_accumulator(self.ledger, "rev-reg-id")

        assert result == "accum"

    def test_get_genesis_transactions_from_settings(self):
        profile = mock.MagicMock()
        profile.context.settings.get.return_value = "GENESIS_TXNS"

        result = _get_genesis_transactions(profile)

        assert result == "GENESIS_TXNS"

    def test_get_genesis_transactions_from_ledger(self):
        result = _get_genesis_transactions(self.profile)

        assert result == "dummy genesis transactions"

    async def test_fix_ledger_entry_no_discrepancies(self):
        rev_list = mock.MagicMock()
        rev_list.rev_reg_def_id = "rev-reg-id"

        result = await fix_ledger_entry(
            self.profile,
            rev_list,
            apply_ledger_update=False,
            genesis_transactions="GENESIS",
        )

        # No discrepancies → no recovery txn
        assert result[1] == {}
        assert result[2] == {}

    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.generate_ledger_revocation_registry_recovery_txn",
        mock.CoroutineMock(return_value={"value": "txn"}),
    )
    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.IssuerCredRevRecord.query_by_ids",
        mock.CoroutineMock(
            return_value=[
                IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_REVOKED,
                    cred_rev_id="1",
                    rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
                )
            ],
        ),
    )
    async def test_fix_ledger_entry_recovery_no_apply(self):
        rev_list = mock.MagicMock()
        rev_list.rev_reg_def_id = "rev-reg-id"

        result = await fix_ledger_entry(
            self.profile,
            rev_list,
            apply_ledger_update=False,
            genesis_transactions="GENESIS",
        )

        assert result[0] == {"value": {"revoked": [1], "accum": "accum"}}
        assert result[1] == {}
        assert result[2] == {}

    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.generate_ledger_revocation_registry_recovery_txn",
        mock.CoroutineMock(return_value={"value": "txn"}),
    )
    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.IssuerCredRevRecord.query_by_ids",
        mock.CoroutineMock(
            return_value=[
                IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_REVOKED,
                    cred_rev_id="1",
                    rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
                ),
                IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_REVOKED,
                    cred_rev_id="2",
                    rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
                ),
            ],
        ),
    )
    async def test_fix_ledger_entry_recovery_apply_without_update(
        self,
    ):
        rev_list = RevList(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            rev_reg_def_id="rev-reg-id",
            current_accumulator="21 124C594B6B20E41B681E",
            revocation_list=[1, 0, 0, 0],
        )

        result = await fix_ledger_entry(
            self.profile,
            rev_list,
            apply_ledger_update=False,
            genesis_transactions="GENESIS",
        )

        assert result[0] == {"value": {"revoked": [1], "accum": "accum"}}
        assert result[1] == {"value": "txn"}
        assert result[2] == {}

    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.generate_ledger_revocation_registry_recovery_txn",
        mock.CoroutineMock(return_value={"value": "txn"}),
    )
    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.recover.IssuerCredRevRecord.query_by_ids",
        mock.CoroutineMock(
            return_value=[
                IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_REVOKED,
                    cred_rev_id="1",
                    rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
                ),
                IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_REVOKED,
                    cred_rev_id="2",
                    rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:tag",
                ),
            ],
        ),
    )
    async def test_fix_ledger_entry_recovery_apply_with_correct_response_from_ledger(
        self,
    ):
        rev_list = RevList(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            rev_reg_def_id="rev-reg-id",
            current_accumulator="21 124C594B6B20E41B681E",
            revocation_list=[1, 0, 0, 0],
        )

        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.send_revoc_reg_entry = mock.CoroutineMock(
            return_value={"result": {"data": {"value": {"accum": "accum"}}}}
        )
        mock_ledger.get_revoc_reg_delta = mock.CoroutineMock(
            return_value=(
                {"value": {"revoked": [1], "accum": "accum"}},
                1234567890,
            )
        )
        mock_ledger.pool = mock.MagicMock(
            genesis_txns="dummy genesis transactions",
        )

        self.ledger = mock_ledger

        self.profile = await create_test_profile()
        self.profile._context.injector.bind_instance(BaseLedger, self.ledger)

        mock_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile._context.injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_executor
        )

        result = await fix_ledger_entry(
            self.profile,
            rev_list,
            apply_ledger_update=True,
            genesis_transactions="GENESIS",
        )

        assert result[0] == {"value": {"revoked": [1], "accum": "accum"}}
        assert result[1] == {"value": "txn"}
        assert result[2] == {}

    @mock.patch.object(
        ConnRecord, "retrieve_by_alias", mock.CoroutineMock(return_value=None)
    )
    async def test_get_endorser_info_no_connection_id(self):
        profile = await create_test_profile(
            {
                "endorser.connection_id": None,
            }
        )
        endorser_did, connection = await _get_endorser_info(profile)
        assert endorser_did is None
        assert connection is None

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_alias",
        mock.CoroutineMock(return_value=[ConnRecord(connection_id="conn-id")]),
    )
    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        mock.CoroutineMock(return_value=ConnRecord(connection_id="conn-id")),
    )
    @mock.patch.object(
        ConnRecord,
        "metadata_get",
        mock.CoroutineMock(return_value={"endorser_did": "endorser-did"}),
    )
    async def test_get_endorser_info_when_author(self):
        profile = await create_test_profile(
            {
                "endorser.author": True,
                "endorser.endorser_alias": "endorser",
            }
        )
        endorser_did, connection = await _get_endorser_info(profile)
        assert endorser_did == "endorser-did"
        assert isinstance(connection, ConnRecord)

    async def test_send_txn_without_endorser(self):
        # Should not raise
        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.send_revoc_reg_entry = mock.CoroutineMock(
            return_value={"result": {"data": {"value": {"accum": "accum"}}}}
        )
        mock_ledger.get_revoc_reg_delta = mock.CoroutineMock(
            return_value=(
                {"value": {"revoked": [1], "accum": "accum"}},
                1234567890,
            )
        )
        mock_ledger.pool = mock.MagicMock(
            genesis_txns="dummy genesis transactions",
        )

        self.ledger = mock_ledger

        self.profile = await create_test_profile()
        self.profile._context.injector.bind_instance(BaseLedger, self.ledger)

        mock_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile._context.injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_executor
        )

        await _send_txn(
            profile=self.profile,
            ledger=self.ledger,
            rev_list=RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                rev_reg_def_id="rev-reg-id",
                current_accumulator="21 124C594B6B20E41B681E",
                revocation_list=[1, 0, 0, 0],
            ),
            recovery_txn={"value": "txn"},
            endorser_did=None,
            connection=None,
        )

    @mock.patch.object(
        TransactionManager,
        "create_record",
        mock.CoroutineMock(return_value={"txn_id": "txn-id"}),
    )
    @mock.patch.object(
        TransactionManager,
        "create_request",
        mock.CoroutineMock(return_value=({"request_id": "request-id"}, "ledger-id")),
    )
    async def test_send_txn_with_endorser_happy_path(self):
        # Should not raise
        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.send_revoc_reg_entry = mock.CoroutineMock(
            return_value=(
                "rev-reg-def-id",
                {"signed_txn": "txn"},
            )
        )

        mock_ledger.get_revoc_reg_delta = mock.CoroutineMock(
            return_value=(
                {"value": {"revoked": [1], "accum": "accum"}},
                1234567890,
            )
        )
        mock_ledger.pool = mock.MagicMock(
            genesis_txns="dummy genesis transactions",
        )

        self.ledger = mock_ledger

        self.profile = await create_test_profile()
        self.profile._context.injector.bind_instance(BaseLedger, self.ledger)
        mock_responder = mock.MagicMock(BaseResponder, autospec=True)
        self.profile._context.injector.bind_instance(BaseResponder, mock_responder)

        mock_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile._context.injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_executor
        )

        await _send_txn(
            profile=self.profile,
            ledger=self.ledger,
            rev_list=RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                rev_reg_def_id="rev-reg-id",
                current_accumulator="21 124C594B6B20E41B681E",
                revocation_list=[1, 0, 0, 0],
            ),
            recovery_txn={"value": "txn"},
            endorser_did="endorser-did",
            connection=mock.MagicMock(ConnRecord, autospec=True),
        )
