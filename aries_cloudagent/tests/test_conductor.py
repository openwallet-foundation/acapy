from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ..conductor import Conductor
from ..messaging.connections.models.connection_target import ConnectionTarget
from ..messaging.message_delivery import MessageDelivery
from ..messaging.outbound_message import OutboundMessage
from ..messaging.protocol_registry import ProtocolRegistry
from ..transport.inbound.base import InboundTransportConfiguration


class TestConfig:
    good_inbound_transports = [
        InboundTransportConfiguration(module="http", host="host", port=80)
    ]
    good_outbound_transports = ["http"]
    bad_inbound_transports = [
        InboundTransportConfiguration(module="bad", host="host", port=80)
    ]
    bad_outbound_transports = ["bad"]
    test_settings = {}


class TestConductor(AsyncTestCase, TestConfig):
    async def test_startup(self):
        conductor = Conductor(
            self.good_inbound_transports,
            self.good_outbound_transports,
            ProtocolRegistry(),
            self.test_settings,
        )
        mock_inbound_mgr = async_mock.create_autospec(
            conductor.inbound_transport_manager
        )
        conductor.inbound_transport_manager = mock_inbound_mgr
        mock_outbound_mgr = async_mock.create_autospec(
            conductor.outbound_transport_manager
        )
        conductor.outbound_transport_manager = mock_outbound_mgr

        await conductor.start()

        mock_inbound_mgr.register.assert_called_once_with(
            self.good_inbound_transports[0],
            conductor.inbound_message_router,
            conductor.register_socket,
        )

        mock_inbound_mgr.start.assert_called_once_with()

        mock_outbound_mgr.register.assert_called_once_with(
            self.good_outbound_transports[0]
        )

        mock_outbound_mgr.start.assert_called_once_with()

    async def test_inbound_message_handler(self):
        conductor = Conductor(
            self.good_inbound_transports,
            self.good_outbound_transports,
            ProtocolRegistry(),
            self.test_settings,
        )
        mock_dispatcher = async_mock.create_autospec(conductor.dispatcher)
        conductor.dispatcher = mock_dispatcher
        mock_serializer = async_mock.create_autospec(conductor.message_serializer)
        conductor.message_serializer = mock_serializer

        delivery = MessageDelivery()
        parsed_msg = {}
        mock_serializer.parse_message.return_value = (parsed_msg, delivery)

        message_body = "{}"
        transport = "http"
        await conductor.inbound_message_router(message_body, transport)

        mock_serializer.parse_message.assert_called_once_with(
            conductor.context, message_body, transport
        )

        mock_dispatcher.dispatch.assert_called_once_with(
            parsed_msg, delivery, None, conductor.outbound_message_router
        )

    async def test_outbound_message_handler(self):
        conductor = Conductor(
            self.good_inbound_transports,
            self.good_outbound_transports,
            ProtocolRegistry(),
            self.test_settings,
        )
        mock_serializer = async_mock.create_autospec(conductor.message_serializer)
        conductor.message_serializer = mock_serializer
        mock_outbound_mgr = async_mock.create_autospec(
            conductor.outbound_transport_manager
        )
        conductor.outbound_transport_manager = mock_outbound_mgr

        payload = "{}"
        target = ConnectionTarget(
            endpoint="endpoint", recipient_keys=(), routing_keys=(), sender_key=""
        )
        message = OutboundMessage(payload=payload, target=target)

        await conductor.outbound_message_router(message)

        mock_serializer.encode_message.assert_called_once_with(
            conductor.context,
            payload,
            target.recipient_keys,
            target.routing_keys,
            target.sender_key,
        )

        mock_outbound_mgr.send_message.assert_called_once_with(message)
