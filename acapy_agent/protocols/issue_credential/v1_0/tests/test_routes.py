from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext
from .....tests import mock
from .....utils.testing import create_test_profile
from .....wallet.base import BaseWallet
from .. import routes as test_module
from . import CRED_DEF_ID


class TestCredentialRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )

    async def test_credential_exchange_list(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.query = mock.CoroutineMock()
            mock_cred_ex.query.return_value = [mock_cred_ex]
            mock_cred_ex.serialize = mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.credential_exchange_list(self.request)
                mock_response.assert_called_once_with(
                    {"results": [mock_cred_ex.serialize.return_value]}
                )

    async def test_credential_exchange_list_x(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.query = mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_list(self.request)

    async def test_credential_exchange_retrieve(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex
            mock_cred_ex.serialize = mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.credential_exchange_retrieve(self.request)
                mock_response.assert_called_once_with(mock_cred_ex.serialize.return_value)

    async def test_credential_exchange_retrieve_not_found(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_retrieve_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex
            mock_cred_ex.serialize = mock.MagicMock(
                side_effect=test_module.BaseModelError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_create(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_cred_ex_record = mock.MagicMock()
            mock_cred_offer = mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.return_value = (
                mock_cred_ex_record,
                mock_cred_offer,
            )

            await test_module.credential_exchange_create(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_create_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_credential_manager.return_value.prepare_send.side_effect = (
                test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create(self.request)

    async def test_credential_exchange_create_no_proposal(self):
        conn_id = "connection-id"

        self.request.json = mock.CoroutineMock(return_value={"connection_id": conn_id})

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create(self.request)
        assert "credential_proposal" in str(context.exception)

    async def test_credential_exchange_send(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_cred_ex_record = mock.MagicMock()
            mock_cred_offer = mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.return_value = (
                mock_cred_ex_record,
                mock_cred_offer,
            )

            await test_module.credential_exchange_send(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_no_proposal(self):
        conn_id = "connection-id"

        self.request.json = mock.CoroutineMock(return_value={"connection_id": conn_id})

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send(self.request)
        assert "credential_proposal" in str(context.exception)

    async def test_credential_exchange_send_no_conn_record(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_not_ready(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
        ):
            mock_cred_ex_record = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_offer = mock.MagicMock()

            mock_credential_manager.return_value = mock.MagicMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock.CoroutineMock(),
                        mock.CoroutineMock(),
                    )
                ),
                prepare_send=mock.CoroutineMock(
                    return_value=(
                        mock_cred_ex_record,
                        mock_cred_offer,
                    )
                ),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_proposal(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex_record = mock.MagicMock()
            mock_credential_manager.return_value.create_proposal.return_value = (
                mock_cred_ex_record
            )
            await test_module.credential_exchange_send_proposal(self.request)

            self.request["outbound_message_router"].assert_awaited_once_with(
                mock_cred_ex_record.credential_proposal_dict, connection_id=conn_id
            )
            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_proposal_no_conn_record(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_proposal.return_value = (
                mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_deser_x(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deser:
            mock_preview_deser.side_effect = test_module.BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_not_ready(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module.CredentialPreview, "deserialize", autospec=True
            ),
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_proposal.return_value = (
                mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_x(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            mock_cred_ex_record = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_credential_manager.return_value.create_proposal.return_value = (
                mock_cred_ex_record
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_create_free_offer(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"debug.auto_respond_credential_offer": True})

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_cred_ex_record = mock.MagicMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_create_free_offer_no_cred_def_id(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_no_preview(self):
        self.request.json = mock.CoroutineMock()
        self.request.json.return_value = {"comment": "comment", "cred_def_id": "dummy"}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_no_conn_id_no_public_did(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"default_endpoint": "http://1.2.3.4:8081"})
        self.session_inject[BaseWallet] = mock.MagicMock(
            get_public_did=mock.CoroutineMock(return_value=None),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_deser_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.side_effect = (
                test_module.BaseModelError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            mock_cred_ex_record = mock.MagicMock(
                serialize=mock.MagicMock(
                    side_effect=test_module.BaseModelError(),
                ),
                save_error_state=mock.CoroutineMock(),
            )
            mock_credential_manager.return_value = mock.MagicMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock_cred_ex_record,
                        mock.MagicMock(),
                    )
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_send_free_offer(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_free_offer_no_cred_def_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.json.return_value = {
            "comment": "comment",
            "credential_preview": "dummy",
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_no_preview(self):
        self.request.json = mock.CoroutineMock()
        self.request.json.return_value = {
            "comment": "comment",
            "cred_def_id": CRED_DEF_ID,
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_no_conn_record(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": "dummy",
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.json.return_value["auto_issue"] = True

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": CRED_DEF_ID,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cred_ex_record = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )

            mock_credential_manager.return_value = mock.MagicMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock_cred_ex_record,
                        mock.MagicMock(),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_bound_offer(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_offer(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_bound_offer_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_no_conn_record(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cred_ex.STATE_PROPOSAL_RECEIVED,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_bad_state(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cred_ex.STATE_ACKED,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_not_ready(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_request(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.create_request.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_request(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_request_no_conn(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "OobRecord", autospec=True) as mock_oob_rec,
            mock.patch.object(
                test_module, "default_did_from_verkey", autospec=True
            ) as mock_default_did_from_verkey,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_oob_rec.retrieve_by_tag_filter = mock.CoroutineMock(
                return_value=mock.MagicMock(our_recipient_key="our-recipient_key")
            )
            mock_default_did_from_verkey.return_value = "holder-did"

            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )
            mock_cred_ex.retrieve_by_id.return_value.connection_id = None

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.create_request.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_request(self.request)

            mock_credential_manager.return_value.create_request.assert_called_once_with(
                mock_cred_ex.retrieve_by_id.return_value, "holder-did"
            )
            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )
            mock_default_did_from_verkey.assert_called_once_with("our-recipient_key")

    async def test_credential_exchange_send_request_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_send_request_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock.MagicMock(
                state=mock_cred_ex.STATE_OFFER_RECEIVED,
                save_error_state=mock.CoroutineMock(),
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_send_request_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = mock.CoroutineMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_issue(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.issue_credential.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_issue_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cred_ex_rec = mock.MagicMock(
            connection_id="dummy",
            serialize=mock.MagicMock(),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex_cls,
        ):
            mock_cred_ex_rec.state = mock_cred_ex_cls.STATE_REQUEST_RECEIVED
            mock_cred_ex_cls.retrieve_by_id = mock.CoroutineMock(
                return_value=mock_cred_ex_rec
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.issue_credential = mock.CoroutineMock()
            mock_credential_manager.return_value.issue_credential.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.issue_credential = mock.CoroutineMock()
            mock_credential_manager.return_value.issue_credential.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_rev_reg_full(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cred_ex_rec = mock.MagicMock(
            connection_id="dummy",
            serialize=mock.MagicMock(),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex_cls,
        ):
            mock_cred_ex_cls.state = mock_cred_ex_cls.STATE_REQUEST_RECEIVED
            mock_cred_ex_cls.retrieve_by_id = mock.CoroutineMock(
                return_value=mock_cred_ex_rec
            )

            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = True

            mock_issue_cred = mock.CoroutineMock(
                side_effect=test_module.IndyIssuerError()
            )
            mock_credential_manager.return_value.issue_credential = mock_issue_cred

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_deser_x(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cred_ex_rec = mock.MagicMock(
            connection_id="dummy",
            serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex_cls,
        ):
            mock_cred_ex_cls.retrieve_by_id = mock.CoroutineMock(
                return_value=mock_cred_ex_rec
            )
            mock_credential_manager.return_value = mock.MagicMock(
                issue_credential=mock.CoroutineMock(
                    return_value=(
                        mock_cred_ex_rec,
                        mock.MagicMock(),
                    )
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_store(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex_record
            )
            mock_credential_manager.return_value.send_credential_ack.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_store_bad_cred_id_json(self):
        self.request.json = mock.CoroutineMock(
            side_effect=test_module.JSONDecodeError("Nope", "Nope", 0)
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            mock_cred_ex_record = mock.MagicMock()

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex_record
            )
            mock_credential_manager.return_value.send_credential_ack.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_store_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cred_ex.STATE_CREDENTIAL_RECEIVED,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex
            )
            mock_credential_manager.return_value.send_credential_ack.return_value = (
                mock_cred_ex,
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(test_module, "CredentialManager", autospec=True),
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_x(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "CredentialManager", autospec=True
            ) as mock_credential_manager,
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex_cls,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cred_ex_record = mock.MagicMock(
                state=mock_cred_ex_cls.STATE_CREDENTIAL_RECEIVED,
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_ex_cls.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )

            mock_credential_manager.return_value = mock.MagicMock(
                store_credential=mock.CoroutineMock(return_value=mock_cred_ex_record),
                send_credential_ack=mock.CoroutineMock(
                    return_value=(mock_cred_ex_record, mock.MagicMock())
                ),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_remove(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex

            mock_cred_ex.delete_record = mock.CoroutineMock()

            await test_module.credential_exchange_remove(self.request)

            mock_response.assert_called_once_with({})

    async def test_credential_exchange_remove_bad_cred_ex_id(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            # Emulate storage not found (bad cred ex id)
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_remove_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            # Emulate storage not found (bad cred ex id)
            mock_rec = mock.MagicMock(
                delete_record=mock.CoroutineMock(side_effect=test_module.StorageError())
            )
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(return_value=mock_rec)

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_problem_report(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}
        magic_report = mock.MagicMock()

        with (
            mock.patch.object(test_module, "CredentialManager", autospec=True),
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(
                test_module, "problem_report_for_record", mock.MagicMock()
            ) as mock_problem_report,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
            )
            mock_problem_report.return_value = magic_report

            await test_module.credential_exchange_problem_report(self.request)

            self.request["outbound_message_router"].assert_awaited_once_with(
                magic_report,
                connection_id=mock_cred_ex.retrieve_by_id.return_value.connection_id,
            )
            mock_response.assert_called_once_with({})

    async def test_credential_exchange_problem_report_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_problem_report(self.request)

    async def test_credential_exchange_problem_report_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "CredentialManager", autospec=True),
            mock.patch.object(test_module, "problem_report_for_record", mock.MagicMock()),
            mock.patch.object(
                test_module, "V10CredentialExchange", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    save_error_state=mock.CoroutineMock(
                        side_effect=test_module.StorageError()
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_problem_report(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
