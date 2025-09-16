import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web
from aiohttp.web import HTTPNotFound

from ......admin.request_context import AdminRequestContext
from ......tests import mock
from ......utils.testing import create_test_profile
from .....issuer import AnonCredsIssuer
from .....models.issuer_cred_rev_record import IssuerCredRevRecord
from .....models.revocation import RevRegDef, RevRegDefState, RevRegDefValue
from .....revocation import AnonCredsRevocation
from .....tests.mock_objects import MockRevocationRegistryDefinition
from ....common.testing import BaseAnonCredsRouteTestCase
from .. import routes as test_module
from ..routes import (
    get_rev_reg_issued,
    get_rev_reg_issued_count,
    get_rev_regs,
    rev_reg_def_post,
    set_active_registry,
)


@pytest.mark.anoncreds
class TestAnonCredsRevocationRegistryRoutes(
    BaseAnonCredsRouteTestCase, IsolatedAsyncioTestCase
):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

        self.rev_reg_id = (
            f"{self.test_did}:4:{self.test_did}:3:CL:1234:default:CL_ACCUM:default"
        )

    @mock.patch.object(
        AnonCredsIssuer,
        "match_created_credential_definitions",
        side_effect=["found", None],
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=MockRevocationRegistryDefinition("revRegId"),
    )
    async def test_rev_reg_def_post(self, mock_match, mock_create):
        self.request.json = mock.CoroutineMock(
            return_value={
                "credDefId": "cred_def_id",
                "issuerId": "issuer_id",
                "maxCredNum": 100,
                "options": {
                    "tails_public_uri": "http://tails_public_uri",
                    "tails_local_uri": "http://tails_local_uri",
                },
            }
        )

        # Must be in wrapper object
        with self.assertRaises(web.HTTPBadRequest):
            await rev_reg_def_post(self.request)

        self.request.json = mock.CoroutineMock(
            return_value={
                "revocation_registry_definition": {
                    "credDefId": "cred_def_id",
                    "issuerId": "issuer_id",
                    "maxCredNum": 100,
                    "options": {
                        "tails_public_uri": "http://tails_public_uri",
                        "tails_local_uri": "http://tails_local_uri",
                    },
                }
            }
        )

        result = await rev_reg_def_post(self.request)

        assert json.loads(result.body)["revocation_registry_definition_id"] == "revRegId"

        assert mock_match.call_count == 1
        assert mock_create.call_count == 1

        with self.assertRaises(web.HTTPNotFound):
            await rev_reg_def_post(self.request)

    async def test_rev_reg_wrong_profile_403(self):
        self.profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )

        self.request.json = mock.CoroutineMock(
            return_value={
                "revocation_registry_definition": {
                    "credDefId": "cred_def_id",
                    "issuerId": "issuer_id",
                    "maxCredNum": 100,
                },
                "options": {
                    "tails_public_uri": "http://tails_public_uri",
                    "tails_local_uri": "http://tails_local_uri",
                },
            }
        )
        with self.assertRaises(web.HTTPForbidden):
            await rev_reg_def_post(self.request)

    async def test_rev_regs_created(self):
        cred_def_id = f"{self.test_did}:3:CL:1234:default"
        self.request.query = {
            "cred_def_id": cred_def_id,
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with (
            mock.patch.object(
                test_module.AnonCredsRevocation,
                "get_created_revocation_registry_definitions",
                mock.AsyncMock(),
            ) as mock_query,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_query.return_value = ["dummy"]

            result = await get_rev_regs(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    @mock.patch.object(
        AnonCredsRevocation,
        "set_active_registry",
        return_value=None,
    )
    async def test_set_active_registry(self, mock_set):
        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        await set_active_registry(self.request)
        assert mock_set.call_count == 1

        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await set_active_registry(self.request)

    async def test_active_registry_wrong_profile_403(self):
        self.profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )

        self.request.match_info = {"rev_reg_id": "rev_reg_id"}

        with self.assertRaises(web.HTTPForbidden):
            await set_active_registry(self.request)

    async def test_get_rev_regs(self):
        self.request.query = {
            "cred_def_id": "test_cred_def_id",
            "state": "active",
        }

        with (
            mock.patch.object(
                AnonCredsRevocation,
                "get_created_revocation_registry_definitions",
                mock.AsyncMock(),
            ) as mock_query,
            mock.patch.object(web, "json_response", mock.Mock()) as mock_json_response,
        ):
            mock_query.return_value = ["dummy"]

            result = await get_rev_regs(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg(self):
        record_id = "4ba81d6e-f341-4e37-83d4-6b1d3e25a7bd"
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                test_module, "AnonCredsRevocation", autospec=True
            ) as mock_anon_creds_revoc,
            mock.patch.object(test_module, "uuid4", mock.Mock()) as mock_uuid,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_uuid.return_value = record_id
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=RevRegDef(
                        issuer_id="issuer_id",
                        type="CL_ACCUM",
                        cred_def_id="cred_def_id",
                        tag="tag",
                        value=RevRegDefValue(
                            public_keys={},
                            max_cred_num=100,
                            tails_hash="tails_hash",
                            tails_location="tails_location",
                        ),
                    )
                ),
                get_created_revocation_registry_definition_state=mock.AsyncMock(
                    return_value=RevRegDefState.STATE_FINISHED
                ),
                get_pending_revocations=mock.AsyncMock(return_value=[]),
            )

            result = await test_module.get_rev_reg(self.request)
            mock_json_response.assert_called_once_with(
                {
                    "result": {
                        "tails_local_path": "tails_location",
                        "tails_hash": "tails_hash",
                        "state": RevRegDefState.STATE_FINISHED,
                        "issuer_did": "issuer_id",
                        "pending_pub": [],
                        "revoc_reg_def": {
                            "ver": "1.0",
                            "id": self.rev_reg_id,
                            "revocDefType": "CL_ACCUM",
                            "tag": "tag",
                            "credDefId": "cred_def_id",
                        },
                        "max_cred_num": 100,
                        "record_id": record_id,
                        "tag": "tag",
                        "revoc_def_type": "CL_ACCUM",
                        "revoc_reg_id": self.rev_reg_id,
                        "cred_def_id": "cred_def_id",
                    }
                }
            )
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_not_found(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                test_module, "AnonCredsRevocation", autospec=True
            ) as mock_anon_creds_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=None
                ),
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.get_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_get_rev_reg_issued(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                AnonCredsRevocation,
                "get_created_revocation_registry_definition",
                mock.AsyncMock(),
            ) as mock_get_rev_reg,
            mock.patch.object(
                IssuerCredRevRecord,
                "query_by_ids",
                mock.CoroutineMock(),
            ) as mock_query,
            mock.patch.object(web, "json_response", mock.Mock()) as mock_json_response,
        ):
            mock_get_rev_reg.return_value = mock.MagicMock()
            mock_query.return_value = [
                mock.MagicMock(serialize=mock.MagicMock(return_value="dummy"))
            ]

            result = await get_rev_reg_issued(self.request)
            mock_json_response.assert_called_once()
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_issued_x(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            autospec=True,
        ) as mock_rev_reg_def:
            mock_rev_reg_def.return_value = None

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.get_rev_reg_issued(self.request)

    async def test_get_rev_reg_issued_count(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                AnonCredsRevocation,
                "get_created_revocation_registry_definition",
                mock.AsyncMock(),
            ) as mock_get_rev_reg,
            mock.patch.object(
                IssuerCredRevRecord,
                "query_by_ids",
                mock.CoroutineMock(),
            ) as mock_query,
            mock.patch.object(web, "json_response", mock.Mock()) as mock_json_response,
        ):
            mock_get_rev_reg.return_value = mock.MagicMock()
            mock_query.return_value = [{}, {}]

            result = await get_rev_reg_issued_count(self.request)
            mock_json_response.assert_called_once_with({"result": 2})
            assert result is mock_json_response.return_value

    async def test_set_rev_reg_state(self):
        record_id = "4ba81d6e-f341-4e37-83d4-6b1d3e25a7bd"
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        self.request.query = {
            "state": RevRegDefState.STATE_FINISHED,
        }

        with (
            mock.patch.object(
                test_module, "AnonCredsRevocation", autospec=True
            ) as mock_anon_creds_revoc,
            mock.patch.object(test_module, "uuid4", mock.Mock()) as mock_uuid,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_uuid.return_value = record_id
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                set_rev_reg_state=mock.AsyncMock(return_value={}),
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=RevRegDef(
                        issuer_id="issuer_id",
                        type="CL_ACCUM",
                        cred_def_id="cred_def_id",
                        tag="tag",
                        value=RevRegDefValue(
                            public_keys={},
                            max_cred_num=100,
                            tails_hash="tails_hash",
                            tails_location="tails_location",
                        ),
                    )
                ),
                get_created_revocation_registry_definition_state=mock.AsyncMock(
                    return_value=RevRegDefState.STATE_FINISHED
                ),
                get_pending_revocations=mock.AsyncMock(return_value=[]),
            )

            result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_called_once_with(
                {
                    "result": {
                        "tails_local_path": "tails_location",
                        "tails_hash": "tails_hash",
                        "state": RevRegDefState.STATE_FINISHED,
                        "issuer_did": "issuer_id",
                        "pending_pub": [],
                        "revoc_reg_def": {
                            "ver": "1.0",
                            "id": self.rev_reg_id,
                            "revocDefType": "CL_ACCUM",
                            "tag": "tag",
                            "credDefId": "cred_def_id",
                        },
                        "max_cred_num": 100,
                        "record_id": record_id,
                        "tag": "tag",
                        "revoc_def_type": "CL_ACCUM",
                        "revoc_reg_id": self.rev_reg_id,
                        "cred_def_id": "cred_def_id",
                    }
                }
            )
            assert result is mock_json_response.return_value

    async def test_set_rev_reg_state_not_found(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        self.request.query = {
            "state": RevRegDefState.STATE_FINISHED,
        }

        with (
            mock.patch.object(
                test_module.AnonCredsRevocation,
                "get_created_revocation_registry_definition",
                mock.AsyncMock(),
            ) as mock_rev_reg_def,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_rev_reg_def.return_value = None

            with self.assertRaises(HTTPNotFound):
                await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_not_called()
