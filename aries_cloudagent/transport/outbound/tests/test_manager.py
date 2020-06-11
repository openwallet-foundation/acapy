import asyncio
import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....config.injection_context import InjectionContext
from ....connections.models.connection_target import ConnectionTarget

from ..manager import (
    OutboundDeliveryError,
    OutboundTransportManager,
    OutboundTransportRegistrationError,
    QueuedOutboundMessage,
)
from ..message import OutboundMessage


class TestOutboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        mgr = OutboundTransportManager(InjectionContext())
        mgr.register("http")
        assert mgr.get_registered_transport_for_scheme("http")
        assert mgr.MAX_RETRY_COUNT == 4

        assert mgr.get_registered_transport_for_scheme("xmpp") is None

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("http")

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("no.such.module.path")

    def test_maximum_retry_count(self):
        context = InjectionContext()
        context.update_settings({"transport.max_outbound_retry": 5})
        mgr = OutboundTransportManager(context)
        mgr.register("http")
        assert mgr.MAX_RETRY_COUNT == 5

    async def test_setup(self):
        context = InjectionContext()
        context.update_settings({"transport.outbound_configs": ["http"]})
        mgr = OutboundTransportManager(context)
        with async_mock.patch.object(mgr, "register") as mock_register:
            await mgr.setup()
            mock_register.assert_called_once_with("http")

    async def test_send_message(self):
        context = InjectionContext()
        mgr = OutboundTransportManager(context)

        transport_cls = async_mock.Mock(spec=[])
        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register_class(transport_cls, "transport_cls")

        transport = async_mock.MagicMock()
        transport.handle_message = async_mock.CoroutineMock()
        transport.wire_format.encode_message = async_mock.CoroutineMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()
        transport.schemes = ["http"]

        transport_cls = async_mock.MagicMock()
        transport_cls.schemes = ["http"]
        transport_cls.return_value = transport
        mgr.register_class(transport_cls, "transport_cls")
        assert mgr.get_registered_transport_for_scheme("http") == "transport_cls"

        await mgr.start()
        await mgr.task_queue
        transport.start.assert_awaited_once_with()
        assert mgr.get_running_transport_for_scheme("http") == "transport_cls"

        message = OutboundMessage(payload="{}")
        assert "payload" in str(message)
        message.target = ConnectionTarget(
            endpoint="http://localhost",
            recipient_keys=[1, 2],
            routing_keys=[3],
            sender_key=4,
        )

        send_context = InjectionContext()
        mgr.enqueue_message(send_context, message)
        await mgr.flush()
        transport.wire_format.encode_message.assert_awaited_once_with(
            send_context,
            message.payload,
            message.target.recipient_keys,
            message.target.routing_keys,
            message.target.sender_key,
        )
        transport.handle_message.assert_awaited_once_with(
            send_context,
            transport.wire_format.encode_message.return_value,
            message.target.endpoint,
        )

        with self.assertRaises(OutboundDeliveryError):
            mgr.get_running_transport_for_endpoint("localhost")

        message.target = ConnectionTarget(
            endpoint="localhost", recipient_keys=[1, 2], routing_keys=[3], sender_key=4,
        )
        with self.assertRaises(OutboundDeliveryError) as context:
            mgr.enqueue_message(send_context, message)
        assert "No supported transport" in str(context.exception)

        await mgr.stop()

        assert mgr.get_running_transport_for_scheme("http") is None
        transport.stop.assert_awaited_once_with()

    async def test_stop_cancel(self):
        context = InjectionContext()
        context.update_settings({"transport.outbound_configs": ["http"]})
        mgr = OutboundTransportManager(context)
        mgr._process_task = async_mock.MagicMock(
            done=async_mock.MagicMock(return_value=False), cancel=async_mock.MagicMock()
        )
        mgr.running_transports = {}
        await mgr.stop()
        mgr._process_task.cancel.assert_called_once()

    async def test_enqueue_webhook(self):
        context = InjectionContext()
        mgr = OutboundTransportManager(context)
        test_topic = "test-topic"
        test_payload = {"test": "payload"}
        test_endpoint = "http://example"
        test_attempts = 2

        with self.assertRaises(OutboundDeliveryError):
            mgr.enqueue_webhook(
                test_topic, test_payload, test_endpoint, max_attempts=test_attempts
            )

        transport_cls = async_mock.MagicMock()
        transport_cls.schemes = ["http"]
        transport_cls.return_value = async_mock.MagicMock()
        transport_cls.return_value.schemes = ["http"]
        transport_cls.return_value.start = async_mock.CoroutineMock()
        tid = mgr.register_class(transport_cls, "transport_cls")
        await mgr.start_transport(tid)

        with async_mock.patch.object(mgr, "process_queued") as mock_process:
            mgr.enqueue_webhook(
                test_topic, test_payload, test_endpoint, max_attempts=test_attempts
            )
            mock_process.assert_called_once_with()
            assert len(mgr.outbound_new) == 1
            queued = mgr.outbound_new[0]
            assert queued.endpoint == f"{test_endpoint}/topic/{test_topic}/"
            assert json.loads(queued.payload) == test_payload
            assert queued.retries == test_attempts - 1
            assert queued.state == QueuedOutboundMessage.STATE_PENDING

    async def test_process_done_x(self):
        mock_task = async_mock.MagicMock(
            done=async_mock.MagicMock(return_value=True),
            exception=async_mock.MagicMock(return_value=KeyError("No such key")),
        )
        context = InjectionContext()
        mgr = OutboundTransportManager(context)

        with async_mock.patch.object(
            mgr, "_process_task", async_mock.MagicMock()
        ) as mock_mgr_process:
            mock_mgr_process.done = async_mock.MagicMock(return_value=True)
            mgr._process_done(mock_task)

    async def test_process_finished_x(self):
        mock_queued = async_mock.MagicMock(retries=1)
        mock_task = async_mock.MagicMock(exc_info=(KeyError, KeyError("nope"), None),)
        context = InjectionContext()
        mgr = OutboundTransportManager(context)

        with async_mock.patch.object(
            mgr, "process_queued", async_mock.MagicMock()
        ) as mock_mgr_process:
            mgr.finished_encode(mock_queued, mock_task)
            mgr.finished_deliver(mock_queued, mock_task)
            mgr.finished_deliver(mock_queued, mock_task)

    async def test_process_loop_x(self):
        mock_queued = async_mock.MagicMock(
            state=QueuedOutboundMessage.STATE_DONE, error=KeyError()
        )

        context = InjectionContext()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(context, mock_handle_not_delivered)
        mgr.outbound_buffer.append(mock_queued)

        await mgr._process_loop()
