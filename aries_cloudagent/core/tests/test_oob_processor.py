import json

from asynctest import ANY
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...connections.models.conn_record import ConnRecord
from ...messaging.decorators.attach_decorator import AttachDecorator
from ...messaging.decorators.service_decorator import ServiceDecorator
from ...messaging.request_context import RequestContext
from ...protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ...protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ...protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ...storage.error import StorageNotFoundError
from ...transport.inbound.receipt import MessageReceipt
from ...transport.outbound.message import OutboundMessage
from ..in_memory.profile import InMemoryProfile
from ..oob_processor import OobMessageProcessor, OobMessageProcessorError


class TestOobProcessor(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.inbound_message_router = async_mock.CoroutineMock()
        self.oob_processor = OobMessageProcessor(
            inbound_message_router=self.inbound_message_router
        )

        self.oob_record = async_mock.MagicMock(
            connection_id="a-connection-id",
            attach_thread_id="the-thid",
            their_service={
                "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                "routingKeys": ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
                "serviceEndpoint": "http://their-service-endpoint.com",
            },
            emit_event=async_mock.CoroutineMock(),
            delete_record=async_mock.CoroutineMock(),
            save=async_mock.CoroutineMock(),
        )
        self.context = RequestContext.test_context()
        self.context.message = ConnectionInvitation()

    async def test_clean_finished_oob_record_no_multi_use_no_request_attach(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        mock_oob = async_mock.MagicMock(
            emit_event=async_mock.CoroutineMock(),
            delete_record=async_mock.CoroutineMock(),
            multi_use=False,
            invitation=async_mock.MagicMock(requests_attach=[]),
        )

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            await self.oob_processor.clean_finished_oob_record(
                self.profile, test_message
            )

            assert mock_oob.state == OobRecord.STATE_DONE
            mock_oob.emit_event.assert_called_once()
            mock_oob.delete_record.assert_called_once()

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"invi_msg_id": "the-pthid"}, {"role": OobRecord.ROLE_SENDER}
            )

    async def test_clean_finished_oob_record_multi_use(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        mock_oob = async_mock.MagicMock(
            emit_event=async_mock.CoroutineMock(),
            delete_record=async_mock.CoroutineMock(),
            multi_use=True,
            invitation=async_mock.MagicMock(requests_attach=[]),
        )

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            await self.oob_processor.clean_finished_oob_record(
                self.profile, test_message
            )

            mock_oob.emit_event.assert_not_called()
            mock_oob.delete_record.assert_not_called()

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"invi_msg_id": "the-pthid"}, {"role": OobRecord.ROLE_SENDER}
            )

    async def test_clean_finished_oob_record_x(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_oob:
            mock_retrieve_oob.side_effect = (StorageNotFoundError(),)

            await self.oob_processor.clean_finished_oob_record(
                self.profile, test_message
            )

    async def test_find_oob_target_for_outbound_message(self):
        mock_oob = async_mock.MagicMock(
            emit_event=async_mock.CoroutineMock(),
            delete_record=async_mock.CoroutineMock(),
            multi_use=True,
            invitation=async_mock.MagicMock(requests_attach=[]),
            invi_msg_id="the-pthid",
            our_recipient_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            their_service={
                "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                "serviceEndpoint": "http://their-service-endpoint.com",
                "routingKeys": ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            },
            our_service={
                "recipientKeys": ["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                "serviceEndpoint": "http://our-service-endpoint.com",
                "routingKeys": [],
            },
        )

        message = json.dumps({"~thread": {"thid": "the-thid"}})
        outbound = OutboundMessage(reply_thread_id="the-thid", payload=message)

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            target = await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )

            assert target
            assert target.endpoint == "http://their-service-endpoint.com"
            assert target.recipient_keys == [
                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
            ]
            assert target.routing_keys == [
                "6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"
            ]
            assert target.sender_key == "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

            payload = json.loads(outbound.payload)

            assert payload == {
                "~thread": {"thid": "the-thid", "pthid": "the-pthid"},
                "~service": {
                    "recipientKeys": ["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                    "serviceEndpoint": "http://our-service-endpoint.com",
                    "routingKeys": [],
                },
            }

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"attach_thread_id": "the-thid"}
            )

    async def test_find_oob_target_for_outbound_message_oob_not_found(self):
        message = json.dumps({})
        outbound = OutboundMessage(reply_thread_id="the-thid", payload=message)

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
        ) as mock_retrieve_oob:
            target = await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )

            assert not target
            mock_retrieve_oob.assert_called_once_with(
                ANY, {"attach_thread_id": "the-thid"}
            )

    async def test_find_oob_target_for_outbound_message_update_service_thread(self):
        mock_oob = async_mock.MagicMock(
            emit_event=async_mock.CoroutineMock(),
            delete_record=async_mock.CoroutineMock(),
            multi_use=True,
            invitation=async_mock.MagicMock(requests_attach=[]),
            invi_msg_id="the-pthid",
            our_recipient_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            their_service={
                "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                "serviceEndpoint": "http://their-service-endpoint.com",
                "routingKeys": ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            },
            our_service={
                "recipientKeys": ["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                "serviceEndpoint": "http://our-service-endpoint.com",
                "routingKeys": [],
            },
        )

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=mock_oob),
        ):
            message = json.dumps({})
            outbound = OutboundMessage(reply_thread_id="the-thid", payload=message)
            await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )
            payload = json.loads(outbound.payload)

            assert payload == {
                "~thread": {"pthid": "the-pthid"},
                "~service": {
                    "recipientKeys": ["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                    "serviceEndpoint": "http://our-service-endpoint.com",
                    "routingKeys": [],
                },
            }

            message = json.dumps(
                {
                    "~service": {"already": "present"},
                }
            )
            outbound = OutboundMessage(reply_thread_id="the-thid", payload=message)
            await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )
            payload = json.loads(outbound.payload)

            assert payload == {
                "~thread": {"pthid": "the-pthid"},
                "~service": {"already": "present"},
            }

    async def test_find_oob_record_for_inbound_message_parent_thread_id(self):
        # With pthid
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

        # With pthid, throws error
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

        # Without pthid
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt()

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_not_called()

    async def test_find_oob_record_for_inbound_message_connectionless_retrieve_oob(
        self,
    ):
        # With thread_id and recipient_verkey
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                recipient_verkey="our-recipient-key",
                sender_verkey=self.oob_record.their_service["recipientKeys"][0],
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(
                ANY,
                {
                    "attach_thread_id": "the-thid",
                    "our_recipient_key": "our-recipient-key",
                },
            )

        # With thread_id and recipient_verkey, throws error
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", recipient_verkey="our-recipient-key"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(
                ANY,
                {
                    "attach_thread_id": "the-thid",
                    "our_recipient_key": "our-recipient-key",
                },
            )

        # With connection
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=None),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", recipient_verkey="our-recipient-key"
            )
            self.context.connection_record = async_mock.MagicMock()

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_not_called()

        # Without thread_id and recipient_verkey
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=None),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt()

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_not_called()

    async def test_find_oob_record_for_inbound_message_sender_connection_id_no_match(
        self,
    ):
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_AWAIT_RESPONSE
            self.context.connection_record = async_mock.MagicMock(
                connection_id="a-connection-id"
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

        # Connection id is different
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_ACCEPTED
            self.context.connection_record = async_mock.MagicMock(
                connection_id="another-connection-id"
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

        # Connection id is not the same, state is not await response
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_ACCEPTED
            self.context.connection_record = async_mock.MagicMock(
                connection_id="another-connection-id"
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

        # Connection id is not the same, state is AWAIT_RESPONSE. oob has connection_id
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve, async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    delete_record=async_mock.CoroutineMock()
                )
            ),
        ) as mock_retrieve_conn:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_AWAIT_RESPONSE
            self.context.connection_record = async_mock.MagicMock(
                connection_id="another-connection-id"
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})
            mock_retrieve_conn.assert_called_once_with(ANY, "a-connection-id")
            mock_retrieve_conn.return_value.delete_record.assert_called_once()

            assert self.oob_record.connection_id == "another-connection-id"

    async def test_find_oob_record_for_inbound_message_attach_thread_id_set(self):
        # No attach thread_id
        self.oob_record.attach_thread_id = None

        self.oob_record.invitation.requests_attach = [
            AttachDecorator.data_json({"@id": "the-thid"})
        ]

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

            assert self.oob_record.attach_thread_id == "the-thid"

    async def test_find_oob_record_for_inbound_message_attach_thread_id_not_in_list(
        self,
    ):
        # No attach thread_id
        self.oob_record.attach_thread_id = None

        self.oob_record.invitation.requests_attach = [
            AttachDecorator.data_json({"@id": "another-thid"})
        ]

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

    async def test_find_oob_record_for_inbound_message_not_attach_thread_id_matching(
        self,
    ):
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

    async def test_find_oob_record_for_inbound_message_not_attach_thread_id_not_matching(
        self,
    ):
        self.oob_record.attach_thread_id = "another-thid"

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

    async def test_find_oob_record_for_inbound_message_recipient_verkey_not_in_their_service(
        self,
    ):
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                parent_thread_id="the-pthid",
                recipient_verkey="recipient-verkey",
                sender_verkey="a-sender-verkey",
            )

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

    async def test_find_oob_record_for_inbound_message_their_service_matching_with_message_receipt(
        self,
    ):
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                parent_thread_id="the-pthid",
                recipient_verkey="recipient-verkey",
                sender_verkey="9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC",
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

    async def test_find_oob_record_for_inbound_message_their_service_set_on_oob_record(
        self,
    ):
        self.context._message._service = ServiceDecorator(
            endpoint="http://example.com/endpoint",
            recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
            routing_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
        )

        self.oob_record.their_service = None

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                parent_thread_id="the-pthid",
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

            assert self.oob_record.their_service == {
                "serviceEndpoint": "http://example.com/endpoint",
                "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                "routingKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
            }

    async def test_find_oob_record_for_inbound_message_session_emit_delete(
        self,
    ):
        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                parent_thread_id="the-pthid",
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

            assert self.oob_record.state == OobRecord.STATE_DONE
            self.oob_record.emit_event.assert_called_once()
            self.oob_record.delete_record.assert_called_once()
            self.oob_record.save.assert_not_called()

    async def test_find_oob_record_for_inbound_message_session_connectionless_save(
        self,
    ):
        self.oob_record.connection_id = None

        with async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                parent_thread_id="the-pthid",
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve.assert_called_once_with(ANY, {"invi_msg_id": "the-pthid"})

            self.oob_record.emit_event.assert_not_called()
            self.oob_record.delete_record.assert_not_called()
            self.oob_record.save.assert_called_once()

    async def test_handle_message_connection(self):
        oob_record = async_mock.MagicMock(
            connection_id="the-conn-id",
            save=async_mock.CoroutineMock(),
            attach_thread_id=None,
            their_service=None,
        )

        await self.oob_processor.handle_message(
            self.profile,
            [
                {
                    "@type": "issue-credential/1.0/offer-credential",
                    "@id": "4a580490-a9d8-44f5-a3f6-14e0b8a219b0",
                }
            ],
            oob_record,
            their_service=ServiceDecorator(
                endpoint="http://their-service-endpoint.com",
                recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                routing_keys=["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            ),
        )

        assert oob_record.attach_thread_id == None
        assert oob_record.their_service == None

        oob_record.save.assert_not_called()

        self.inbound_message_router.assert_called_once_with(self.profile, ANY, False)

    async def test_handle_message_connectionless(self):
        oob_record = async_mock.MagicMock(
            save=async_mock.CoroutineMock(), connection_id=None
        )

        await self.oob_processor.handle_message(
            self.profile,
            [
                {
                    "@type": "issue-credential/1.0/offer-credential",
                    "@id": "4a580490-a9d8-44f5-a3f6-14e0b8a219b0",
                }
            ],
            oob_record,
            their_service=ServiceDecorator(
                endpoint="http://their-service-endpoint.com",
                recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                routing_keys=["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            ),
        )

        assert oob_record.attach_thread_id == "4a580490-a9d8-44f5-a3f6-14e0b8a219b0"
        assert oob_record.their_service == {
            "serviceEndpoint": "http://their-service-endpoint.com",
            "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
            "routingKeys": ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
        }

        oob_record.save.assert_called_once()

        self.inbound_message_router.assert_called_once_with(self.profile, ANY, False)

    async def test_handle_message_unsupported_message_type(self):
        with self.assertRaises(OobMessageProcessorError) as err:
            await self.oob_processor.handle_message(
                self.profile, [{"@type": "unsupported"}], async_mock.MagicMock()
            )
        assert (
            "None of the oob attached messages supported. Supported message types are issue-credential/1.0/offer-credential, issue-credential/2.0/offer-credential, present-proof/1.0/request-presentation, present-proof/2.0/request-presentation"
            in err.exception.message
        )

    async def test_get_thread_id(self):
        message_w_thread = {
            "@id": "the-message-id",
            "~thread": {"thid": "the-thread-id"},
        }
        message_wo_thread = {"@id": "the-message-id"}

        assert self.oob_processor.get_thread_id(message_w_thread) == "the-thread-id"
        assert self.oob_processor.get_thread_id(message_wo_thread) == "the-message-id"
