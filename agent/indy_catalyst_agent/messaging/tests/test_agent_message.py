from asynctest import TestCase as AsyncTestCase
from marshmallow import fields

from ..agent_message import AgentMessage, AgentMessageSchema
from ..decorators.signature_decorator import SignatureDecorator
from ...wallet.basic import BasicWallet


class SignedAgentMessage(AgentMessage):
    """Signed agent message tests"""

    class Meta:
        """Meta data"""

        handler_class = None
        schema_class = "SignedAgentMessageSchema"
        message_type = "signed-agent-message"

    def __init__(self, value: str = None, **kwargs):
        super(SignedAgentMessage, self).__init__(**kwargs)
        self.value = value


class SignedAgentMessageSchema(AgentMessageSchema):
    """Utility schema"""

    class Meta:
        model_class = SignedAgentMessage
        signed_fields = ("value",)

    value = fields.Str(required=True)


class BasicAgentMessage(AgentMessage):
    """Simple agent message implementation"""

    class Meta:
        """Meta data"""

        schema_class = "AgentMessageSchema"
        message_type = "basic-message"


class TestAgentMessage(AsyncTestCase):
    """Tests agent message."""

    class BadImplementationClass(AgentMessage):
        """Test utility class."""

        pass

    def test_init(self):
        """Tests init class"""
        SignedAgentMessage()

        with self.assertRaises(TypeError) as context:
            self.BadImplementationClass()  # pylint: disable=E0110

        assert "Can't instantiate abstract" in str(context.exception)

    async def test_field_signature(self):
        wallet = BasicWallet()
        key_info = await wallet.create_signing_key()

        msg = SignedAgentMessage()
        msg.value = "Test value"
        await msg.sign_field("value", key_info.verkey, wallet)
        sig = msg.get_signature("value")
        assert isinstance(sig, SignatureDecorator)

        assert await sig.verify(wallet)
        assert await msg.verify_signed_field("value", wallet) == key_info.verkey
        assert await msg.verify_signatures(wallet)

        serial = msg.serialize()
        assert "value~sig" in serial and "value" not in serial

        loaded = SignedAgentMessage.deserialize(serial)
        assert isinstance(loaded, SignedAgentMessage)
        assert await loaded.verify_signed_field("value", wallet) == key_info.verkey

    async def test_assign_thread(self):
        msg = BasicAgentMessage()
        assert msg._thread_id == msg._id
        reply = BasicAgentMessage()
        reply.assign_thread_from(msg)
        assert reply._thread_id == msg._thread_id
        assert reply._thread_id != reply._id
