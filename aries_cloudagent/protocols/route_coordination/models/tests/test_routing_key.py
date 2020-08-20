from unittest import TestCase as UnitTestCase
from .....config.injection_context import InjectionContext
from .....messaging.request_context import RequestContext
from .....storage.basic import BasicStorage, StorageRecord
from .....storage.base import BaseStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock
from .....cache.base import BaseCache
import json

from ..routing_key import RoutingKey


test_routing_key_id = "dummy"
test_route_coordination_id = "dummy"
test_routing_key = "dummy"

class TestRoutingKeyUnit(UnitTestCase):
    def test_routing_key(self):
        routing_key = RoutingKey(
            routing_key_id=test_routing_key_id,
            route_coordination_id=test_route_coordination_id,
            routing_key=test_routing_key
        )
       
        assert routing_key.routing_key_id == test_routing_key_id
        assert routing_key.record_value == {
            "route_coordination_id":test_route_coordination_id,
            "routing_key":test_routing_key
        }

class TestRoutingKeyAsync(AsyncTestCase):
    async def test_retrieve_by_routing_key_and_coord_id(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_value = {
                        "routing_key": test_routing_key,
                        "route_coordination_id": test_route_coordination_id
                    }
        
        stored = StorageRecord(
            RoutingKey.RECORD_TYPE, json.dumps(record_value), {}, {
                        "routing_key",
                        "route_coordination_id",
                    }
        )

        mock_storage.search_records.return_value.__aiter__.return_value = [stored]
        result = await RoutingKey.retrieve_by_routing_key_and_coord_id(context, test_routing_key, test_route_coordination_id)
        mock_storage.search_records.assert_called_once_with(
            RoutingKey.RECORD_TYPE, record_value, None, {"retrieveTags": False}
        )
        
        assert result and isinstance(result, RoutingKey)
        assert result.routing_key == record_value.get("routing_key")
        assert result.route_coordination_id == record_value.get("route_coordination_id")