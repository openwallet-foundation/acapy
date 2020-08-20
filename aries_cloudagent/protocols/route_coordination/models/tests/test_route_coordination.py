from unittest import TestCase as UnitTestCase
from .....config.injection_context import InjectionContext
from .....messaging.request_context import RequestContext
from .....storage.basic import BasicStorage, StorageRecord
from .....storage.base import BaseStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock
from .....cache.base import BaseCache
import json

from ..route_coordination import RouteCoordination


test_route_coordination_id = "dummy"
test_connection_id = "dummy"
test_state = "dummy"
test_mediator_terms = ["dummy","dummy"]
test_recipient_terms = ["dummy","dummy"]
test_routing_keys = ["dummy","dummy"]
test_routing_endpoint = "dummy"
test_role = "dummy"
test_thread_id = "dummy"

class TestRouteCoordinationUnit(UnitTestCase):
    def test_routing_key(self):
        routing_key = RouteCoordination(
            route_coordination_id=test_route_coordination_id,
            connection_id=test_connection_id,
            state=test_state,
            mediator_terms=test_mediator_terms,
            recipient_terms=test_recipient_terms,
            routing_keys=test_routing_keys,
            routing_endpoint=test_routing_endpoint,
            role=test_role,
            thread_id=test_thread_id
        )
       
        assert routing_key.route_coordination_id == test_route_coordination_id
        assert routing_key.record_value == {
            "connection_id":test_connection_id,
            "state":test_state,
            "mediator_terms":test_mediator_terms,
            "recipient_terms":test_recipient_terms,
            "routing_keys":test_routing_keys,
            "routing_endpoint":test_routing_endpoint,
            "role":test_role
        }

class TestRouteCoordinationAsync(AsyncTestCase):  
    async def test_retrieve_by_thread(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_value = {
                "connection_id":test_connection_id,
                "state":test_state,
                "mediator_terms":test_mediator_terms,
                "recipient_terms":test_recipient_terms,
                "routing_keys":test_routing_keys,
                "routing_endpoint":test_routing_endpoint,
                "role":test_role,
                "thread_id":test_thread_id
            }

        stored = StorageRecord(
            RouteCoordination.RECORD_TYPE, json.dumps(record_value), {}, {"thread_id"}
        )

        mock_storage.search_records.return_value.__aiter__.return_value = [stored]
        result = await RouteCoordination.retrieve_by_thread(context, test_thread_id)

        tag_filter = {"thread_id": test_thread_id}

        mock_storage.search_records.assert_called_once_with(
            RouteCoordination.RECORD_TYPE, tag_filter, None, {"retrieveTags": False}
        )
        
        assert result and isinstance(result, RouteCoordination)
        assert result.mediator_terms == record_value.get("mediator_terms")

    async def test_retrieve_by_connection_id(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_value = {
                "connection_id":test_connection_id,
                "state":test_state,
                "mediator_terms":test_mediator_terms,
                "recipient_terms":test_recipient_terms,
                "routing_keys":test_routing_keys,
                "routing_endpoint":test_routing_endpoint,
                "role":test_role,
                "thread_id":test_thread_id
            }
            
        stored = StorageRecord(
            RouteCoordination.RECORD_TYPE, json.dumps(record_value), {}, {"connection_id"}
        )

        mock_storage.search_records.return_value.__aiter__.return_value = [stored]
        result = await RouteCoordination.retrieve_by_connection_id(context, test_connection_id)

        tag_filter = {"connection_id": test_connection_id}

        mock_storage.search_records.assert_called_once_with(
            RouteCoordination.RECORD_TYPE, tag_filter, None, {"retrieveTags": False}
        )
        
        assert result and isinstance(result, RouteCoordination)
        assert result.mediator_terms == record_value.get("mediator_terms")