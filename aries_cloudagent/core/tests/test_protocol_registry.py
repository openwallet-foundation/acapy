from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.injection_context import InjectionContext
from ...utils.classloader import ClassLoader

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

    async def test_disclosed_str(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_handler}
        )
        self.registry.register_controllers({self.test_protocol: "mock-class-name"})
        protocols = [self.test_protocol]
        ctx = InjectionContext()

        class Mockery:
            def __init__(self, protocol):
                self.protocol = protocol

            async def check_access(self, context):
                return False

        with async_mock.patch.object(
            ClassLoader, "load_class", async_mock.MagicMock()
        ) as load_class:
            load_class.return_value = Mockery
            published = await self.registry.prepare_disclosed(ctx, protocols)
            assert not published

    def test_resolve_message_class_str(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_handler}
        )
        mock_class = async_mock.MagicMock()
        with async_mock.patch.object(
            ClassLoader, "load_class", async_mock.MagicMock()
        ) as load_class:
            load_class.return_value = mock_class
            result = self.registry.resolve_message_class(self.test_message_type)
            assert result == mock_class

    def test_resolve_message_class_no_major_version_support(self):
        result = self.registry.resolve_message_class("proto/1.2/hello")
        assert result is None

    def test_resolve_message_load_class_str(self):
        message_type_a = "proto/1.2/aaa"
        self.registry.register_message_types(
            {message_type_a: self.test_message_handler},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 2,
                "path": "v1_2",
            },
        )
        mock_class = async_mock.MagicMock()
        with async_mock.patch.object(
            ClassLoader, "load_class", async_mock.MagicMock()
        ) as load_class:
            load_class.side_effect = [mock_class, mock_class]
            result = self.registry.resolve_message_class("proto/1.1/aaa")
            assert result == mock_class

    def test_resolve_message_load_class_none(self):
        message_type_a = "proto/1.2/aaa"
        self.registry.register_message_types(
            {message_type_a: self.test_message_handler},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 2,
                "path": "v1_2",
            },
        )
        mock_class = async_mock.MagicMock()
        with async_mock.patch.object(
            ClassLoader, "load_class", async_mock.MagicMock()
        ) as load_class:
            load_class.side_effect = [mock_class, mock_class]
            result = self.registry.resolve_message_class("proto/1.2/bbb")
            assert result is None

    def test_repr(self):
        assert type(repr(self.registry)) is str
