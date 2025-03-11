from unittest import IsolatedAsyncioTestCase
from unittest.mock import ANY

from ...admin.request_context import AdminRequestContext
from ...cache.base import BaseCache
from ...cache.in_memory import InMemoryCache
from ...connections.models.conn_record import ConnRecord
from ...storage.error import StorageNotFoundError
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module


class TestConnectionRoutes(IsolatedAsyncioTestCase):
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

    async def test_connections_list(self):
        self.request.query = {
            "invitation_id": "dummy",  # exercise tag filter assignment
            "their_role": ConnRecord.Role.REQUESTER.rfc160,
            "connection_protocol": "connections/1.0",
            "invitation_key": "some-invitation-key",
            "their_public_did": "a_public_did",
            "invitation_msg_id": "dummy_msg",
        }

        STATE_COMPLETED = ConnRecord.State.COMPLETED
        STATE_INVITATION = ConnRecord.State.INVITATION
        STATE_ABANDONED = ConnRecord.State.ABANDONED
        with mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec:
            mock_conn_rec.query = mock.CoroutineMock()
            mock_conn_rec.Role = ConnRecord.Role
            mock_conn_rec.State = mock.MagicMock(
                COMPLETED=STATE_COMPLETED,
                INVITATION=STATE_INVITATION,
                ABANDONED=STATE_ABANDONED,
                get=mock.MagicMock(
                    side_effect=[
                        ConnRecord.State.ABANDONED,
                        ConnRecord.State.COMPLETED,
                        ConnRecord.State.INVITATION,
                    ]
                ),
            )
            conns = [  # in ascending order here
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.COMPLETED.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.INVITATION.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.ABANDONED.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
            ]
            mock_conn_rec.query.return_value = conns

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.connections_list(self.request)
                mock_conn_rec.query.assert_called_once_with(
                    ANY,
                    {
                        "invitation_id": "dummy",
                        "invitation_key": "some-invitation-key",
                        "their_public_did": "a_public_did",
                        "invitation_msg_id": "dummy_msg",
                    },
                    limit=100,
                    offset=0,
                    order_by="id",
                    descending=False,
                    post_filter_positive={
                        "their_role": list(ConnRecord.Role.REQUESTER.value),
                        "connection_protocol": "connections/1.0",
                    },
                    alt=True,
                )
                mock_response.assert_called_once_with(
                    {
                        "results": [
                            {
                                k: c.serialize.return_value[k]
                                for k in ["state", "created_at"]
                            }
                            for c in conns
                        ]
                    }  # sorted
                )

    async def test_connections_list_x(self):
        self.request.query = {
            "their_role": ConnRecord.Role.REQUESTER.rfc160,
            "alias": "my connection",
            "state": ConnRecord.State.COMPLETED.rfc23,
        }

        STATE_COMPLETED = ConnRecord.State.COMPLETED
        ROLE_REQUESTER = ConnRecord.Role.REQUESTER
        with mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec:
            mock_conn_rec.Role = mock.MagicMock(return_value=ROLE_REQUESTER)
            mock_conn_rec.State = mock.MagicMock(
                COMPLETED=STATE_COMPLETED,
                get=mock.MagicMock(return_value=ConnRecord.State.COMPLETED),
            )
            mock_conn_rec.query = mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_list(self.request)

    async def test_connections_retrieve(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock(return_value={"hello": "world"})

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_retrieve(self.request)
            mock_response.assert_called_once_with({"hello": "world"})

    async def test_connections_endpoints(self):
        self.request.match_info = {"conn_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "BaseConnectionManager", autospec=True
            ) as mock_conn_mgr_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_mgr_cls.return_value = mock.MagicMock(
                get_endpoints=mock.CoroutineMock(
                    return_value=("localhost:8080", "1.2.3.4:8081")
                )
            )
            await test_module.connections_endpoints(self.request)
            mock_response.assert_called_once_with(
                {
                    "my_endpoint": "localhost:8080",
                    "their_endpoint": "1.2.3.4:8081",
                }
            )

    async def test_connections_endpoints_x(self):
        self.request.match_info = {"conn_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "BaseConnectionManager", autospec=True
            ) as mock_conn_mgr_cls,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_conn_mgr_cls.return_value = mock.MagicMock(
                get_endpoints=mock.CoroutineMock(side_effect=StorageNotFoundError())
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_endpoints(self.request)

            mock_conn_mgr_cls.return_value = mock.MagicMock(
                get_endpoints=mock.CoroutineMock(side_effect=test_module.WalletError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_endpoints(self.request)

    async def test_connections_metadata(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(
                mock_conn_rec, "metadata_get_all", mock.CoroutineMock()
            ) as mock_metadata_get_all,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_metadata_get_all.return_value = {"hello": "world"}

            await test_module.connections_metadata(self.request)
            mock_metadata_get_all.assert_called_once()
            mock_response.assert_called_once_with({"results": {"hello": "world"}})

    async def test_connections_metadata_get_single(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        self.request.query = {"key": "test"}

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(mock_conn_rec, "metadata_get_all", mock.CoroutineMock()),
            mock.patch.object(
                mock_conn_rec, "metadata_get", mock.CoroutineMock()
            ) as mock_metadata_get,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_metadata_get.return_value = {"test": "value"}

            await test_module.connections_metadata(self.request)
            mock_metadata_get.assert_called_once()
            mock_response.assert_called_once_with({"results": {"test": "value"}})

    async def test_connections_metadata_x(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(
                mock_conn_rec, "metadata_get_all", mock.CoroutineMock()
            ) as mock_metadata_get_all,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_metadata_get_all.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_metadata(self.request)

            mock_metadata_get_all.side_effect = test_module.BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_metadata(self.request)

    async def test_connections_metadata_set(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        self.request.json = mock.CoroutineMock(
            return_value={"metadata": {"hello": "world"}}
        )

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(
                mock_conn_rec, "metadata_get_all", mock.CoroutineMock()
            ) as mock_metadata_get_all,
            mock.patch.object(
                mock_conn_rec, "metadata_set", mock.CoroutineMock()
            ) as mock_metadata_set,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_metadata_get_all.return_value = {"hello": "world"}

            await test_module.connections_metadata_set(self.request)
            mock_metadata_set.assert_called_once()
            mock_response.assert_called_once_with({"results": {"hello": "world"}})

    async def test_connections_metadata_set_x(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        self.request.json = mock.CoroutineMock(
            return_value={"metadata": {"hello": "world"}}
        )

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(mock_conn_rec, "metadata_get_all", mock.CoroutineMock()),
            mock.patch.object(
                mock_conn_rec, "metadata_set", mock.CoroutineMock()
            ) as mock_metadata_set,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_metadata_set.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_metadata_set(self.request)

            mock_metadata_set.side_effect = test_module.BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_metadata_set(self.request)

    async def test_connections_retrieve_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_retrieve(self.request)

    async def test_connections_retrieve_x(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock(side_effect=test_module.BaseModelError())

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_retrieve(self.request)

    async def test_connections_remove(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.delete_record = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_remove(self.request)
            mock_response.assert_called_once_with({})

    async def test_connections_remove_cache_key(self):
        cache = InMemoryCache()
        profile = self.context.profile
        await cache.set("conn_rec_state::dummy", "active")
        profile.context.injector.bind_instance(BaseCache, cache)
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.delete_record = mock.CoroutineMock()
        assert (await cache.get("conn_rec_state::dummy")) == "active"
        with (
            mock.patch.object(
                test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_remove(self.request)
            mock_response.assert_called_once_with({})
            assert not (await cache.get("conn_rec_state::dummy"))

    async def test_connections_remove_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_remove(self.request)

    async def test_connections_remove_x(self):
        self.request.match_info = {"conn_id": "dummy"}
        mock_conn_rec = mock.MagicMock(
            delete_record=mock.CoroutineMock(side_effect=test_module.StorageError())
        )

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_remove(self.request)

    async def test_connections_create_static(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        self.request.query = {
            "auto_accept": "true",
            "alias": "alias",
        }
        self.request.match_info = {"conn_id": "dummy"}

        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()
        mock_my_info = mock.MagicMock()
        mock_my_info.did = "my_did"
        mock_my_info.verkey = "my_verkey"
        mock_their_info = mock.MagicMock()
        mock_their_info.did = "their_did"
        mock_their_info.verkey = "their_verkey"

        with (
            mock.patch.object(
                test_module, "BaseConnectionManager", autospec=True
            ) as mock_conn_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_conn_mgr.return_value.create_static_connection = mock.CoroutineMock(
                return_value=(mock_my_info, mock_their_info, mock_conn_rec)
            )

            await test_module.connections_create_static(self.request)
            mock_response.assert_called_once_with(
                {
                    "my_did": mock_my_info.did,
                    "my_verkey": mock_my_info.verkey,
                    "their_did": mock_their_info.did,
                    "their_verkey": mock_their_info.verkey,
                    "my_endpoint": self.context.settings.get("default_endpoint"),
                    "record": mock_conn_rec.serialize.return_value,
                }
            )

    async def test_connections_create_static_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        self.request.query = {
            "auto_accept": "true",
            "alias": "alias",
        }
        self.request.match_info = {"conn_id": "dummy"}

        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()
        mock_my_info = mock.MagicMock()
        mock_my_info.did = "my_did"
        mock_my_info.verkey = "my_verkey"
        mock_their_info = mock.MagicMock()
        mock_their_info.did = "their_did"
        mock_their_info.verkey = "their_verkey"

        with mock.patch.object(
            test_module, "BaseConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_mgr.return_value.create_static_connection = mock.CoroutineMock(
                side_effect=test_module.WalletError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_create_static(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
