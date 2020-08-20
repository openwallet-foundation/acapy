from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from ....storage.error import StorageNotFoundError
from ....holder.base import BaseHolder
from ....messaging.request_context import RequestContext
from .. import routes as test_module

from ..models.route_coordination import RouteCoordination


class TestRouteCoordinationRoutes(AsyncTestCase):
    async def test_create_mediation_request(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"connection_id": "dummy"}
        mock.json = async_mock.CoroutineMock(
            return_value={
                "recipient_terms": ["dummy"],
                "mediator_terms": ["dummy"]
            }
        )
        mock.app = {
            "request_context": "context",
        }
        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_route_coordination = async_mock.MagicMock()
            mock_route_manager.return_value.create_mediation_request.return_value = (
                mock_route_coordination
            )

            await test_module.create_mediation_request(mock)

            mock_response.assert_called_once_with(
                mock_route_coordination.serialize()
            )

    async def test_create_mediation_request_no_conn_record(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()
        mock_request.app = {
            "request_context": "context",
        }
        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record:

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.create_mediation_request(mock_request)

    async def test_routing_list(self):
        mock = async_mock.MagicMock()
        mock.query = {"connection_id": "dummy", 
                    "route_coordination_id": "dummy",
                    "initiator": "self",
                    "state": "mediation_request",
                    "role": "mediator"
                }
        mock.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coordination:

            mock_route_coordination.query = async_mock.CoroutineMock()
            mock_route_coordination.query.return_value = [mock_route_coordination]
            mock_route_coordination.serialize = async_mock.MagicMock()
            mock_route_coordination.serialize.return_value = {"route_coordination_id": "dummy", "created_at": "dummy"}

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.routing_list(mock)
                mock_response.assert_called_once_with(
                    {"results": [mock_route_coordination.serialize.return_value]}
                )

    async def test_grant_mediate_request(self):
            mock = async_mock.MagicMock()
            mock.json = async_mock.CoroutineMock()

            mock.app = {
                "outbound_message_router": async_mock.CoroutineMock(),
                "request_context": async_mock.patch.object(
                    aio_web, "BaseRequest", autospec=True
                ),
            }

            mock.match_info = {"id": "dummy"}

            with async_mock.patch.object(
                test_module, "ConnectionRecord", autospec=True
            ) as mock_connection_record, async_mock.patch.object(
                test_module, "RouteCoordinationManager", autospec=True
            ) as mock_route_manager, async_mock.patch.object(
                test_module, "RouteCoordination", autospec=True
            ) as mock_route_coord, async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:

                mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
                mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

                mock_route_manager.return_value.create_accept_response = (
                    async_mock.CoroutineMock()
                )

                mock_routing_record = async_mock.MagicMock()

                mock_route_manager.return_value.create_accept_response.return_value = (
                    async_mock.MagicMock(),
                    mock_routing_record
                )

                await test_module.grant_mediate_request(mock)

                mock_response.assert_called_once_with(
                    mock_routing_record.serialize.return_value
                )

    async def test_grant_mediate_request_no_route_coord(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            # Emulate storage not found (no route coordination record)
            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_accept_response = (
                async_mock.CoroutineMock()
            )
            mock_route_manager.return_value.create_accept_response.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.grant_mediate_request(mock)

    async def test_grant_mediate_request_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
            mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_accept_response = (
                async_mock.CoroutineMock()
            )
            mock_route_manager.return_value.create_accept_response.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.grant_mediate_request(mock)

    async def test_deny_mediate_request(self):
            mock = async_mock.MagicMock()
            mock.json = async_mock.CoroutineMock()

            mock.app = {
                "outbound_message_router": async_mock.CoroutineMock(),
                "request_context": async_mock.patch.object(
                    aio_web, "BaseRequest", autospec=True
                ),
            }

            mock.json = async_mock.CoroutineMock(
                return_value={
                    "recipient_terms": ["dummy"],
                    "mediator_terms": ["dummy"]
                }
            )

            with async_mock.patch.object(
                test_module, "ConnectionRecord", autospec=True
            ) as mock_connection_record, async_mock.patch.object(
                test_module, "RouteCoordinationManager", autospec=True
            ) as mock_route_manager, async_mock.patch.object(
                test_module, "RouteCoordination", autospec=True
            ) as mock_route_coord, async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:

                mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
                mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

                mock_route_manager.return_value.create_deny_response = (
                    async_mock.CoroutineMock()
                )

                mock_route_coordination = async_mock.MagicMock()

                mock_route_manager.return_value.create_deny_response.return_value = (
                   async_mock.MagicMock(),
                   mock_route_coordination,
                )

                await test_module.deny_mediate_request(mock)

                mock_response.assert_called_once_with(
                    mock_route_coordination.serialize.return_value
                )

    async def test_deny_mediate_request_no_route_coord(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.json = async_mock.CoroutineMock(
                return_value={
                    "recipient_terms": ["dummy"],
                    "mediator_terms": ["dummy"]
                }
            )

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            # Emulate storage not found (no route coordination record)
            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_deny_response = (
                async_mock.CoroutineMock()
            )
            mock_route_manager.return_value.create_deny_response.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.deny_mediate_request(mock)

    async def test_deny_mediate_request_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.json = async_mock.CoroutineMock(
                return_value={
                    "recipient_terms": ["dummy"],
                    "mediator_terms": ["dummy"]
                }
            )

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
            mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_deny_response = (
                async_mock.CoroutineMock()
            )
            mock_route_manager.return_value.create_deny_response.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.deny_mediate_request(mock)

    async def test_keylist_update(self):
            mock = async_mock.MagicMock()
            mock.json = async_mock.CoroutineMock()

            mock.app = {
                "outbound_message_router": async_mock.CoroutineMock(),
                "request_context": async_mock.patch.object(
                    aio_web, "BaseRequest", autospec=True
                ),
            }
            
            mock_updates = {"content": "hello"}

            mock.match_info = {"id": "dummy"}
            mock.json = async_mock.CoroutineMock(
                            return_value={"updates":mock_updates}
                        )
            with async_mock.patch.object(
                test_module, "ConnectionRecord", autospec=True
            ) as mock_connection_record, async_mock.patch.object(
                test_module, "RouteCoordinationManager", autospec=True
            ) as mock_route_manager, async_mock.patch.object(
                test_module, "RouteCoordination", autospec=True
            ) as mock_route_coord, async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:

                mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
                mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

                mock_route_manager.return_value.create_keylist_update_request = (
                    async_mock.CoroutineMock()
                )
                mock_route_manager.return_value.create_keylist_update_request.return_value = (
                   async_mock.MagicMock()
                )

                await test_module.keylist_update(mock)

                mock_response.assert_called_once_with(
                    {"updates": mock_updates}
                )

    async def test_keylist_update_no_route_coord(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}
        mock.json = async_mock.CoroutineMock(
                            return_value={'updates': {'content': 'hello'}}
                        )

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            # Emulate storage not found (no route coordination record)
            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_keylist_update_request.return_value = (
               async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.keylist_update(mock)

    async def test_keylist_update_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}
        mock.json = async_mock.CoroutineMock(
                            return_value={'updates': {'content': 'hello'}}
                        )

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
            mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_keylist_update_request.return_value = (
               async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.keylist_update(mock)

    async def test_keylist_query(self):
            mock = async_mock.MagicMock()
            mock.json = async_mock.CoroutineMock()

            mock.app = {
                "outbound_message_router": async_mock.CoroutineMock(),
                "request_context": async_mock.patch.object(
                    aio_web, "BaseRequest", autospec=True
                ),
            }
            
            mock.match_info = {"id": "dummy"}
            mock.json = async_mock.CoroutineMock()
            with async_mock.patch.object(
                test_module, "ConnectionRecord", autospec=True
            ) as mock_connection_record, async_mock.patch.object(
                test_module, "RouteCoordinationManager", autospec=True
            ) as mock_route_manager, async_mock.patch.object(
                test_module, "RouteCoordination", autospec=True
            ) as mock_route_coord, async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:

                mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
                
                mock_route_coord_value = async_mock.CoroutineMock()
                
                mock_route_coord.retrieve_by_id.return_value = (mock_route_coord_value)

                mock_route_manager.return_value.create_keylist_query_request_request = (
                    async_mock.CoroutineMock()
                )
                mock_route_manager.return_value.create_keylist_query_request_request.return_value = (
                   async_mock.MagicMock()
                )

                await test_module.keylist_query(mock)

                mock_response.assert_called_once_with(
                    {
                        "route_coordination_id": mock_route_coord_value.connection_id
                    }
                )

    async def test_keylist_query_no_route_coord(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}
        mock.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            # Emulate storage not found (no route coordination record)
            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_keylist_query_request_request.return_value = (
               async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.keylist_query(mock)

    async def test_keylist_query_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        
        mock.match_info = {"id": "dummy"}
        mock.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "RouteCoordinationManager", autospec=True
        ) as mock_route_manager, async_mock.patch.object(
            test_module, "RouteCoordination", autospec=True
        ) as mock_route_coord:

            mock_route_coord.retrieve_by_id = async_mock.CoroutineMock()
            mock_route_coord.retrieve_by_id.return_value = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            mock_route_manager.return_value.create_keylist_query_request_request.return_value = (
               async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.keylist_query(mock)
