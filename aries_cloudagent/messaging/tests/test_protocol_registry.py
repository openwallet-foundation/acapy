from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.injection_context import InjectionContext

from ..error import MessageParseError
from ..protocol_registry import ProtocolRegistry


class TestProtocolRegistry(AsyncTestCase):
    no_type_message = {"a": "b"}
    unknown_type_message = {"@type": 1}
    test_message_type = "PROTOCOL/MESSAGE"
    test_protocol = "PROTOCOL"
    test_protocol_queries = ["*", "PROTOCOL", "PROTO*"]
    test_protocol_queries_fail = ["", "nomatch", "nomatch*"]
    test_message_handler = "fake_handler"
    test_controller = "fake_controller"

    def setUp(self):
        self.registry = ProtocolRegistry()

    def test_protocols(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_handler}
        )
        self.registry.register_controllers(
            {self.test_message_type: self.test_controller}
        )

        assert list(self.registry.message_types) == [self.test_message_type]
        assert list(self.registry.protocols) == [self.test_protocol]
        assert self.registry.controllers == {
            self.test_message_type: self.test_controller
        }

    def test_message_type_query(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_handler}
        )
        for q in self.test_protocol_queries:
            matches = self.registry.protocols_matching_query(q)
            assert tuple(matches) == (self.test_protocol,)
        for q in self.test_protocol_queries_fail:
            matches = self.registry.protocols_matching_query(q)
            assert matches == ()

    async def test_disclosed(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_handler}
        )
        mock = async_mock.MagicMock()
        mock.return_value.check_access = async_mock.CoroutineMock()
        mock.return_value.check_access.return_value = True
        mock.return_value.determine_roles = async_mock.CoroutineMock()
        mock.return_value.determine_roles.return_value = ["ROLE"]
        self.registry.register_controllers({self.test_protocol: mock})
        protocols = [self.test_protocol]
        ctx = InjectionContext()
        published = await self.registry.prepare_disclosed(ctx, protocols)
        mock.return_value.check_access.assert_called_once_with(ctx)
        mock.return_value.determine_roles.assert_called_once_with(ctx)
        assert len(published) == 1
        assert published[0]["pid"] == self.test_protocol
        assert published[0]["roles"] == ["ROLE"]

    def test_repr(self):
        assert type(repr(self.registry)) is str
