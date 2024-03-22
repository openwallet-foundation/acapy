from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ...config.injection_context import InjectionContext
from ...utils.classloader import ClassLoader, DeferLoad

from ..protocol_registry import ProtocolRegistry


class TestProtocolRegistry(IsolatedAsyncioTestCase):
    no_type_message = {"a": "b"}
    unknown_type_message = {"@type": 1}
    test_message_type = "doc/protocol/1.0/message"
    test_protocol = "doc/protocol/1.0"
    test_protocol_queries = ["*", "doc/protocol/1.0", "doc/proto*"]
    test_protocol_queries_fail = ["", "nomatch", "nomatch*"]
    test_message_cls = "fake_msg_cls"
    test_controller = "fake_controller"

    def setUp(self):
        self.registry = ProtocolRegistry()

    def test_protocols(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_cls}
        )
        self.registry.register_controllers(
            {self.test_message_type: self.test_controller}
        )

        assert list(self.registry.message_types) == [self.test_message_type]
        assert list(self.registry.protocols) == [self.test_protocol]

    def test_message_type_query(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_cls}
        )
        for q in self.test_protocol_queries:
            matches = self.registry.protocols_matching_query(q)
            assert tuple(matches) == (self.test_protocol,)
        for q in self.test_protocol_queries_fail:
            matches = self.registry.protocols_matching_query(q)
            assert matches == ()

    def test_registration_with_minor_version(self):
        MSG_PATH = "aries_cloudagent.protocols.introduction.v0_1.messages"
        test_typesets = {
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/1.0/fake-forward-invitation": f"{MSG_PATH}.forward_invitation.ForwardInvitation",
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/1.0/fake-invitation": f"{MSG_PATH}.invitation.Invitation",
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/1.0/fake-invitation-request": f"{MSG_PATH}.invitation_request.InvitationRequest",
            "https://didcom.org/introduction-service/1.0/fake-forward-invitation": f"{MSG_PATH}.forward_invitation.ForwardInvitation",
            "https://didcom.org/introduction-service/1.0/fake-invitation": f"{MSG_PATH}.invitation.Invitation",
            "https://didcom.org/introduction-service/1.0/fake-invitation-request": f"{MSG_PATH}.invitation_request.InvitationRequest",
        }
        test_version_def = {
            "current_minor_version": 0,
            "major_version": 1,
            "minimum_minor_version": 0,
            "path": "v0_1",
        }
        self.registry.register_message_types(test_typesets, test_version_def)
        assert (
            "https://didcom.org/introduction-service/1.0/fake-forward-invitation"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/introduction-service/1.0/fake-invitation"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/introduction-service/1.0/fake-invitation-request"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/1.0/fake-forward-invitation"
            in self.registry.message_types
        )

    def test_register_msg_types_for_multiple_minor_versions(self):
        MSG_PATH = "aries_cloudagent.protocols.out_of_band.v1_0.messages"
        test_typesets = {
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/invitation": f"{MSG_PATH}.invitation.Invitation",
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/handshake-reuse": f"{MSG_PATH}.reuse.HandshakeReuse",
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/handshake-reuse-accepted": f"{MSG_PATH}.reuse_accept.HandshakeReuseAccept",
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/problem_report": f"{MSG_PATH}.problem_report.OOBProblemReport",
            "https://didcom.org/out-of-band/1.1/invitation": f"{MSG_PATH}.invitation.Invitation",
            "https://didcom.org/out-of-band/1.1/handshake-reuse": f"{MSG_PATH}.reuse.HandshakeReuse",
            "https://didcom.org/out-of-band/1.1/handshake-reuse-accepted": f"{MSG_PATH}.reuse_accept.HandshakeReuseAccept",
            "https://didcom.org/out-of-band/1.1/problem_report": f"{MSG_PATH}.problem_report.OOBProblemReport",
        }
        test_version_def = {
            "current_minor_version": 1,
            "major_version": 1,
            "minimum_minor_version": 0,
            "path": "v0_1",
        }
        self.registry.register_message_types(test_typesets, test_version_def)
        assert (
            "https://didcom.org/out-of-band/1.0/invitation"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.0/handshake-reuse"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.0/handshake-reuse-accepted"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.0/problem_report"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.1/invitation"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.1/handshake-reuse"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.1/handshake-reuse-accepted"
            in self.registry.message_types
        )
        assert (
            "https://didcom.org/out-of-band/1.1/problem_report"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.0/invitation"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.0/handshake-reuse"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.0/handshake-reuse-accepted"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.0/problem_report"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/invitation"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/handshake-reuse"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/handshake-reuse-accepted"
            in self.registry.message_types
        )
        assert (
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/out-of-band/1.1/problem_report"
            in self.registry.message_types
        )

    async def test_disclosed(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_cls}
        )
        mocked = mock.MagicMock()
        mocked.return_value.check_access = mock.CoroutineMock()
        mocked.return_value.check_access.return_value = True
        mocked.return_value.determine_roles = mock.CoroutineMock()
        mocked.return_value.determine_roles.return_value = ["ROLE"]
        self.registry.register_controllers({self.test_protocol: mocked})
        protocols = [self.test_protocol]
        ctx = InjectionContext()
        published = await self.registry.prepare_disclosed(ctx, protocols)
        mocked.return_value.check_access.assert_called_once_with(ctx)
        mocked.return_value.determine_roles.assert_called_once_with(ctx)
        assert len(published) == 1
        assert published[0]["pid"] == self.test_protocol
        assert published[0]["roles"] == ["ROLE"]

    async def test_disclosed_str(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_cls}
        )
        self.registry.register_controllers({self.test_protocol: "mock-class-name"})
        protocols = [self.test_protocol]
        ctx = InjectionContext()

        class Mockery:
            def __init__(self, protocol):
                self.protocol = protocol

            async def check_access(self, context):
                return False

        with mock.patch.object(
            ClassLoader, "load_class", mock.MagicMock()
        ) as load_class:
            load_class.return_value = Mockery
            published = await self.registry.prepare_disclosed(ctx, protocols)
            assert not published

    def test_resolve_message_class_str(self):
        self.registry.register_message_types(
            {self.test_message_type: self.test_message_cls}
        )
        result = self.registry.resolve_message_class(self.test_message_type)
        assert isinstance(result, DeferLoad)
        assert result._cls_path == self.test_message_cls

    def test_resolve_message_class_no_major_version_support(self):
        result = self.registry.resolve_message_class("doc/proto/1.2/hello")
        assert result is None

    def test_resolve_message_load_class_str(self):
        message_type_a = "doc/proto/1.2/aaa"
        self.registry.register_message_types(
            {message_type_a: self.test_message_cls},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 2,
                "path": "v1_2",
            },
        )
        result = self.registry.resolve_message_class("doc/proto/1.1/aaa")
        assert isinstance(result, DeferLoad)
        assert result._cls_path == self.test_message_cls

    def test_resolve_message_load_class_none(self):
        message_type_a = "doc/proto/1.2/aaa"
        self.registry.register_message_types(
            {message_type_a: self.test_message_cls},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 2,
                "path": "v1_2",
            },
        )
        result = self.registry.resolve_message_class("doc/proto/1.2/bbb")
        assert result is None

    def test_repr(self):
        assert isinstance(repr(self.registry), str)
