from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....config.injection_context import InjectionContext
from ....messaging.request_context import RequestContext
from ....ledger.base import BaseLedger
from ....wallet.base import BaseWallet
from ....wallet.basic import BasicWallet
from ....messaging.responder import BaseResponder, MockResponder
from ....storage.error import StorageNotFoundError
from .. import routes as test_module

from ..manager import RouteCoordinationManager, RouteCoordinationManagerError
from ..models.route_coordination import RouteCoordination
from ..models.routing_key import RoutingKey
from ..messages.mediation_request import MediationRequest
from ..messages.mediation_grant import MediationGrant
from ..messages.mediation_deny import MediationDeny
from ..messages.keylist_update_request import KeylistUpdateRequest
from ..messages.keylist_update_response import KeylistUpdateResponse
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from ..messages.inner.keylist_update_result import KeylistUpdateResult
from ..messages.keylist_query import KeylistQuery
from ..messages.inner.keylist_query_paginate import KeylistQueryPaginate
from ..messages.keylist import KeylistQueryResponse

class TestRouteCoordinationManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.wallet = BasicWallet()
        self.context.injector.bind_instance(BaseLedger, self.ledger)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.manager = RouteCoordinationManager(self.context)

    async def test_create_mediation_request(self):
        connection_id = ["dummy","dummy"]
        mediator_terms = ["dummy","dummy"]
        recipient_terms = ["dummy","dummy"]
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route_coord:
            stored_route_coord = await self.manager.create_mediation_request(
                connection_id= connection_id,
                recipient_terms= mediator_terms,
                mediator_terms= recipient_terms
                )
            save_route_coord.assert_called_once()
     
            assert stored_route_coord
            assert stored_route_coord.connection_id == connection_id

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_request(self):
        test_mediator_terms=["dummy"]
        mediation_request = MediationRequest(mediator_terms=test_mediator_terms)
        self.context.message = mediation_request
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"
        with async_mock.patch.object(
            RouteCoordination,
            "save",
            async_mock.CoroutineMock(return_value=mediation_request)
        ) as save_route_coord:
            response = await self.manager.receive_request()
            save_route_coord.assert_called_once()
            assert response.mediator_terms == test_mediator_terms

    async def test_create_accept_response(self):
        route_coordination = RouteCoordination(state = RouteCoordination.STATE_MEDIATION_RECEIVED)
       
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route_coord:
            grant_response, route_coordination_response = await self.manager.create_accept_response(
                    route_coordination
                )
            save_route_coord.assert_called_once()
     
            assert route_coordination_response.state == RouteCoordination.STATE_MEDIATION_GRANTED

    async def test_create_accept_response_not_response_state(self):
        route_coordination = RouteCoordination(state = RouteCoordination.STATE_MEDIATION_GRANTED)
       
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route_coord:
            
            with self.assertRaises(RouteCoordinationManagerError):
                await self.manager.create_accept_response(route_coordination)

    async def test_receive_mediation_grant(self):
        route_dummy = RouteCoordination(route_coordination_id="dummy")
        mediation_grant_message = MediationGrant()
        mediation_grant_message.routing_keys = []
        mediation_grant_message.routing_keys.append("H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV")
        request = async_mock.MagicMock(return_value=mediation_grant_message)
        self.context.message = request
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            route_out = await self.manager.receive_mediation_grant()
            retrieve_route.assert_called_once_with(
                self.context, {"thread_id": self.context.message._thread_id},
            )
            save_route.assert_called_once()

            assert route_out.state == (
                RouteCoordination.STATE_MEDIATION_GRANTED
            )

    async def test_create_deny_response(self):
        route_coordination = RouteCoordination(state = RouteCoordination.STATE_MEDIATION_RECEIVED)
       
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route_coord:
            deny_response, route_coordination_response = await self.manager.create_deny_response(
                    route_coordination
                )
            save_route_coord.assert_called_once()
     
            assert route_coordination_response.state == RouteCoordination.STATE_MEDIATION_DENIED

    async def test_receive_mediation_deny(self):
        route_dummy = RouteCoordination()
        request = async_mock.MagicMock()
        self.context.message = request
        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            route_out = await self.manager.receive_mediation_deny()
            retrieve_route.assert_called_once_with(
                self.context, {"thread_id": self.context.message._thread_id},
            )
            save_route.assert_called_once()

            assert route_out.state == (
                RouteCoordination.STATE_MEDIATION_DENIED
            )

    async def test_create_keylist_update_request(self):
        request = await self.manager.create_keylist_update_request(async_mock.MagicMock())
        assert request

    async def test_receive_keylist_update_request(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"], route_coordination_id="dummy")
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "add"
        test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)
        keylist_update_req = KeylistUpdateRequest()
        keylist_update_req.updates.append(test_updates)
        self.context.message = keylist_update_req
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route, async_mock.patch.object(
            RoutingKey, "save", autospec=True
        ) as save_key:
            retrieve_route.return_value = route_dummy
            await self.manager.receive_keylist_update_request()
            save_route.assert_called_once()

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_keylist_update_request_action_remove(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"], route_coordination_id="dummy")
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "remove"
        test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)
        keylist_update_req = KeylistUpdateRequest()
        keylist_update_req.updates.append(test_updates)
        self.context.message = keylist_update_req
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route, async_mock.patch.object(
            RoutingKey, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_key:
            retrieve_route.return_value = route_dummy
            await self.manager.receive_keylist_update_request()
            save_route.assert_called_once()

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_keylist_update_request_action_remove_no_recipient(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["dummy"], route_coordination_id="dummy")
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "remove"
        test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)
        keylist_update_req = KeylistUpdateRequest()
        keylist_update_req.updates.append(test_updates)
        self.context.message = keylist_update_req
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route, async_mock.patch.object(
            RoutingKey, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_key:
            retrieve_route.return_value = route_dummy
            await self.manager.receive_keylist_update_request()
            save_route.assert_called_once()

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_keylist_update_request_no_recipient(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["dummy"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "add"
        test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)
        keylist_update_req = KeylistUpdateRequest()
        keylist_update_req.updates.append(test_updates)
        self.context.message = keylist_update_req
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            await self.manager.receive_keylist_update_request()
            save_route.assert_called_once()

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_keylist_update_request_no_route(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["dummy"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "add"
        test_updates = KeylistUpdateRule(recipient_key=test_recipient_key_data, action=test_action_data)
        keylist_update_req = KeylistUpdateRequest()
        keylist_update_req.updates.append(test_updates)
        self.context.message = keylist_update_req
        self.context.connection_record = async_mock.CoroutineMock()
        self.context.connection_record.connection_id = "dummy"
        with async_mock.patch.object(
            RouteCoordination, "retrieve_by_connection_id", autospec=False
        ) as retrieve_route_coord:
            retrieve_route_coord.return_value = None
            with self.assertRaises(RouteCoordinationManagerError):
                await self.manager.receive_keylist_update_request()

    async def test_receive_keylist_update_response(self):
        route_dummy = RouteCoordination(routing_keys=["dummy"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "add"
        test_result_data = "success"
        test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        self.context.message = keylist_update_response
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            server_error, client_error = await self.manager.receive_keylist_update_response()
            save_route.assert_called_once()

            assert test_recipient_key_data in (
                        retrieve_route.return_value.routing_keys
                    )

    async def test_receive_keylist_update_response_action_remove(self):
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "remove"
        test_result_data = "success"
        test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        self.context.message = keylist_update_response
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            server_error, client_error = await self.manager.receive_keylist_update_response()
            save_route.assert_called_once()

            assert test_recipient_key_data not in (
                        retrieve_route.return_value.routing_keys
                    )

    async def test_receive_keylist_update_response_server_error(self):
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "remove"
        test_result_data = "server_error"
        test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        self.context.message = keylist_update_response
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            server_error, client_error = await self.manager.receive_keylist_update_response()
            save_route.assert_called_once()

            assert server_error[0] == test_recipient_key_data

    async def test_receive_keylist_update_response_client_error(self):
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "remove"
        test_result_data = "client_error"
        test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        self.context.message = keylist_update_response
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "save", autospec=True
        ) as save_route, async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route:
            retrieve_route.return_value = route_dummy
            server_error, client_error = await self.manager.receive_keylist_update_response()
            save_route.assert_called_once()

            assert client_error[0] == test_recipient_key_data
            
    async def test_receive_keylist_update_response_no_route(self):
        route_dummy = RouteCoordination(routing_keys=["dummy"])
        test_recipient_key_data = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        test_action_data = "add"
        test_result_data = "success"
        test_updated = KeylistUpdateResult(recipient_key=test_recipient_key_data, action=test_action_data, result=test_result_data)
        keylist_update_response = KeylistUpdateResponse()
        keylist_update_response.updated.append(test_updated)
        self.context.message = keylist_update_response
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "retrieve_by_connection_id", autospec=False
        ) as retrieve_route_coord:
            retrieve_route_coord.return_value = None
            with self.assertRaises(RouteCoordinationManagerError):
                await self.manager.receive_keylist_update_response()

    async def test_create_keylist_query_request_request(self):
        request = await self.manager.create_keylist_query_request_request(async_mock.MagicMock(),
                                        async_mock.MagicMock(),
                                        async_mock.MagicMock()
                                        )
        assert request

    async def test_receive_keylist_query_request(self):
        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"], route_coordination_id="dummy")
        test_filter_data = {
            "routing_key": [
                "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                "2wUJCoyzkJz1tTxehfT7Usq5FgJz3EQHBQC7b2mXxbRZ"
            ]
        }
        test_limit_data = 1
        test_offset_data = 1
        test_paginate_data = KeylistQueryPaginate(limit=test_limit_data, offset=test_offset_data)
        keylist_query = KeylistQuery()
        keylist_query.filter = test_filter_data
        keylist_query.paginate = test_paginate_data
        self.context.message = keylist_query
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        keys_dummy = []
        keys_dummy.append(RoutingKey(routing_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"))

        with async_mock.patch.object(
            RouteCoordination, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_route, async_mock.patch.object(
            RoutingKey, "query", autospec=True
        ) as retrieve_key:
            retrieve_key.return_value = keys_dummy
            await self.manager.receive_keylist_query_request()
            retrieve_key.assert_called_once()

            messages = responder.messages
            assert len(messages) == 1

    async def test_receive_keylist_query_request_no_route(self):
        route_dummy = RouteCoordination(routing_keys=["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"], route_coordination_id="dummy")
        test_filter_data = {
            "routing_key": [
                "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                "2wUJCoyzkJz1tTxehfT7Usq5FgJz3EQHBQC7b2mXxbRZ"
            ]
        }
        test_limit_data = 1
        test_offset_data = 1
        test_paginate_data = KeylistQueryPaginate(limit=test_limit_data, offset=test_offset_data)
        keylist_query = KeylistQuery()
        keylist_query.filter = test_filter_data
        keylist_query.paginate = test_paginate_data
        self.context.message = keylist_query
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        with async_mock.patch.object(
            RouteCoordination, "retrieve_by_connection_id", autospec=False
        ) as retrieve_route_coord:
            retrieve_route_coord.return_value = None
            with self.assertRaises(RouteCoordinationManagerError):
                await self.manager.receive_keylist_query_request()
