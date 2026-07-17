import json
import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import ANY

import pytest

from ...connections.models.conn_record import ConnRecord
from ...core.event_bus import EventBus
from ...messaging.decorators.attach_decorator import AttachDecorator
from ...messaging.decorators.service_decorator import ServiceDecorator
from ...messaging.request_context import RequestContext
from ...messaging.responder import BaseResponder, MockResponder
from ...protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ...protocols.issue_credential.v2_0.manager import V20CredManager
from ...protocols.issue_credential.v2_0.messages.cred_offer import V20CredOffer
from ...protocols.issue_credential.v2_0.messages.cred_request import V20CredRequest
from ...protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from ...protocols.out_of_band.v1_0.manager import OutOfBandManager
from ...protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ...protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ...storage.error import StorageNotFoundError
from ...tests import mock
from ...transport.inbound.receipt import MessageReceipt
from ...transport.outbound.message import OutboundMessage
from ...utils.testing import create_test_profile
from ..oob_processor import OobMessageProcessor, OobMessageProcessorError


class TestOobProcessor(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.inbound_message_router = mock.MagicMock()
        self.oob_processor = OobMessageProcessor(
            inbound_message_router=self.inbound_message_router
        )

        self.oob_record = mock.MagicMock(
            connection_id="a-connection-id",
            attach_thread_id="the-thid",
            their_service=ServiceDecorator(
                recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                routing_keys=["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
                endpoint="http://their-service-endpoint.com",
            ),
            emit_event=mock.CoroutineMock(),
            delete_record=mock.CoroutineMock(),
            save=mock.CoroutineMock(),
        )
        self.context = RequestContext.test_context(self.profile)
        self.context.message = InvitationMessage()

    async def test_clean_finished_oob_record_no_multi_use_no_request_attach(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        mock_oob = mock.MagicMock(
            emit_event=mock.CoroutineMock(),
            delete_record=mock.CoroutineMock(),
            multi_use=False,
            invitation=mock.MagicMock(requests_attach=[]),
        )

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            await self.oob_processor.clean_finished_oob_record(self.profile, test_message)

            assert mock_oob.state == OobRecord.STATE_DONE
            mock_oob.emit_event.assert_called_once()
            mock_oob.delete_record.assert_called_once()

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"invi_msg_id": "the-pthid"}, {"role": OobRecord.ROLE_SENDER}
            )

    async def test_clean_finished_oob_record_multi_use(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        mock_oob = mock.MagicMock(
            emit_event=mock.CoroutineMock(),
            delete_record=mock.CoroutineMock(),
            multi_use=True,
            invitation=mock.MagicMock(requests_attach=[]),
        )

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            await self.oob_processor.clean_finished_oob_record(self.profile, test_message)

            mock_oob.emit_event.assert_called_once()
            mock_oob.delete_record.assert_not_called()

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"invi_msg_id": "the-pthid"}, {"role": OobRecord.ROLE_SENDER}
            )

    async def test_clean_finished_oob_record_x(self):
        test_message = InvitationMessage()
        test_message.assign_thread_id("the-thid", "the-pthid")

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(),
        ) as mock_retrieve_oob:
            mock_retrieve_oob.side_effect = (StorageNotFoundError(),)

            await self.oob_processor.clean_finished_oob_record(self.profile, test_message)

    async def test_find_oob_target_for_outbound_message(self):
        mock_oob = mock.MagicMock(
            emit_event=mock.CoroutineMock(),
            delete_record=mock.CoroutineMock(),
            multi_use=True,
            invitation=mock.MagicMock(requests_attach=[]),
            invi_msg_id="the-pthid",
            our_recipient_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            their_service=ServiceDecorator(
                recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                endpoint="http://their-service-endpoint.com",
                routing_keys=["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            ),
            our_service=ServiceDecorator(
                recipient_keys=["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                endpoint="http://our-service-endpoint.com",
                routing_keys=[],
            ),
        )

        message = json.dumps({"~thread": {"thid": "the-thid"}})
        outbound = OutboundMessage(reply_thread_id="the-thid", payload=message)

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=mock_oob),
        ) as mock_retrieve_oob:
            target = await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )

            assert target
            assert target.endpoint == "http://their-service-endpoint.com"
            assert target.recipient_keys == [
                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
            ]
            assert target.routing_keys == ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"]
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

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
        ) as mock_retrieve_oob:
            target = await self.oob_processor.find_oob_target_for_outbound_message(
                self.profile, outbound
            )

            assert not target
            mock_retrieve_oob.assert_called_once_with(
                ANY, {"attach_thread_id": "the-thid"}
            )

    async def test_find_oob_target_for_outbound_message_update_service_thread(self):
        mock_oob = mock.MagicMock(
            emit_event=mock.CoroutineMock(),
            delete_record=mock.CoroutineMock(),
            multi_use=True,
            invitation=mock.MagicMock(requests_attach=[]),
            invi_msg_id="the-pthid",
            our_recipient_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            their_service=ServiceDecorator(
                recipient_keys=["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
                endpoint="http://their-service-endpoint.com",
                routing_keys=["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
            ),
            our_service=ServiceDecorator(
                recipient_keys=["3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"],
                endpoint="http://our-service-endpoint.com",
                routing_keys=[],
            ),
        )

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=mock_oob),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid",
                recipient_verkey="our-recipient-key",
                sender_verkey=self.oob_record.their_service.recipient_keys[0],
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(side_effect=(StorageNotFoundError(),)),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=None),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", recipient_verkey="our-recipient-key"
            )
            self.context.connection_record = mock.MagicMock()

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_not_called()

        # Without thread_id and recipient_verkey
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=None),
        ) as mock_retrieve:
            self.context.message_receipt = MessageReceipt()

            assert not await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_not_called()

    async def test_find_oob_record_for_inbound_message_sender_connection_id_no_match(
        self,
    ):
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_AWAIT_RESPONSE
            self.context.connection_record = mock.MagicMock(
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_ACCEPTED
            self.context.connection_record = mock.MagicMock(
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
        ) as mock_retrieve:
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_ACCEPTED
            self.context.connection_record = mock.MagicMock(
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
        with (
            mock.patch.object(
                OobRecord,
                "retrieve_by_tag_filter",
                mock.CoroutineMock(return_value=self.oob_record),
            ) as mock_retrieve,
            mock.patch.object(
                ConnRecord,
                "retrieve_by_id",
                mock.CoroutineMock(
                    return_value=mock.MagicMock(delete_record=mock.CoroutineMock())
                ),
            ) as mock_retrieve_conn,
        ):
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_AWAIT_RESPONSE
            self.context.connection_record = mock.MagicMock(
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

    async def test_find_oob_record_for_inbound_message_self_connection_not_deleted(
        self,
    ):
        """Regression test for issue #3300 bug #2.

        In a self-connection (one wallet playing both the inviter and invitee
        roles for one OOB invitation with both handshake_protocols and an
        attachment), the "old" connection associated with the OobRecord is the
        *other role's own* ConnRecord -- reciprocal DIDs with the inbound
        message's connection -- not a stale/superseded connection from a real
        connection-reuse race. It must not be deleted, or the still-pending
        DIDXComplete for that connection later fails with DIDXManagerError:
        "No corresponding connection request found".
        """
        old_conn_record = mock.MagicMock(
            my_did="old-my-did",
            their_did="new-my-did",
            delete_record=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(
                OobRecord,
                "retrieve_by_tag_filter",
                mock.CoroutineMock(return_value=self.oob_record),
            ) as mock_retrieve,
            mock.patch.object(
                ConnRecord,
                "retrieve_by_id",
                mock.CoroutineMock(return_value=old_conn_record),
            ) as mock_retrieve_conn,
        ):
            self.oob_record.role = OobRecord.ROLE_SENDER
            self.oob_record.state = OobRecord.STATE_AWAIT_RESPONSE
            self.context.connection_record = mock.MagicMock(
                connection_id="another-connection-id",
                my_did="new-my-did",
                their_did="old-my-did",
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            assert await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )
            mock_retrieve.assert_called_once()
            mock_retrieve_conn.assert_called_once_with(ANY, "a-connection-id")
            old_conn_record.delete_record.assert_not_called()

            assert self.oob_record.connection_id == "another-connection-id"

    async def test_find_oob_record_inbound_offer_does_not_consume_sender_record(
        self,
    ):
        """Regression test for issue #3300 (self-issuance, bug #4).

        An inbound credential offer flows sender -> receiver, so it can never
        belong to our own role=sender OobRecord. In a self-connection the
        receiver-role record may already be gone (deleted after the handshake),
        leaving only the sender record to match the offer's pthid: the offer
        must NOT consume (update/delete) that sender record, or the later
        request-credential reply finds no OobRecord at all.
        """
        self.oob_record.role = OobRecord.ROLE_SENDER

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
        ):
            self.context.message = V20CredOffer(formats=[], offers_attach=[])
            self.context.connection_record = mock.MagicMock(
                connection_id="receiver-role-connection-id"
            )
            self.context.message_receipt = MessageReceipt(
                thread_id="the-thid", parent_thread_id="the-pthid"
            )

            result = await self.oob_processor.find_oob_record_for_inbound_message(
                self.context
            )

            assert result is None
            self.oob_record.delete_record.assert_not_called()
            self.oob_record.save.assert_not_called()

    async def test_find_oob_record_for_inbound_message_attach_thread_id_set(self):
        # No attach thread_id
        self.oob_record.attach_thread_id = None

        self.oob_record.invitation.requests_attach = [
            AttachDecorator.data_json({"@id": "the-thid"})
        ]

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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

        with mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            mock.CoroutineMock(return_value=self.oob_record),
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
        oob_record = mock.MagicMock(
            connection_id="the-conn-id",
            save=mock.CoroutineMock(),
            attach_thread_id=None,
            their_service=None,
        )

        await self.oob_processor.handle_message(
            self.profile,
            [
                {
                    "@type": "issue-credential/2.0/offer-credential",
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

        assert oob_record.attach_thread_id is None
        assert oob_record.their_service is None

        oob_record.save.assert_not_called()

        self.inbound_message_router.assert_called_once_with(self.profile, ANY, False)

    async def test_handle_message_connectionless(self):
        oob_record = mock.MagicMock(save=mock.CoroutineMock(), connection_id=None)

        await self.oob_processor.handle_message(
            self.profile,
            [
                {
                    "@type": "issue-credential/2.0/offer-credential",
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
        assert oob_record.their_service.serialize() == {
            "serviceEndpoint": "http://their-service-endpoint.com",
            "recipientKeys": ["9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"],
            "routingKeys": ["6QSduYdf8Bi6t8PfNm5vNomGWDtXhmMmTRzaciudBXYJ"],
        }

        oob_record.save.assert_called_once()

        self.inbound_message_router.assert_called_once_with(self.profile, ANY, False)

    async def test_handle_message_unsupported_message_type(self):
        with self.assertRaises(OobMessageProcessorError) as err:
            await self.oob_processor.handle_message(
                self.profile, [{"@type": "unsupported"}], mock.MagicMock()
            )
        assert (
            "None of the oob attached messages supported. Supported message types are issue-credential/2.0/offer-credential, present-proof/2.0/request-presentation, issue-credential/1.0/offer-credential, present-proof/1.0/request-presentation"
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


# --- Regression tests for self-issuance via OOB attachment without a prior
# --- connection (aries-rfcs/acapy issue #3300, bug #1): creating an OOB
# --- invitation with an attached credential-offer and then receiving that
# --- same invitation back into the same wallet used to raise
# --- StorageDuplicateError from find_oob_record_for_inbound_message, because
# --- the invi_msg_id is shared by two OobRecords (role=sender, role=receiver).


def _wallet_settings(wallet_type: str) -> dict:
    settings = {
        "wallet.type": wallet_type,
        "auto_provision": True,
        "default_endpoint": "http://example.com/endpoint",
        "default_label": "self-issuer",
    }
    if wallet_type == "kanon-anoncreds":
        postgres_url = os.getenv("POSTGRES_URL")
        settings.update(
            {
                "wallet.storage_type": "postgres",
                "wallet.storage_config": {"url": postgres_url},
                "wallet.storage_creds": {
                    "account": "postgres",
                    "password": "postgres",
                },
                "dbstore_storage_type": "postgres",
                "dbstore_storage_config": {"url": postgres_url},
                "dbstore_storage_creds": {
                    "account": "postgres",
                    "password": "postgres",
                },
                "dbstore_schema_config": "normalize",
            }
        )
    return settings


WALLET_TYPES = [
    "askar",
    "askar-anoncreds",
    pytest.param(
        "kanon-anoncreds",
        marks=pytest.mark.skipif(
            not os.getenv("POSTGRES_URL"),
            reason="Kanon PostgreSQL integration tests disabled: set POSTGRES_URL "
            "to enable",
        ),
    ),
]


def _bind_oob_manager_deps(profile):
    """Bind the dependencies OutOfBandManager needs, for direct manager tests."""
    route_manager = mock.MagicMock(RouteManager, autospec=True)
    route_manager.routing_info = mock.CoroutineMock(return_value=([], None))
    route_manager.mediation_record_if_id = mock.CoroutineMock(return_value=None)
    route_manager.route_invitation = mock.CoroutineMock(return_value=None)
    route_manager.route_verkey = mock.CoroutineMock(return_value=None)
    profile.context.injector.bind_instance(RouteManager, route_manager)
    profile.context.injector.bind_instance(BaseResponder, MockResponder())
    profile.context.injector.bind_instance(EventBus, EventBus())
    return route_manager


@pytest.mark.parametrize("wallet_type", WALLET_TYPES)
async def test_self_issuance_oob_attachment_without_connection(wallet_type):
    """An OOB invitation with an attached cred-offer, received by its own
    creator, must not raise StorageDuplicateError when the attached message
    is routed back through find_oob_record_for_inbound_message.
    """
    profile = await create_test_profile(settings=_wallet_settings(wallet_type))
    oob_processor = OobMessageProcessor(inbound_message_router=mock.MagicMock())
    profile.context.injector.bind_instance(OobMessageProcessor, oob_processor)
    _bind_oob_manager_deps(profile)

    oob_mgr = OutOfBandManager(profile)

    offer = V20CredOffer(formats=[], offers_attach=[])
    cred_ex = V20CredExRecord(
        cred_ex_id=None,
        state=V20CredExRecord.STATE_OFFER_SENT,
        cred_offer=offer.serialize(),
    )
    async with profile.session() as session:
        await cred_ex.save(session)

    invitation_record = await oob_mgr.create_invitation(
        my_label="self-issuer",
        attachments=[{"id": cred_ex.cred_ex_id, "type": "credential-offer"}],
    )

    # Two OobRecords with the same invi_msg_id now exist: role=sender (from
    # create_invitation) and role=receiver (from receive_invitation below).
    oob_record = await oob_mgr.receive_invitation(invitation_record.invitation)
    assert oob_record.role == OobRecord.ROLE_RECEIVER

    async with profile.session() as session:
        oob_records = await OobRecord.query(
            session, tag_filter={"invi_msg_id": invitation_record.invi_msg_id}
        )
    assert len(oob_records) == 2
    assert {r.role for r in oob_records} == {
        OobRecord.ROLE_SENDER,
        OobRecord.ROLE_RECEIVER,
    }

    # Simulate the attached credential-offer message being routed back
    # through the inbound pipeline: this is exactly where
    # find_oob_record_for_inbound_message previously raised
    # StorageDuplicateError.
    context = RequestContext.test_context(profile)
    context.message = offer
    context.message_receipt = MessageReceipt(
        thread_id=offer._id,
        parent_thread_id=invitation_record.invi_msg_id,
    )

    result = await oob_processor.find_oob_record_for_inbound_message(context)

    assert result is not None
    assert result.role == OobRecord.ROLE_RECEIVER


@pytest.mark.parametrize("wallet_type", WALLET_TYPES)
async def test_self_issuance_connectionless_full_round_trip(wallet_type):
    """Full connectionless self-issuance (bug #3, downstream of issue #3300).

    Create an OOB invitation with an attached credential offer (no
    handshake_protocols), receive it back into the same wallet, then drive the
    holder side to send a credential request back into the same wallet. The
    credential-request lookup used to come back empty (find_oob_record_for_inbound
    _message returning None -- not even hitting the "Multiple OOB records" branch
    that bug #1 fixed) because the duplicate-record disambiguation defaulted every
    non-didexchange message type to role=receiver, when a *reply* message flowing
    holder -> issuer (like issue-credential's request-credential) actually belongs
    to the role=sender record.
    """
    profile = await create_test_profile(settings=_wallet_settings(wallet_type))
    inbound_messages = []

    def inbound_router(profile_, inbound_message, can_respond):
        inbound_messages.append(inbound_message)

    oob_processor = OobMessageProcessor(inbound_message_router=inbound_router)
    profile.context.injector.bind_instance(OobMessageProcessor, oob_processor)
    _bind_oob_manager_deps(profile)

    oob_mgr = OutOfBandManager(profile)

    offer = V20CredOffer(formats=[], offers_attach=[])
    cred_ex = V20CredExRecord(
        cred_ex_id=None,
        state=V20CredExRecord.STATE_OFFER_SENT,
        cred_offer=offer.serialize(),
    )
    async with profile.session() as session:
        await cred_ex.save(session)

    invitation_record = await oob_mgr.create_invitation(
        my_label="self-issuer",
        attachments=[{"id": cred_ex.cred_ex_id, "type": "credential-offer"}],
    )

    # Receiving our own invitation processes the attached offer and delivers it
    # to the inbound router, exactly like a real inbound transport would.
    await oob_mgr.receive_invitation(invitation_record.invitation)
    assert len(inbound_messages) == 1
    offer_inbound = inbound_messages[0]

    offer_context = RequestContext.test_context(profile)
    offer_context.message = offer
    offer_context.message_receipt = offer_inbound.receipt

    oob_record_for_offer = await oob_processor.find_oob_record_for_inbound_message(
        offer_context
    )
    assert oob_record_for_offer is not None
    assert oob_record_for_offer.role == OobRecord.ROLE_RECEIVER

    # Holder side: receive the offer and build a credential request reply.
    cred_manager = V20CredManager(profile)
    holder_cred_ex = await cred_manager.receive_offer(offer, None)

    cred_request_message = V20CredRequest(formats=[], requests_attach=[])
    cred_request_message.assign_thread_from(offer)
    holder_cred_ex.thread_id = cred_request_message._thread_id
    holder_cred_ex.state = V20CredExRecord.STATE_REQUEST_SENT
    holder_cred_ex.cred_request = cred_request_message
    async with profile.session() as session:
        await holder_cred_ex.save(session, reason="test credential request")

    # Simulate sending the request: this is exactly what the outbound transport
    # manager does before delivering the message (attaches ~service/~thread.pthid
    # and resolves the delivery target/recipient key from the OOB record).
    outbound = OutboundMessage(
        reply_thread_id=cred_request_message._thread_id,
        payload=cred_request_message.serialize(as_string=True),
    )
    target = await oob_processor.find_oob_target_for_outbound_message(
        profile, outbound
    )
    assert target is not None

    # Simulate that same request being delivered back inbound, as it is in the
    # real self-issuance-without-handshake deployment scenario: recipient_verkey
    # is the key the message was actually decrypted with (the issuer's/sender's
    # connectionless key -- what the outbound target resolved to), and
    # sender_verkey is the holder's own connectionless key (carried in the
    # message's own ~service block, used by the recipient to reply).
    payload = json.loads(outbound.payload)
    request_context = RequestContext.test_context(profile)
    request_context.message = V20CredRequest.deserialize(payload)
    request_context.message_receipt = MessageReceipt(
        thread_id=payload["~thread"]["thid"],
        parent_thread_id=payload["~thread"].get("pthid"),
        recipient_verkey=target.recipient_keys[0],
        sender_verkey=payload["~service"]["recipientKeys"][0],
    )

    oob_record_for_request = await oob_processor.find_oob_record_for_inbound_message(
        request_context
    )

    # This is the fix under test: previously this came back None, and
    # V20CredRequestHandler.handle raised "No connection or associated
    # connectionless exchange found for credential request".
    assert oob_record_for_request is not None
    assert oob_record_for_request.role == OobRecord.ROLE_SENDER
    assert oob_record_for_request.invi_msg_id == invitation_record.invi_msg_id
