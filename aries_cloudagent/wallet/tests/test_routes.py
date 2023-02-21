import mock as async_mock
import pytest
from aiohttp.web import HTTPForbidden
from async_case import IsolatedAsyncioTestCase

from ...admin.request_context import AdminRequestContext
from ...core.in_memory import InMemoryProfile
from ...ledger.base import BaseLedger
from ...protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ...wallet.did_method import SOV, DIDMethods, DIDMethod, HolderDefinedDid
from ...wallet.key_type import ED25519, KeyTypes
from .. import routes as test_module
from ..base import BaseWallet
from ..did_info import DIDInfo
from ..did_posture import DIDPosture


class TestWalletRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.wallet = async_mock.create_autospec(BaseWallet)
        self.session_inject = {BaseWallet: self.wallet}
        self.profile = InMemoryProfile.test_profile()
        self.context = AdminRequestContext.test_context(
            self.session_inject, self.profile
        )
        self.context.injector.bind_instance(KeyTypes, KeyTypes())
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.AsyncMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_posted_did = "posted-did"
        self.test_posted_verkey = "posted-verkey"
        self.did_methods = DIDMethods()
        self.context.injector.bind_instance(DIDMethods, self.did_methods)

    async def test_missing_wallet(self):
        self.session_inject[BaseWallet] = None

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_create_did(self.request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_did_list(self.request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_get_public_did(self.request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_set_public_did(self.request)

        with self.assertRaises(HTTPForbidden):
            self.request.json = async_mock.AsyncMock(
                return_value={
                    "did": self.test_did,
                    "endpoint": "https://my-endpoint.ca:8020",
                }
            )
            await test_module.wallet_set_did_endpoint(self.request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_get_did_endpoint(self.request)

    def test_format_did_info(self):
        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            DIDPosture.WALLET_ONLY.metadata,
            SOV,
            ED25519,
        )
        result = test_module.format_did_info(did_info)
        assert (
            result["did"] == self.test_did
            and result["verkey"] == self.test_verkey
            and result["posture"] == DIDPosture.WALLET_ONLY.moniker
        )

        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"posted": True, "public": True},
            SOV,
            ED25519,
        )
        result = test_module.format_did_info(did_info)
        assert result["posture"] == DIDPosture.PUBLIC.moniker

        did_info = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"posted": True, "public": False},
            SOV,
            ED25519,
        )
        result = test_module.format_did_info(did_info)
        assert result["posture"] == DIDPosture.POSTED.moniker

    async def test_create_did(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.create_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.WALLET_ONLY.metadata,
                SOV,
                ED25519,
            )
            result = await test_module.wallet_create_did(self.request)
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.WALLET_ONLY.moniker,
                        "key_type": ED25519.key_type,
                        "method": SOV.method_name,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_create_did_unsupported_key_type(self):
        self.request.json = async_mock.AsyncMock(
            return_value={"method": "sov", "options": {"key_type": "bls12381g2"}}
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_create_did(self.request)

    async def test_create_did_method_requires_user_defined_did(self):
        # given
        did_custom = DIDMethod(
            name="custom",
            key_types=[ED25519],
            rotation=True,
            holder_defined_did=HolderDefinedDid.REQUIRED,
        )
        self.did_methods.register(did_custom)

        self.request.json = async_mock.AsyncMock(
            return_value={"method": "custom", "options": {"key_type": "ed25519"}}
        )

        # when - then
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_create_did(self.request)

    async def test_create_did_method_doesnt_support_user_defined_did(self):
        did_custom = DIDMethod(
            name="custom",
            key_types=[ED25519],
            rotation=True,
            holder_defined_did=HolderDefinedDid.NO,
        )
        self.did_methods.register(did_custom)

        # when
        self.request.json = async_mock.AsyncMock(
            return_value={
                "method": "custom",
                "options": {
                    "key_type": ED25519.key_type,
                    "did": "did:custom:aCustomUserDefinedDID",
                },
            }
        )

        # then
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_create_did(self.request)

    async def test_create_did_x(self):
        self.wallet.create_local_did.side_effect = test_module.WalletError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_create_did(self.request)

    async def test_did_list(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:  # , async_mock.patch.object(
            self.wallet.get_local_dids.return_value = [
                DIDInfo(
                    self.test_did,
                    self.test_verkey,
                    DIDPosture.WALLET_ONLY.metadata,
                    SOV,
                    ED25519,
                ),
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    DIDPosture.POSTED.metadata,
                    SOV,
                    ED25519,
                ),
            ]
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_posted_did,
                            "verkey": self.test_posted_verkey,
                            "posture": DIDPosture.POSTED.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        },
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        },
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_public(self):
        self.request.query = {"posture": DIDPosture.PUBLIC.moniker}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            self.wallet.get_posted_dids.return_value = [
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    DIDPosture.POSTED.metadata,
                    SOV,
                    ED25519,
                )
            ]
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.PUBLIC.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_posted(self):
        self.request.query = {"posture": DIDPosture.POSTED.moniker}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            self.wallet.get_posted_dids.return_value = [
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    {
                        "posted": True,
                        "public": False,
                    },
                    SOV,
                    ED25519,
                )
            ]
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_posted_did,
                            "verkey": self.test_posted_verkey,
                            "posture": DIDPosture.POSTED.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_did(self):
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.WALLET_ONLY.metadata,
                SOV,
                ED25519,
            )
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_did_x(self):
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did.side_effect = test_module.WalletError()
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with({"results": []})
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_verkey(self):
        self.request.query = {"verkey": self.test_verkey}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did_for_verkey.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.WALLET_ONLY.metadata,
                SOV,
                ED25519,
            )
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                            "key_type": ED25519.key_type,
                            "method": SOV.method_name,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_verkey_x(self):
        self.request.query = {"verkey": self.test_verkey}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did_for_verkey.side_effect = test_module.WalletError()
            result = await test_module.wallet_did_list(self.request)
            json_response.assert_called_once_with({"results": []})
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_get_public_did(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            result = await test_module.wallet_get_public_did(self.request)
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                        "key_type": ED25519.key_type,
                        "method": SOV.method_name,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_get_public_did_x(self):
        self.wallet.get_public_did.side_effect = test_module.WalletError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_public_did(self.request)

    async def test_set_public_did(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.get_key_for_did = async_mock.AsyncMock()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.route_public_did = async_mock.AsyncMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.set_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            result = await test_module.wallet_set_public_did(self.request)
            self.wallet.set_public_did.assert_awaited_once()
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                        "key_type": ED25519.key_type,
                        "method": SOV.method_name,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_set_public_did_no_query_did(self):
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_no_ledger(self):
        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)
        self.request.query = {"did": self.test_did}

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_not_public(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.get_key_for_did = async_mock.AsyncMock(return_value=None)
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_not_found(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.get_key_for_did = async_mock.AsyncMock(return_value=None)
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        self.wallet.get_local_did.side_effect = test_module.WalletNotFoundError()
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_x(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.get_key_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            self.wallet.set_public_did.side_effect = test_module.WalletError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_no_wallet_did(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.get_key_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            self.wallet.set_public_did.side_effect = test_module.WalletNotFoundError()
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.wallet_set_public_did(self.request)

    async def test_set_public_did_update_endpoint(self):
        self.request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.get_key_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.route_public_did = async_mock.AsyncMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock()
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.set_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                {**DIDPosture.PUBLIC.metadata, "endpoint": "https://endpoint.com"},
                SOV,
                ED25519,
            )
            result = await test_module.wallet_set_public_did(self.request)
            self.wallet.set_public_did.assert_awaited_once()
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                        "key_type": ED25519.key_type,
                        "method": SOV.method_name,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_set_public_did_update_endpoint_use_default_update_in_wallet(self):
        self.request.query = {"did": self.test_did}
        self.context.update_settings(
            {"default_endpoint": "https://default_endpoint.com"}
        )

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.get_key_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        mock_route_manager = async_mock.MagicMock()
        mock_route_manager.route_public_did = async_mock.AsyncMock()
        mock_route_manager.mediation_record_if_id = async_mock.AsyncMock(
            return_value=None
        )
        mock_route_manager.__aenter__ = async_mock.AsyncMock(
            return_value=mock_route_manager
        )
        self.profile.context.injector.bind_instance(RouteManager, mock_route_manager)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            did_info = DIDInfo(
                self.test_did,
                self.test_verkey,
                DIDPosture.PUBLIC.metadata,
                SOV,
                ED25519,
            )
            self.wallet.get_local_did.return_value = did_info
            self.wallet.set_public_did.return_value = did_info
            result = await test_module.wallet_set_public_did(self.request)
            self.wallet.set_public_did.assert_awaited_once()
            self.wallet.set_did_endpoint.assert_awaited_once_with(
                did_info.did,
                "https://default_endpoint.com",
                ledger,
                write_ledger=True,
                endorser_did=None,
                routing_keys=None,
            )
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                        "key_type": ED25519.key_type,
                        "method": SOV.method_name,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_set_did_endpoint(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
            SOV,
            ED25519,
        )
        self.wallet.get_public_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            DIDPosture.PUBLIC.metadata,
            SOV,
            ED25519,
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            await test_module.wallet_set_did_endpoint(self.request)
            json_response.assert_called_once_with({})

    async def test_set_did_endpoint_public_did_no_ledger(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
            SOV,
            ED25519,
        )
        self.wallet.get_public_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            DIDPosture.PUBLIC.metadata,
            SOV,
            ED25519,
        )
        self.wallet.set_did_endpoint.side_effect = test_module.LedgerConfigError()

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_set_did_endpoint(self.request)

    async def test_set_did_endpoint_x(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        self.wallet.set_did_endpoint.side_effect = test_module.WalletError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_set_did_endpoint(self.request)

    async def test_set_did_endpoint_no_wallet_did(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        ledger = Ledger()
        ledger.update_endpoint_for_did = async_mock.AsyncMock()
        ledger.__aenter__ = async_mock.AsyncMock(return_value=ledger)
        self.profile.context.injector.bind_instance(BaseLedger, ledger)

        self.wallet.set_did_endpoint.side_effect = test_module.WalletNotFoundError()

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_did_endpoint(self.request)

    async def test_get_did_endpoint(self):
        self.request.query = {"did": self.test_did}

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
            SOV,
            ED25519,
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            await test_module.wallet_get_did_endpoint(self.request)
            json_response.assert_called_once_with(
                {
                    "did": self.test_did,
                    "endpoint": self.wallet.get_local_did.return_value.metadata[
                        "endpoint"
                    ],
                }
            )

    async def test_get_did_endpoint_no_did(self):
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_did_endpoint(self.request)

    async def test_get_did_endpoint_no_wallet_did(self):
        self.request.query = {"did": self.test_did}

        self.wallet.get_local_did.side_effect = test_module.WalletNotFoundError()

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_get_did_endpoint(self.request)

    async def test_get_did_endpoint_wallet_x(self):
        self.request.query = {"did": self.test_did}

        self.wallet.get_local_did.side_effect = test_module.WalletError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_did_endpoint(self.request)

    async def test_rotate_did_keypair(self):
        self.request.query = {"did": "did"}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did = async_mock.AsyncMock(
                return_value=DIDInfo(
                    "did",
                    "verkey",
                    {"public": False},
                    SOV,
                    ED25519,
                )
            )
            self.wallet.rotate_did_keypair_start = async_mock.AsyncMock()
            self.wallet.rotate_did_keypair_apply = async_mock.AsyncMock()

            await test_module.wallet_rotate_did_keypair(self.request)
            json_response.assert_called_once_with({})

    async def test_rotate_did_keypair_missing_wallet(self):
        self.request.query = {"did": "did"}
        self.session_inject[BaseWallet] = None

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_rotate_did_keypair(self.request)

    async def test_rotate_did_keypair_no_query_did(self):
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.request)

    async def test_rotate_did_keypair_did_not_local(self):
        self.request.query = {"did": "did"}

        self.wallet.get_local_did = async_mock.AsyncMock(
            side_effect=test_module.WalletNotFoundError("Unknown DID")
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_rotate_did_keypair(self.request)

        self.wallet.get_local_did = async_mock.AsyncMock(
            return_value=DIDInfo(
                "did",
                "verkey",
                {"posted": True, "public": True},
                SOV,
                ED25519,
            )
        )
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.request)

    async def test_rotate_did_keypair_x(self):
        self.request.query = {"did": "did"}

        self.wallet.get_local_did = async_mock.AsyncMock(
            return_value=DIDInfo(
                "did",
                "verkey",
                {"public": False},
                SOV,
                ED25519,
            )
        )
        self.wallet.rotate_did_keypair_start = async_mock.AsyncMock(
            side_effect=test_module.WalletError()
        )
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
