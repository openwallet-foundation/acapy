import json

import indy_vdr
import pytest
import pytest_asyncio

from ...anoncreds.default.legacy_indy.registry import LegacyIndyRegistry
from ...cache.base import BaseCache
from ...cache.in_memory import InMemoryCache
from ...indy.issuer import IndyIssuer
from ...tests import mock
from ...utils.testing import create_test_profile
from ...wallet.base import BaseWallet
from ...wallet.did_info import DIDInfo
from ...wallet.did_method import SOV, DIDMethod, DIDMethods, HolderDefinedDid
from ...wallet.did_posture import DIDPosture
from ...wallet.error import WalletNotFoundError
from ...wallet.key_type import ED25519, KeyTypes
from ..endpoint_type import EndpointType
from ..indy_vdr import (
    BadLedgerRequestError,
    ClosedPoolError,
    IndyVdrLedger,
    IndyVdrLedgerPool,
    LedgerError,
    LedgerTransactionError,
    Role,
    VdrError,
)

from ...core.profile import Profile
from ...storage.askar import AskarStorage
from ..util import TAA_ACCEPTED_RECORD_TYPE

WEB = DIDMethod(
    name="web",
    key_types=[ED25519],
    rotation=True,
    holder_defined_did=HolderDefinedDid.REQUIRED,
)

TEST_TENANT_DID = "WgWxqztrNooG92RXvxSTWv"
TEST_SCHEMA_SEQ_NO = 4935
TEST_CRED_DEF_TAG = "tenant_tag"

TEST_CRED_DEF_ID = f"{TEST_TENANT_DID}:3:CL:{TEST_SCHEMA_SEQ_NO}:{TEST_CRED_DEF_TAG}"


@pytest_asyncio.fixture
async def ledger():
    did_methods = DIDMethods()
    did_methods.register(WEB)
    profile = await create_test_profile()
    profile.context.injector.bind_instance(DIDMethods, did_methods)
    profile.context.injector.bind_instance(BaseCache, InMemoryCache())
    profile.context.injector.bind_instance(KeyTypes, KeyTypes())

    ledger = IndyVdrLedger(IndyVdrLedgerPool("test-ledger"), profile)

    async def open():
        ledger.pool.handle = mock.MagicMock(indy_vdr.Pool)

    async def close():
        ledger.pool.handle = None

    with (
        mock.patch.object(ledger.pool, "open", open),
        mock.patch.object(ledger.pool, "close", close),
        mock.patch.object(
            ledger, "is_ledger_read_only", mock.CoroutineMock(return_value=False)
        ),
    ):
        yield ledger


