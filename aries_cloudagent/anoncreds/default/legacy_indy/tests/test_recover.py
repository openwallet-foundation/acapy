"""Test Recover."""

import hashlib
from unittest import IsolatedAsyncioTestCase

import aiohttp
import base58
import indy_vdr
import pytest
from anoncreds import RevocationRegistryDefinition

from aries_cloudagent.tests import mock

from ....models.anoncreds_revocation import RevList, RevRegDef, RevRegDefValue
from ..recover import (
    RevocRecoveryException,
    _check_tails_hash_for_inconsistency,
    fetch_txns,
    generate_ledger_rrrecovery_txn,
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
            await fetch_txns(
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
        "aries_cloudagent.anoncreds.default.legacy_indy.recover._check_tails_hash_for_inconsistency"
    )
    async def test_fetch_txns(self, *_):
        result = await fetch_txns(
            GENESIS,
            "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            "CsQY9MGeD3CQP4EyuVFo5m",
        )
        assert isinstance(result, tuple)

    @mock.patch(
        "aries_cloudagent.anoncreds.default.legacy_indy.recover.fetch_txns",
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
    async def test_generate_ledger_rrrecovery_txn(self):

        # Has updates
        result = await generate_ledger_rrrecovery_txn(
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
        result = await generate_ledger_rrrecovery_txn(
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

        # Logs waring when ledger has revoked indexes not in wallet
        with mock.patch(
            "aries_cloudagent.anoncreds.default.legacy_indy.recover.LOGGER"
        ) as mock_logger:
            result = await generate_ledger_rrrecovery_txn(
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
