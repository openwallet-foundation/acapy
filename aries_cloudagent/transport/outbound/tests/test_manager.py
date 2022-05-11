import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....core.in_memory import InMemoryProfile
from ....connections.models.connection_target import ConnectionTarget
from ....core.in_memory import InMemoryProfile
from ...wire_format import BaseWireFormat

from .. import manager as test_module
from ..manager import (
    OutboundDeliveryError,
    OutboundTransportManager,
    OutboundTransportRegistrationError,
    QueuedOutboundMessage,
)
from ..message import OutboundMessage


class TestOutboundTransportManager(AsyncTestCase):
    def test_register_path(self):
        mgr = OutboundTransportManager(InMemoryProfile.test_profile())
        mgr.register("http")
        assert mgr.get_registered_transport_for_scheme("http")
        assert mgr.MAX_RETRY_COUNT == 4

        assert mgr.get_registered_transport_for_scheme("xmpp") is None

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("http")

        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register("no.such.module.path")

    def test_maximum_retry_count(self):
        profile = InMemoryProfile.test_profile({"transport.max_outbound_retry": 5})
        mgr = OutboundTransportManager(profile)
        mgr.register("http")
        assert mgr.MAX_RETRY_COUNT == 5

    async def test_setup(self):
        profile = InMemoryProfile.test_profile({"transport.outbound_configs": ["http"]})
        mgr = OutboundTransportManager(profile)
        with async_mock.patch.object(mgr, "register") as mock_register:
            await mgr.setup()
            mock_register.assert_called_once_with("http")

    async def test_send_message(self):
        profile = InMemoryProfile.test_profile()
        mgr = OutboundTransportManager(profile)

        transport_cls = async_mock.Mock(spec=[])
        with self.assertRaises(OutboundTransportRegistrationError):
            mgr.register_class(transport_cls, "transport_cls")

        transport = async_mock.MagicMock()
        transport.handle_message = async_mock.CoroutineMock()
        transport.wire_format.encode_message = async_mock.CoroutineMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()
        transport.schemes = ["http"]
        transport.is_external = False

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

        send_session = InMemoryProfile.test_session()
        send_profile = send_session.profile
        setattr(
            send_profile, "session", async_mock.MagicMock(return_value=send_session)
        )
        await mgr.enqueue_message(send_profile, message)
        await mgr.flush()

        transport.wire_format.encode_message.assert_awaited_once_with(
            send_session,
            message.payload,
            message.target.recipient_keys,
            message.target.routing_keys,
            message.target.sender_key,
        )
        transport.handle_message.assert_awaited_once_with(
            send_profile,
            transport.wire_format.encode_message.return_value,
            message.target.endpoint,
            None,
            None,
        )

        with self.assertRaises(OutboundDeliveryError):
            mgr.get_running_transport_for_endpoint("localhost")

        message.target = ConnectionTarget(
            endpoint="localhost",
            recipient_keys=[1, 2],
            routing_keys=[3],
            sender_key=4,
        )
        with self.assertRaises(OutboundDeliveryError) as context:
            await mgr.enqueue_message(send_profile, message)
        assert "No supported transport" in str(context.exception)

        await mgr.stop()

        assert mgr.get_running_transport_for_scheme("http") is None
        transport.stop.assert_awaited_once_with()

    async def test_stop_cancel(self):
        profile = InMemoryProfile.test_profile({"transport.outbound_configs": ["http"]})
        mgr = OutboundTransportManager(profile)
        mgr._process_task = async_mock.MagicMock(
            done=async_mock.MagicMock(return_value=False), cancel=async_mock.MagicMock()
        )
        mgr.running_transports = {}
        await mgr.stop()
        mgr._process_task.cancel.assert_called_once()

    async def test_enqueue_webhook(self):
        profile = InMemoryProfile.test_profile()
        mgr = OutboundTransportManager(profile)
        test_topic = "test-topic"
        test_payload = {"test": "payload"}
        test_endpoint_host = "http://example"
        test_endpoint = f"{test_endpoint_host}#abc123"
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
            assert queued.endpoint == f"{test_endpoint_host}/topic/{test_topic}/"
            assert json.loads(queued.payload) == test_payload
            assert queued.retries == test_attempts - 1
            assert queued.state == QueuedOutboundMessage.STATE_PENDING

    async def test_process_done_x(self):
        mock_task = async_mock.MagicMock(
            done=async_mock.MagicMock(return_value=True),
            exception=async_mock.MagicMock(return_value=KeyError("No such key")),
        )
        profile = InMemoryProfile.test_profile()
        mgr = OutboundTransportManager(profile)

        with async_mock.patch.object(
            mgr, "_process_task", async_mock.MagicMock()
        ) as mock_mgr_process:
            mock_mgr_process.done = async_mock.MagicMock(return_value=True)
            mgr._process_done(mock_task)

    async def test_process_finished_x(self):
        mock_queued = async_mock.MagicMock(retries=1)
        mock_task = async_mock.MagicMock(
            exc_info=(KeyError, KeyError("nope"), None),
        )
        profile = InMemoryProfile.test_profile()
        mgr = OutboundTransportManager(profile)

        with async_mock.patch.object(
            mgr, "process_queued", async_mock.MagicMock()
        ) as mock_mgr_process:
            mgr.finished_encode(mock_queued, mock_task)
            mgr.finished_deliver(mock_queued, mock_task)
            mgr.finished_deliver(mock_queued, mock_task)

    async def test_process_loop_retry_now(self):
        mock_queued = async_mock.MagicMock(
            state=QueuedOutboundMessage.STATE_RETRY,
            retry_at=test_module.get_timer() - 1,
        )

        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)
        mgr.outbound_buffer.append(mock_queued)

        with async_mock.patch.object(
            test_module, "trace_event", async_mock.MagicMock()
        ) as mock_trace:
            mock_trace.side_effect = KeyError()
            with self.assertRaises(KeyError):  # cover retry logic and bail
                await mgr._process_loop()
            assert mock_queued.retry_at is None

    async def test_process_loop_retry_later(self):
        mock_queued = async_mock.MagicMock(
            state=QueuedOutboundMessage.STATE_RETRY,
            retry_at=test_module.get_timer() + 3600,
        )

        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)
        mgr.outbound_buffer.append(mock_queued)

        with async_mock.patch.object(
            test_module.asyncio, "sleep", async_mock.CoroutineMock()
        ) as mock_sleep_x:
            mock_sleep_x.side_effect = KeyError()
            with self.assertRaises(KeyError):  # cover retry logic and bail
                await mgr._process_loop()
            assert mock_queued.retry_at is not None

    async def test_process_loop_new(self):
        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)

        mgr.outbound_new = [
            async_mock.MagicMock(
                state=test_module.QueuedOutboundMessage.STATE_NEW,
                message=async_mock.MagicMock(enc_payload=b"encr"),
            )
        ]
        with async_mock.patch.object(
            mgr, "deliver_queued_message", async_mock.MagicMock()
        ) as mock_deliver, async_mock.patch.object(
            mgr.outbound_event, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module, "trace_event", async_mock.MagicMock()
        ) as mock_trace:
            mock_wait.side_effect = KeyError()  # cover state=NEW logic and bail

            with self.assertRaises(KeyError):
                await mgr._process_loop()

    async def test_process_loop_new_deliver(self):
        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)

        mgr.outbound_new = [
            async_mock.MagicMock(
                state=test_module.QueuedOutboundMessage.STATE_DELIVER,
                message=async_mock.MagicMock(enc_payload=b"encr"),
            )
        ]
        with async_mock.patch.object(
            mgr, "deliver_queued_message", async_mock.MagicMock()
        ) as mock_deliver, async_mock.patch.object(
            mgr.outbound_event, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module, "trace_event", async_mock.MagicMock()
        ) as mock_trace:
            mock_wait.side_effect = KeyError()  # cover state=DELIVER logic and bail

            with self.assertRaises(KeyError):
                await mgr._process_loop()

    async def test_process_loop_x(self):
        mock_queued = async_mock.MagicMock(
            state=QueuedOutboundMessage.STATE_DONE,
            error=KeyError(),
            endpoint="http://1.2.3.4:8081",
            payload="Hello world",
        )

        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)
        mgr.outbound_buffer.append(mock_queued)

        await mgr._process_loop()

    async def test_finished_deliver_x_log_debug(self):
        mock_queued = async_mock.MagicMock(
            state=QueuedOutboundMessage.STATE_DONE, retries=1
        )
        mock_completed_x = async_mock.MagicMock(exc_info=KeyError("an error occurred"))

        profile = InMemoryProfile.test_profile()
        mock_handle_not_delivered = async_mock.MagicMock()
        mgr = OutboundTransportManager(profile, mock_handle_not_delivered)
        mgr.outbound_buffer.append(mock_queued)
        with async_mock.patch.object(
            test_module.LOGGER, "exception", async_mock.MagicMock()
        ) as mock_logger_exception, async_mock.patch.object(
            test_module.LOGGER, "error", async_mock.MagicMock()
        ) as mock_logger_error, async_mock.patch.object(
            test_module.LOGGER, "isEnabledFor", async_mock.MagicMock()
        ) as mock_logger_enabled, async_mock.patch.object(
            mgr, "process_queued", async_mock.MagicMock()
        ) as mock_process:
            mock_logger_enabled.return_value = True  # cover debug logging
            mgr.finished_deliver(mock_queued, mock_completed_x)

    async def test_should_encode_outbound_message(self):
        base_wire_format = BaseWireFormat()
        encoded_msg = "encoded_message"
        base_wire_format.encode_message = async_mock.CoroutineMock(
            return_value=encoded_msg
        )
        profile = InMemoryProfile.test_profile(bind={BaseWireFormat: base_wire_format})
        profile.session = async_mock.CoroutineMock(return_value=async_mock.MagicMock())
        outbound = async_mock.MagicMock(payload="payload", enc_payload=None)
        target = async_mock.MagicMock()

        mgr = OutboundTransportManager(profile)
        result = await mgr.encode_outbound_message(profile, outbound, target)

        assert result.payload == encoded_msg
        base_wire_format.encode_message.assert_called_once_with(
            await profile.session(),
            outbound.payload,
            target.recipient_keys,
            target.routing_keys,
            target.sender_key,
        )

    async def test_should_not_encode_already_packed_message(self):
        profile = InMemoryProfile.test_session().profile
        enc_payload = "enc_payload"
        outbound = async_mock.MagicMock(enc_payload=enc_payload)
        target = async_mock.MagicMock()

        mgr = OutboundTransportManager(profile)
        result = await mgr.encode_outbound_message(profile, outbound, target)

        assert result.payload == enc_payload
