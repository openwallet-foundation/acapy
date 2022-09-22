from asynctest import TestCase as AsyncTestCase

from .....connections.models.conn_record import ConnRecord
from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....did.did_key import DIDKey
from .....wallet.key_type import ED25519

from ....didcomm_prefix import DIDCommPrefix
from ....out_of_band.v1_0.message_types import INVITATION as OOB_INVITATION
from ....out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitationMessage,
)
from ....out_of_band.v1_0.messages.service import Service as OOBService

from .. import base_service, demo_service

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"


class TestIntroductionService(AsyncTestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = RequestContext(self.profile)
        self.oob_invi_msg = OOBInvitationMessage(
            label=TEST_LABEL,
            handshake_protocols=[DIDCommPrefix.qualify_current(OOB_INVITATION)],
            services=[
                OOBService(
                    _id="#inline",
                    _type="did-communication",
                    did=TEST_DID,
                    recipient_keys=[
                        DIDKey.from_public_key_b58(TEST_VERKEY, ED25519).did
                    ],
                    routing_keys=[
                        DIDKey.from_public_key_b58(TEST_ROUTE_VERKEY, ED25519).did
                    ],
                    service_endpoint=TEST_ENDPOINT,
                )
            ],
        )

    async def test_service_start_introduction_no_init_conn_rec(self):
        service = await demo_service.DemoIntroductionService.service_handler()()
        session = await self.profile.session()

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id="init-id",
                target_connection_id=None,
                message="Hello",
                session=session,
                outbound_handler=None,
            )

    async def test_service_start_introduction_init_conn_rec_not_completed(self):
        service = await demo_service.DemoIntroductionService.service_handler()()
        session = await self.profile.session()

        conn_rec_init = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.ABANDONED.rfc23,
        )
        await conn_rec_init.save(session)
        assert conn_rec_init._id

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id=None,
                message="Hello",
                session=session,
                outbound_handler=None,
            )

    async def test_service_start_introduction_no_target_conn_rec(self):
        service = await demo_service.DemoIntroductionService.service_handler()()
        session = await self.profile.session()

        conn_rec_init = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        await conn_rec_init.save(session)
        assert conn_rec_init._id

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id="target-id",
                message="Hello",
                session=session,
                outbound_handler=None,
            )

    async def test_service_start_introduction_target_conn_rec_not_completed(self):
        service = await demo_service.DemoIntroductionService.service_handler()()
        session = await self.profile.session()

        conn_rec_init = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        await conn_rec_init.save(session)
        assert conn_rec_init._id

        conn_rec_target = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.ABANDONED.rfc23,
        )
        await conn_rec_target.save(session)
        assert conn_rec_target._id

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id=conn_rec_target._id,
                message="Hello",
                session=session,
                outbound_handler=None,
            )

    async def test_service_start_and_return_introduction(self):
        service = await demo_service.DemoIntroductionService.service_handler()()
        start_responder = MockResponder()
        session = await self.profile.session()

        conn_rec_init = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        await conn_rec_init.save(session)
        assert conn_rec_init._id

        conn_rec_target = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        await conn_rec_target.save(session)
        assert conn_rec_target._id

        await service.start_introduction(
            init_connection_id=conn_rec_init._id,
            target_connection_id=conn_rec_target._id,
            message="Hello Start",
            session=session,
            outbound_handler=start_responder.send,
        )
        messages = start_responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert isinstance(result, demo_service.IntroInvitationRequest)
        assert result.message == "Hello Start"
        assert target["connection_id"] == conn_rec_target._id

        invite = demo_service.IntroInvitation(
            invitation=self.oob_invi_msg,
            message="Hello Invite",
            _id=result._id,
        )
        return_responder = MockResponder()

        await service.return_invitation(
            target_connection_id=conn_rec_target._id,
            invitation=invite,
            session=session,
            outbound_handler=return_responder.send,
        )
        messages = return_responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert isinstance(result, demo_service.ForwardInvitation)
        assert result.message == "Hello Invite"
        assert target["connection_id"] == conn_rec_init._id

    async def test_service_return_invitation_not_found(self):
        invite = demo_service.IntroInvitation(
            invitation=self.oob_invi_msg,
            message="Hello World",
        )

        service = await demo_service.DemoIntroductionService.service_handler()()
        session = await self.profile.session()

        conn_rec_target = ConnRecord(
            connection_id=None,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        await conn_rec_target.save(session)
        assert conn_rec_target._id

        await service.return_invitation(
            target_connection_id=conn_rec_target._id,
            invitation=invite,
            session=session,
            outbound_handler=None,
        )