@pytest.mark.indy_vdr
class TestIndyVdrLedger:
    @pytest.mark.asyncio
    async def test_aenter_aexit(self, ledger: IndyVdrLedger):
        assert ledger.pool_handle is None

        async with ledger as led:
            assert ledger.pool_handle

        assert ledger.pool_handle is None

    @pytest.mark.asyncio
    async def test_submit_pool_closed(self, ledger: IndyVdrLedger):
        with pytest.raises(ClosedPoolError):
            await ledger._submit("{}")

    @pytest.mark.asyncio
    async def test_submit_signed(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)
            test_msg = indy_vdr.ledger.build_get_txn_request(test_did.did, 1, 1)

        async with ledger:
            result = await ledger._submit(
                test_msg, sign=True, taa_accept=False, write_ledger=False
            )
            assert result.get("signature")
            assert result.get("taaAcceptance") is None

            result = await ledger._submit(
                test_msg, sign=True, taa_accept=True, write_ledger=False
            )
            assert result.get("signature")
            assert result.get("taaAcceptance") is None

            ledger.pool_handle.submit_request.assert_not_awaited()
            await ledger._submit(test_msg)
            ledger.pool_handle.submit_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_txn_author_agreement(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            with mock.patch.object(
                ledger.pool_handle,
                "submit_request",
                mock.CoroutineMock(
                    side_effect=[
                        {"data": {"aml": ".."}},
                        {"data": {"text": "text", "version": "1.0"}},
                    ]
                ),
            ):
                response = await ledger.fetch_txn_author_agreement()
                assert response == {
                    "aml_record": {"aml": ".."},
                    "taa_record": {
                        "text": "text",
                        "version": "1.0",
                        "digest": ledger.taa_digest("1.0", "text"),
                    },
                    "taa_required": True,
                }

    @pytest.mark.asyncio
    async def test_submit_signed_taa_accept(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)

        async with ledger:
            test_msg = indy_vdr.ledger.build_get_txn_request(test_did.did, 1, 1)

            await ledger.accept_txn_author_agreement(
                {
                    "text": "txt",
                    "version": "ver",
                    "digest": ledger.taa_digest("ver", "txt"),
                },
                mechanism="manual",
                accept_time=1000,
            )

            result = await ledger._submit(
                test_msg, sign=True, taa_accept=True, write_ledger=False
            )
            assert result.get("signature")
            assert result.get("taaAcceptance")

            # no accept_time
            await ledger.accept_txn_author_agreement(
                {
                    "text": "txt",
                    "version": "ver",
                    "digest": ledger.taa_digest("ver", "txt"),
                },
                mechanism="manual",
            )

    @pytest.mark.asyncio
    async def test_submit_unsigned(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            test_msg = indy_vdr.ledger.build_get_txn_request(None, 1, 1)

            result = await ledger._submit(
                test_msg, sign=False, taa_accept=False, write_ledger=False
            )
            assert result.get("signature") is None
            assert result.get("taaAcceptance") is None

            # no public DID
            with pytest.raises(BadLedgerRequestError):
                await ledger._submit(test_msg, sign=True, write_ledger=False)

    @pytest.mark.asyncio
    async def test_submit_unsigned_ledger_transaction_error(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            test_msg = indy_vdr.ledger.build_get_txn_request(None, 1, 1)

            ledger.pool_handle.submit_request.side_effect = VdrError(99, "message")
            with pytest.raises(LedgerTransactionError):
                await ledger._submit(test_msg, sign=False, taa_accept=False)

    @pytest.mark.asyncio
    async def test_txn_endorse(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_msg = indy_vdr.ledger.build_get_txn_request(None, 1, 1)

            async with ledger:
                # invalid request
                with pytest.raises(BadLedgerRequestError):
                    await ledger.txn_endorse(request_json="{}")

                # no public DID
                with pytest.raises(BadLedgerRequestError):
                    await ledger.txn_endorse(request_json=test_msg.body)

                test_did = await wallet.create_public_did(SOV, ED25519)
                test_msg.set_endorser(test_did.did)

                endorsed_json = await ledger.txn_endorse(request_json=test_msg.body)
                body = json.loads(endorsed_json)
                assert test_did.did in body["signatures"]

    @pytest.mark.asyncio
    async def test_send_schema(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)
            issuer = mock.MagicMock(IndyIssuer)
            issuer.create_schema.return_value = (
                "schema_issuer_did:schema_name:9.1",
                (
                    r'{"ver": "1.0", "id": "schema_issuer_did:schema_name:9.1", "name":'
                    r' "schema_name", "version": "9.1", "attrNames": ["a", "b"]}'
                ),
            )

        async with ledger:
            ledger.pool_handle.submit_request.return_value = {"txnMetadata": {"seqNo": 1}}

            with mock.patch.object(
                ledger,
                "check_existing_schema",
                mock.CoroutineMock(return_value=None),
            ):
                schema_id, _ = await ledger.create_and_send_schema(
                    issuer, "schema_name", "9.1", ["a", "b"]
                )

            issuer.create_schema.assert_awaited_once_with(
                test_did.did, "schema_name", "9.1", ["a", "b"]
            )

            ledger.pool_handle.submit_request.assert_awaited_once()

            assert schema_id == issuer.create_schema.return_value[0]

            # test endorsed
            schema_id, signed_txn = await ledger.create_and_send_schema(
                issuer=issuer,
                schema_name="schema_name",
                schema_version="9.1",
                attribute_names=["a", "b"],
                write_ledger=False,
                endorser_did=test_did.did,
            )
            assert schema_id == issuer.create_schema.return_value[0]
            txn = json.loads(signed_txn["signed_txn"])
            assert txn.get("endorser") == test_did.did
            assert txn.get("signature")

    @pytest.mark.asyncio
    async def test_send_schema_no_public_did(
        self,
        ledger: IndyVdrLedger,
    ):
        issuer = mock.MagicMock(IndyIssuer)
        async with ledger:
            with pytest.raises(BadLedgerRequestError):
                await ledger.create_and_send_schema(
                    issuer, "schema_name", "9.1", ["a", "b"]
                )

    @pytest.mark.asyncio
    async def test_send_schema_already_exists(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        issuer = mock.MagicMock(IndyIssuer)
        issuer.create_schema.return_value = (
            "schema_issuer_did:schema_name:9.1",
            (
                r'{"ver": "1.0", "id": "schema_issuer_did:schema_name:9.1", "name":'
                r' "schema_name", "version": "9.1", "attrNames": ["a", "b"]}'
            ),
        )

        async with ledger:
            with mock.patch.object(
                ledger,
                "check_existing_schema",
                mock.CoroutineMock(
                    return_value=(
                        issuer.create_schema.return_value[0],
                        {"schema": "result"},
                    )
                ),
            ) as mock_check:
                schema_id, schema_def = await ledger.create_and_send_schema(
                    issuer, "schema_name", "9.1", ["a", "b"]
                )
                assert schema_id == mock_check.return_value[0]
                assert schema_def == mock_check.return_value[1]

    @pytest.mark.asyncio
    async def test_send_schema_ledger_read_only(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        issuer = mock.MagicMock(IndyIssuer)
        issuer.create_schema.return_value = (
            "schema_issuer_did:schema_name:9.1",
            (
                r'{"ver": "1.0", "id": "schema_issuer_did:schema_name:9.1", "name":'
                r' "schema_name", "version": "9.1", "attrNames": ["a", "b"]}'
            ),
        )

        async with ledger:
            ledger.pool.read_only = True
            with (
                mock.patch.object(
                    ledger,
                    "check_existing_schema",
                    mock.CoroutineMock(return_value=False),
                ),
                mock.patch.object(
                    ledger,
                    "is_ledger_read_only",
                    mock.CoroutineMock(return_value=True),
                ),
            ):
                with pytest.raises(LedgerError):
                    await ledger.create_and_send_schema(
                        issuer, "schema_name", "9.1", ["a", "b"]
                    )

    @pytest.mark.asyncio
    async def test_send_schema_ledger_transaction_error(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        issuer = mock.MagicMock(IndyIssuer)
        issuer.create_schema.return_value = (
            "schema_issuer_did:schema_name:9.1",
            (
                r'{"ver": "1.0", "id": "schema_issuer_did:schema_name:9.1", "name":'
                r' "schema_name", "version": "9.1", "attrNames": ["a", "b"]}'
            ),
        )

        async with ledger:
            ledger.pool_handle.submit_request.side_effect = VdrError(99, "message")

            with mock.patch.object(
                ledger,
                "check_existing_schema",
                mock.CoroutineMock(return_value=False),
            ):
                with pytest.raises(LedgerTransactionError):
                    await ledger.create_and_send_schema(
                        issuer, "schema_name", "9.1", ["a", "b"]
                    )

    @pytest.mark.asyncio
    async def test_send_schema_no_indy_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            wallet.create_public_did = mock.CoroutineMock(
                return_value={
                    "result": {
                        "did": "did:web:doma.in",
                        "verkey": "verkey",
                        "posture": DIDPosture.PUBLIC.moniker,
                        "key_type": ED25519.key_type,
                        "method": WEB.method_name,
                    }
                }
            )
        issuer = mock.MagicMock(IndyIssuer)
        async with ledger:
            with pytest.raises(BadLedgerRequestError):
                await ledger.create_and_send_schema(
                    issuer, "schema_name", "9.1", ["a", "b"]
                )

    @pytest.mark.asyncio
    async def test_get_schema(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "seqNo": 99,
                "dest": "55GkHamhTU1ZbTbV2ab9DE",
                "data": {
                    "name": "schema_name",
                    "version": "9.1",
                    "attr_names": ["a", "b"],
                },
            }

            result = await ledger.get_schema("55GkHamhTU1ZbTbV2ab9DE:2:schema_name:9.1")
            assert result == {
                "ver": "1.0",
                "id": "55GkHamhTU1ZbTbV2ab9DE:2:schema_name:9.1",
                "name": "schema_name",
                "version": "9.1",
                "attrNames": ["a", "b"],
                "seqNo": 99,
            }

    @pytest.mark.asyncio
    async def test_get_schema_not_found(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {}
            result = await ledger.get_schema("55GkHamhTU1ZbTbV2ab9DE:2:schema_name:9.1")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_credential_definition(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        schema_id = "55GkHamhTU1ZbTbV2ab9DE:2:schema_name:9.1"
        cred_def_id = "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag"
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": schema_id,
            "type": "CL",
            "tag": "tag",
            "value": {
                "primary": {
                    "n": "...",
                    "s": "...",
                    "r": "...",
                    "revocation": None,
                }
            },
        }
        issuer = mock.MagicMock(IndyIssuer)
        issuer.make_credential_definition_id.return_value = cred_def_id
        issuer.credential_definition_in_wallet.return_value = False
        issuer.create_and_store_credential_definition.return_value = (
            cred_def_id,
            json.dumps(cred_def),
        )

        async with ledger:
            ledger.pool_handle.submit_request.side_effect = (
                {
                    "seqNo": 99,
                    "dest": "55GkHamhTU1ZbTbV2ab9DE",
                    "data": {
                        "name": "schema_name",
                        "version": "9.1",
                        "attr_names": ["a", "b"],
                    },
                },
                {"data": None},  # cred def lookup result
                {},  # submission result
            )

            result = await ledger.create_and_send_credential_definition(
                issuer=issuer,
                schema_id=schema_id,
                signature_type="CL",
                tag="tag",
                support_revocation=False,
            )
            assert result == (cred_def_id, cred_def, True)

    @pytest.mark.asyncio
    async def test_send_credential_definition_no_public_did(
        self,
        ledger: IndyVdrLedger,
    ):
        issuer = mock.MagicMock(IndyIssuer)
        async with ledger:
            with pytest.raises(BadLedgerRequestError):
                await ledger.create_and_send_credential_definition(
                    issuer, "schema_id", None, "tag"
                )

    @pytest.mark.asyncio
    async def test_send_credential_definition_no_such_schema(self, ledger: IndyVdrLedger):
        issuer = mock.MagicMock(IndyIssuer)
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {}
            with pytest.raises(BadLedgerRequestError):
                await ledger.create_and_send_credential_definition(
                    issuer, "schema_id", None, "tag"
                )

    @pytest.mark.asyncio
    async def test_send_credential_definition_read_only(self, ledger: IndyVdrLedger):
        issuer = mock.MagicMock(IndyIssuer)
        async with ledger:
            ledger.pool.read_only = True
            with pytest.raises(LedgerError):
                await ledger.create_and_send_credential_definition(
                    issuer, "schema_id", None, "tag"
                )

    @pytest.mark.asyncio
    async def test_get_credential_definition(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "seqNo": 99,
                "ref": "schema-id",
                "signature_type": "CL",
                "tag": "tag",
                "origin": "origin-did",
                "data": {"cred": "def"},
            }

            result = await ledger.get_credential_definition(
                "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag"
            )
            assert result == {
                "ver": "1.0",
                "id": "origin-did:3:CL:schema-id:tag",
                "schemaId": "schema-id",
                "type": "CL",
                "tag": "tag",
                "value": {"cred": "def"},
            }

    @pytest.mark.asyncio
    async def test_get_credential_definition_not_found(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "seqNo": 99,
                "ref": "schema-id",
                "signature_type": "CL",
                "tag": "tag",
                "origin": "origin-did",
                "data": None,
            }

            result = await ledger.get_credential_definition(
                "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_key_for_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"verkey": "VK"}',
            }
            result = await ledger.get_key_for_did("55GkHamhTU1ZbTbV2ab9DE")
            assert result == "VK"

    @pytest.mark.asyncio
    async def test_get_key_for_did_non_sov_public_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            async with ledger.profile.session() as session:
                wallet = session.inject(BaseWallet)
                wallet.get_public_did = mock.CoroutineMock(
                    return_value=DIDInfo(
                        "did:web:doma.in",
                        "verkey",
                        DIDPosture.PUBLIC.metadata,
                        WEB,
                        ED25519,
                    )
                )
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"verkey": "VK"}',
            }
            result = await ledger.get_key_for_did("55GkHamhTU1ZbTbV2ab9DE")
            assert result == "VK"

    @pytest.mark.asyncio
    async def test_get_all_endpoints_for_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"endpoint": {"default": "endp"}}',
            }
            result = await ledger.get_all_endpoints_for_did("55GkHamhTU1ZbTbV2ab9DE")
            assert result == {"default": "endp"}

    @pytest.mark.asyncio
    async def test_get_all_endpoints_for_did_none(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": None,
            }
            result = await ledger.get_all_endpoints_for_did("55GkHamhTU1ZbTbV2ab9DE")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_endpoint_for_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"endpoint": {"endpoint": "endp"}}',
            }
            result = await ledger.get_endpoint_for_did(
                "55GkHamhTU1ZbTbV2ab9DE", EndpointType.ENDPOINT
            )
            assert result == "endp"

    @pytest.mark.asyncio
    async def test_get_endpoint_for_did_address_none(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"endpoint": null}',
            }
            result = await ledger.get_endpoint_for_did(
                "55GkHamhTU1ZbTbV2ab9DE", EndpointType.ENDPOINT
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_endpoint_for_did_empty(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": None,
            }
            result = await ledger.get_endpoint_for_did(
                "55GkHamhTU1ZbTbV2ab9DE", EndpointType.ENDPOINT
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_update_endpoint_for_did(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            ledger.pool_handle.submit_request.side_effect = (
                {"data": None},
                {"data": None},
            )
            await ledger.update_endpoint_for_did(
                "55GkHamhTU1ZbTbV2ab9DE", "https://url", EndpointType.ENDPOINT
            )

    @pytest.mark.parametrize(
        "all_exist_endpoints, routing_keys, result",
        [
            (
                {"profile": "https://endpoint/profile"},
                ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                {
                    "endpoint": {
                        "profile": "https://endpoint/profile",
                        "endpoint": "https://url",
                        "routingKeys": ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                    }
                },
            ),
            (
                {"profile": "https://endpoint/profile"},
                None,
                {
                    "endpoint": {
                        "profile": "https://endpoint/profile",
                        "endpoint": "https://url",
                        "routingKeys": [],
                    }
                },
            ),
            (
                None,
                ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                {
                    "endpoint": {
                        "endpoint": "https://url",
                        "routingKeys": ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                    }
                },
            ),
            (None, None, {"endpoint": {"endpoint": "https://url", "routingKeys": []}}),
            (
                {
                    "profile": "https://endpoint/profile",
                    "spec_divergent_endpoint": "https://endpoint",
                },
                ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                {
                    "endpoint": {
                        "profile": "https://endpoint/profile",
                        "spec_divergent_endpoint": "https://endpoint",
                        "endpoint": "https://url",
                        "routingKeys": ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
                    }
                },
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_construct_attr_json(
        self, ledger: IndyVdrLedger, all_exist_endpoints, routing_keys, result
    ):
        async with ledger:
            attr_json = await ledger._construct_attr_json(
                "https://url", EndpointType.ENDPOINT, all_exist_endpoints, routing_keys
            )
        assert attr_json == json.dumps(result)

    @pytest.mark.asyncio
    async def test_update_endpoint_for_did_calls_attr_json(self, ledger: IndyVdrLedger):
        routing_keys = ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"]
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)

        async with ledger:
            with (
                mock.patch.object(
                    ledger,
                    "_construct_attr_json",
                    mock.CoroutineMock(
                        return_value=json.dumps(
                            {
                                "endpoint": {
                                    "endpoint": {
                                        "endpoint": "https://url",
                                        "routingKeys": [],
                                    }
                                }
                            }
                        )
                    ),
                ) as mock_construct_attr_json,
                mock.patch.object(
                    ledger,
                    "get_all_endpoints_for_did",
                    mock.CoroutineMock(return_value={}),
                ),
            ):
                await ledger.update_endpoint_for_did(
                    test_did.did,
                    "https://url",
                    EndpointType.ENDPOINT,
                    routing_keys=routing_keys,
                )
                mock_construct_attr_json.assert_called_once_with(
                    "https://url",
                    EndpointType.ENDPOINT,
                    {},
                    routing_keys,
                )

    @pytest.mark.asyncio
    async def test_update_endpoint_for_did_no_public(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {"data": None}
            with pytest.raises(BadLedgerRequestError):
                await ledger.update_endpoint_for_did(
                    "55GkHamhTU1ZbTbV2ab9DE", "https://url", EndpointType.ENDPOINT
                )

    @pytest.mark.asyncio
    async def test_update_endpoint_for_did_read_only(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool.read_only = True
            ledger.pool_handle.submit_request.return_value = {"data": None}
            with pytest.raises(LedgerError):
                await ledger.update_endpoint_for_did(
                    "55GkHamhTU1ZbTbV2ab9DE", "https://url", EndpointType.ENDPOINT
                )

    @pytest.mark.asyncio
    async def test_register_nym_local(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
            post_did = await wallet.create_local_did(SOV, ED25519)
            async with ledger:
                await ledger.register_nym(post_did.did, post_did.verkey)
            did = await wallet.get_local_did(post_did.did)
            assert did.metadata["posted"] is True

    @pytest.mark.asyncio
    async def test_register_nym_non_local(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            await ledger.register_nym("55GkHamhTU1ZbTbV2ab9DE", "verkey")

    @pytest.mark.asyncio
    async def test_register_nym_no_public(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            with pytest.raises(BadLedgerRequestError):
                await ledger.register_nym("55GkHamhTU1ZbTbV2ab9DE", "verkey")

    @pytest.mark.asyncio
    async def test_register_nym_read_only(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool.read_only = True
            with pytest.raises(LedgerError):
                await ledger.register_nym(
                    "55GkHamhTU1ZbTbV2ab9DE",
                    "verkey",
                    "",
                )

    @pytest.mark.asyncio
    async def test_get_nym_role(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"role":"TRUSTEE"}'
            }
            result = await ledger.get_nym_role(
                "55GkHamhTU1ZbTbV2ab9DE",
            )
            assert result == Role.TRUSTEE

    @pytest.mark.asyncio
    async def test_get_nym_role_unknown(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {"data": r"{}"}
            with pytest.raises(BadLedgerRequestError):
                await ledger.get_nym_role(
                    "55GkHamhTU1ZbTbV2ab9DE",
                )

    @pytest.mark.asyncio
    async def test_get_nym_role_invalid(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            ledger.pool_handle.submit_request.return_value = {
                "data": r'{"role":"INVALID"}'
            }
            result = await ledger.get_nym_role(
                "55GkHamhTU1ZbTbV2ab9DE",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_revoc_reg_def(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            ledger.pool_handle.submit_request.return_value = {
                "data": {"id": reg_id},
                "txnTime": 1234567890,
            }
            result = await ledger.get_revoc_reg_def(
                reg_id,
            )
            assert result["id"] == reg_id
            assert result["txnTime"] == 1234567890

    @pytest.mark.asyncio
    async def test_get_revoc_reg_entry(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            ledger.pool_handle.submit_request.return_value = {
                "data": {
                    "id": reg_id,
                    "txnTime": 1234567890,
                    "value": "...",
                    "revocRegDefId": reg_id,
                },
            }
            result = await ledger.get_revoc_reg_entry(reg_id, 1234567890)
            assert result == ({"ver": "1.0", "value": "..."}, 1234567890)

    @pytest.mark.asyncio
    async def test_get_revoc_reg_delta(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            ledger.pool_handle.submit_request.return_value = {
                "data": {
                    "value": {
                        "accum_to": {
                            "value": {"accum": "ACCUM"},
                            "txnTime": 1234567890,
                        },
                        "issued": [1, 2],
                        "revoked": [3, 4],
                    },
                    "revocRegDefId": reg_id,
                },
            }
            result = await ledger.get_revoc_reg_delta(reg_id)
            assert result == (
                {
                    "ver": "1.0",
                    "value": {"accum": "ACCUM", "issued": [1, 2], "revoked": [3, 4]},
                },
                1234567890,
            )

    @pytest.mark.asyncio
    async def test_get_revoc_reg_delta_without_accum_to(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            ledger.pool_handle.submit_request.side_effect = [
                # First call to get_revoc_reg_delta
                {
                    "data": {
                        "value": {},
                        "revocRegDefId": reg_id,
                    },
                },
                # Get registry with test_get_revoc_reg_entry
                {
                    "data": {
                        "id": reg_id,
                        "txnTime": 1234567890,
                        "value": "...",
                        "revocRegDefId": reg_id,
                    },
                },
                # Second call to get_revoc_reg_delta
                {
                    "data": {
                        "value": {
                            "accum_to": {
                                "value": {"accum": "ACCUM"},
                                "txnTime": 1234567890,
                            },
                            "issued": [1, 2],
                            "revoked": [3, 4],
                        },
                        "revocRegDefId": reg_id,
                    },
                },
            ]
            result = await ledger.get_revoc_reg_delta(reg_id)
            assert result == (
                {
                    "ver": "1.0",
                    "value": {"accum": "ACCUM", "issued": [1, 2], "revoked": [3, 4]},
                },
                1234567890,
            )

    @pytest.mark.asyncio
    async def test_send_revoc_reg_def(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_def = {
                "ver": "1.0",
                "id": reg_id,
                "revocDefType": "CL_ACCUM",
                "tag": "tag1",
                "credDefId": "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag",
                "value": {
                    "issuanceType": "ISSUANCE_ON_DEMAND",
                    "maxCredNum": 5,
                    "publicKeys": {"accumKey": {"z": "1 ..."}},
                    "tailsHash": "",
                    "tailsLocation": "",
                },
            }
            ledger.pool_handle.submit_request.return_value = {"status": "ok"}
            result = await ledger.send_revoc_reg_def(reg_def, issuer_did=None)
            assert result == {"result": {"status": "ok"}}

    @pytest.mark.asyncio
    async def test_send_revoc_reg_def_anoncreds_write_to_ledger(
        self,
        ledger: IndyVdrLedger,
    ):
        ledger.profile.settings.set_value("wallet.type", "askar-anoncreds")
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_def = {
                "ver": "1.0",
                "id": reg_id,
                "revocDefType": "CL_ACCUM",
                "tag": "tag1",
                "credDefId": "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag",
                "value": {
                    "issuanceType": "ISSUANCE_ON_DEMAND",
                    "maxCredNum": 5,
                    "publicKeys": {"accumKey": {"z": "1 ..."}},
                    "tailsHash": "",
                    "tailsLocation": "",
                },
            }

            with mock.patch.object(
                LegacyIndyRegistry,
                "txn_submit",
                return_value=json.dumps({"result": {"txnMetadata": {"seqNo": 1234}}}),
            ):
                ledger.pool_handle.submit_request.return_value = {"status": "ok"}
                result = await ledger.send_revoc_reg_def(reg_def, issuer_did=None)
                assert result == 1234

    @pytest.mark.asyncio
    async def test_send_revoc_reg_def_anoncreds_do_not_write_to_ledger(
        self,
        ledger: IndyVdrLedger,
    ):
        ledger.profile.settings.set_value("wallet.type", "askar-anoncreds")
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_def = {
                "ver": "1.0",
                "id": reg_id,
                "revocDefType": "CL_ACCUM",
                "tag": "tag1",
                "credDefId": "55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag",
                "value": {
                    "issuanceType": "ISSUANCE_ON_DEMAND",
                    "maxCredNum": 5,
                    "publicKeys": {"accumKey": {"z": "1 ..."}},
                    "tailsHash": "",
                    "tailsLocation": "",
                },
            }

            with mock.patch.object(
                LegacyIndyRegistry,
                "txn_submit",
                return_value=json.dumps({"result": {"txnMetadata": {"seqNo": 1234}}}),
            ):
                ledger.pool_handle.submit_request.return_value = {"status": "ok"}
                result = await ledger.send_revoc_reg_def(
                    reg_def, issuer_did=None, write_ledger=False
                )
                assert isinstance(result, tuple)

    @pytest.mark.asyncio
    async def test_send_revoc_reg_entry(
        self,
        ledger: IndyVdrLedger,
    ):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_entry = {
                "ver": "1.0",
                "value": {},
            }
            ledger.pool_handle.submit_request.return_value = {"status": "ok"}
            result = await ledger.send_revoc_reg_entry(reg_id, "CL_ACCUM", reg_entry)
            assert result == {"result": {"status": "ok"}}

    @pytest.mark.asyncio
    async def test_send_revoc_reg_entry_anoncreds_write_to_ledger(
        self,
        ledger: IndyVdrLedger,
    ):
        ledger.profile.settings.set_value("wallet.type", "askar-anoncreds")
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_entry = {
                "ver": "1.0",
                "value": {},
            }
            with mock.patch.object(
                LegacyIndyRegistry,
                "txn_submit",
                return_value=json.dumps({"result": {"txnMetadata": {"seqNo": 1234}}}),
            ):
                ledger.pool_handle.submit_request.return_value = {"status": "ok"}
                result = await ledger.send_revoc_reg_entry(
                    reg_id, "CL_ACCUM", reg_entry, write_ledger=False
                )
                assert isinstance(result, tuple)

    @pytest.mark.asyncio
    async def test_send_revoc_reg_entry_anoncreds_do_not_write_to_ledger(
        self,
        ledger: IndyVdrLedger,
    ):
        ledger.profile.settings.set_value("wallet.type", "askar-anoncreds")
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            reg_id = (
                "55GkHamhTU1ZbTbV2ab9DE:4:55GkHamhTU1ZbTbV2ab9DE:3:CL:99:tag:CL_ACCUM:0"
            )
            reg_entry = {
                "ver": "1.0",
                "value": {},
            }
            with mock.patch.object(
                LegacyIndyRegistry,
                "txn_submit",
                return_value=json.dumps({"result": {"txnMetadata": {"seqNo": 1234}}}),
            ):
                ledger.pool_handle.submit_request.return_value = {"status": "ok"}
                result = await ledger.send_revoc_reg_entry(reg_id, "CL_ACCUM", reg_entry)
                assert result == 1234

    @pytest.mark.asyncio
    async def test_credential_definition_id2schema_id(self, ledger: IndyVdrLedger):
        S_ID = "55GkHamhTU1ZbTbV2ab9DE:2:favourite_drink:1.0"
        SEQ_NO = "9999"

        async with ledger:
            with mock.patch.object(
                ledger,
                "get_schema",
                mock.CoroutineMock(return_value={"id": S_ID}),
            ) as mock_get_schema:
                s_id_short = await ledger.credential_definition_id2schema_id(
                    f"55GkHamhTU1ZbTbV2ab9DE:3:CL:{SEQ_NO}:tag"
                )

                mock_get_schema.assert_called_once_with(SEQ_NO)

                assert s_id_short == S_ID
                s_id_long = await ledger.credential_definition_id2schema_id(
                    f"55GkHamhTU1ZbTbV2ab9DE:3:CL:{s_id_short}:tag"
                )
                assert s_id_long == s_id_short

    @pytest.mark.asyncio
    async def test_rotate_did_keypair(self, ledger: IndyVdrLedger):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(SOV, ED25519)

        async with ledger:
            with mock.patch.object(
                ledger.pool_handle,
                "submit_request",
                mock.CoroutineMock(
                    side_effect=[
                        {"data": json.dumps({"seqNo": 1234})},
                        {"data": {"txn": {"data": {"role": "101", "alias": "Billy"}}}},
                        {"data": "ok"},
                    ]
                ),
            ):
                ledger.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
                await ledger.rotate_public_did_keypair()

    async def _create_tenant_profile(
        self, main_profile: Profile, name: str = "tenant"
    ) -> Profile:
        """Helper to create a secondary profile instance for testing."""
        tenant_settings = {
            "wallet.type": main_profile.settings.get("wallet.type", "askar-anoncreds"),
            "auto_provision": True,
            "wallet.name": f"{name}_wallet",
            "wallet.key": f"test_tenant_key_for_{name}",
            "wallet.key_derivation_method": "RAW",
            "default_label": name,
        }
        tenant_profile = await create_test_profile(settings=tenant_settings)
        tenant_profile.context.injector.bind_instance(
            DIDMethods, main_profile.context.injector.inject(DIDMethods)
        )
        tenant_profile.context.injector.bind_instance(BaseCache, InMemoryCache())
        tenant_profile.context.injector.bind_instance(
            KeyTypes, main_profile.context.injector.inject(KeyTypes)
        )
        await tenant_profile.session()
        return tenant_profile

    @pytest.mark.asyncio
    async def test_submit_signing_uses_passed_profile_context(
        self, ledger: IndyVdrLedger
    ):
        """Test _submit calls sign_message using the passed profile context."""

        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "submit_tenant"
        )

        mock_signing_did = DIDInfo("tenant_signer", "tenant_signer_vk", {}, SOV, ED25519)

        mock_request_obj = mock.MagicMock(spec=indy_vdr.Request)
        mock_request_obj.signature_input = b"data_to_be_signed"
        mock_request_obj.body = json.dumps({"req": "data"})
        mock_request_obj.set_signature = mock.Mock()
        mock_request_obj.set_txn_author_agreement_acceptance = mock.Mock()

        with mock.patch(
            "acapy_agent.wallet.askar.AskarWallet.sign_message",
            new_callable=mock.CoroutineMock,
            return_value=b"mock_signature_from_patch",
        ) as mock_sign_message_patch:
            ledger.get_wallet_public_did = mock.CoroutineMock(
                return_value=mock_signing_did
            )
            ledger.get_latest_txn_author_acceptance = mock.CoroutineMock(return_value={})

            async with ledger:
                await ledger._submit(
                    mock_request_obj,
                    sign=True,
                    sign_did=mock_signing_did,
                    taa_accept=False,
                    write_ledger=False,
                    profile=tenant_profile,
                )

        mock_sign_message_patch.assert_awaited_once_with(
            message=b"data_to_be_signed", from_verkey=mock_signing_did.verkey
        )
        mock_request_obj.set_signature.assert_called_once_with(
            b"mock_signature_from_patch"
        )

    @pytest.mark.asyncio
    async def test_get_wallet_public_did_uses_passed_profile(self, ledger: IndyVdrLedger):
        """Test get_wallet_public_did uses the explicitly passed profile."""
        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "get_did_tenant"
        )
        mock_tenant_did = DIDInfo("did:sov:tenant_pub", "vk_pub", {}, SOV, ED25519)

        with mock.patch(
            "acapy_agent.wallet.askar.AskarWallet.get_public_did",
            new_callable=mock.CoroutineMock,
            return_value=mock_tenant_did,
        ) as mock_get_public_patch:
            result_did = await ledger.get_wallet_public_did(profile=tenant_profile)

        assert result_did is mock_tenant_did
        mock_get_public_patch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_latest_taa_uses_passed_profile(self, ledger: IndyVdrLedger):
        """Test get_latest_txn_author_acceptance uses the explicitly passed profile."""
        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "get_taa_tenant"
        )
        tenant_profile.context.injector.bind_instance(BaseCache, InMemoryCache())

        with mock.patch.object(
            AskarStorage, "find_all_records", return_value=[]
        ) as mock_find_records_patch:
            result_taa = await ledger.get_latest_txn_author_acceptance(
                profile=tenant_profile
            )

        mock_find_records_patch.assert_awaited_once()
        call_args, _call_kwargs = mock_find_records_patch.call_args
        assert call_args[0] == TAA_ACCEPTED_RECORD_TYPE
        assert call_args[1] == {"pool_name": ledger.pool_name}

        assert result_taa == {}

    @pytest.mark.asyncio
    async def test_send_revoc_reg_entry_uses_passed_profile(self, ledger: IndyVdrLedger):
        """Test send_revoc_reg_entry passes the correct profile to _submit."""
        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "rev_entry_tenant"
        )

        async with tenant_profile.session() as session:
            wallet = session.inject(BaseWallet)
            tenant_did = await wallet.create_public_did(SOV, ED25519)

        test_rev_reg_id = f"{tenant_did.did}:4:{TEST_CRED_DEF_ID}:CL_ACCUM:0"
        test_reg_entry = {"ver": "1.0", "value": {"accum": "test_accum"}}

        with (
            mock.patch.object(
                IndyVdrLedger,
                "get_revoc_reg_def",
                new=mock.CoroutineMock(
                    return_value={"txn": {"data": {"revocDefType": "CL_ACCUM"}}}
                ),
            ),
            mock.patch.object(
                IndyVdrLedger,
                "_create_revoc_reg_entry_request",
                new=mock.CoroutineMock(
                    return_value=mock.MagicMock(spec=indy_vdr.Request)
                ),
            ),
            mock.patch.object(
                IndyVdrLedger,
                "_submit",
                new=mock.CoroutineMock(return_value={"result": "mock_ok"}),
            ) as mock_submit,
        ):
            async with ledger:
                await ledger.send_revoc_reg_entry(
                    revoc_reg_id=test_rev_reg_id,
                    revoc_def_type="CL_ACCUM",
                    revoc_reg_entry=test_reg_entry,
                    write_ledger=True,
                    profile=tenant_profile,
                )

        mock_submit.assert_awaited_once()
        _, submit_kwargs = mock_submit.call_args
        assert submit_kwargs.get("profile") is tenant_profile
        assert submit_kwargs.get("sign_did").did == tenant_did.did

    @pytest.mark.asyncio
    async def test_ledger_txn_submit_uses_passed_profile(self, ledger: IndyVdrLedger):
        """Test ledger txn_submit passes profile kwarg to _submit."""
        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "txn_submit_tenant"
        )

        ledger._submit = mock.CoroutineMock(
            return_value={"op": "REPLY", "result": {"status": "ok"}}
        )

        test_txn_data = '{"req": "data"}'
        test_sign_did = mock.MagicMock(spec=DIDInfo)

        await ledger.txn_submit(
            test_txn_data,
            sign=True,
            sign_did=test_sign_did,
            write_ledger=True,
            profile=tenant_profile,
        )

        ledger._submit.assert_awaited_once()
        _submit_args, submit_kwargs = ledger._submit.call_args
        assert "profile" in submit_kwargs
        assert submit_kwargs["profile"] is tenant_profile
        assert _submit_args[0] == test_txn_data
        assert submit_kwargs["sign"] is True
        assert submit_kwargs["sign_did"] is test_sign_did
        assert submit_kwargs["write_ledger"] is True

    @pytest.mark.asyncio
    async def test_submit_wallet_not_found_error(self, ledger: IndyVdrLedger):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)
            # Create a DID not present in the wallet
            invalid_did = DIDInfo(
                did="did:sov:invalid",
                verkey="invalid_verkey",
                metadata={},
                method=SOV,
                key_type=ED25519,
            )
        async with ledger:
            test_msg = indy_vdr.ledger.build_get_txn_request(test_did.did, 1, 1)
            with pytest.raises(WalletNotFoundError):
                await ledger._submit(
                    test_msg, sign=True, sign_did=invalid_did, write_ledger=False
                )

    @pytest.mark.asyncio
    async def test_submit_unexpected_error(self, ledger: IndyVdrLedger):
        async with ledger.profile.session() as session:
            wallet = session.inject(BaseWallet)
            test_did = await wallet.create_public_did(SOV, ED25519)
        async with ledger:
            test_msg = indy_vdr.ledger.build_get_txn_request(test_did.did, 1, 1)
            ledger.pool_handle.submit_request.side_effect = ValueError("Unexpected error")
            with pytest.raises(LedgerTransactionError) as exc_info:
                await ledger._submit(test_msg)
            assert "Unexpected error during ledger submission" in str(exc_info.value)
            assert isinstance(exc_info.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_txn_submit_passes_profile(self, ledger: IndyVdrLedger):
        tenant_profile = await self._create_tenant_profile(
            ledger.profile, "submit_tenant"
        )
        test_txn_data = '{"req": "data"}'
        mock_sign_did = mock.MagicMock(spec=DIDInfo)
        ledger._submit = mock.CoroutineMock(return_value={"result": "ok"})

        await ledger.txn_submit(
            test_txn_data,
            sign=True,
            sign_did=mock_sign_did,
            write_ledger=True,
            profile=tenant_profile,
        )

        ledger._submit.assert_awaited_once()
        _, kwargs = ledger._submit.call_args
        assert kwargs.get("profile") == tenant_profile
