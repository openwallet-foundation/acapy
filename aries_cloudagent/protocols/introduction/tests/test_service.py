from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....config.injection_context import InjectionContext
from ....connections.models.connection_record import ConnectionRecord
from ....messaging.request_context import RequestContext
from ....messaging.responder import MockResponder
from ....storage.base import BaseStorage
from ....storage.basic import BasicStorage
from ....storage.error import StorageNotFoundError

from ...connections.messages.connection_invitation import ConnectionInvitation

from .. import base_service, demo_service

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestIntroductionRoutes(AsyncTestCase):
    def setUp(self):
        self.storage = BasicStorage()
        self.context = InjectionContext(enforce_typing=False)
        self.context.injector.bind_instance(BaseStorage, self.storage)

    async def test_service_start_introduction_no_init_conn_rec(self):
        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id="init-id",
                target_connection_id=None,
                message="Hello",
                outbound_handler=None
            )

    async def test_service_start_introduction_init_conn_rec_not_active(self):
        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )

        conn_rec_init = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_INACTIVE,
        )
        await conn_rec_init.save(self.context)
        assert conn_rec_init._id

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id=None,
                message="Hello",
                outbound_handler=None
            )

    async def test_service_start_introduction_no_target_conn_rec(self):
        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )

        conn_rec_init = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )
        await conn_rec_init.save(self.context)
        assert conn_rec_init._id
        
        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id="target-id",
                message="Hello",
                outbound_handler=None
            )

    async def test_service_start_introduction_target_conn_rec_not_active(self):
        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )

        conn_rec_init = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )
        await conn_rec_init.save(self.context)
        assert conn_rec_init._id
        

        conn_rec_target = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_INACTIVE,
        )
        await conn_rec_target.save(self.context)
        assert conn_rec_target._id

        with self.assertRaises(base_service.IntroductionError):
            await service.start_introduction(
                init_connection_id=conn_rec_init._id,
                target_connection_id=conn_rec_target._id,
                message="Hello",
                outbound_handler=None
            )

    async def test_service_start_and_return_introduction(self):
        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )
        start_responder = MockResponder()

        conn_rec_init = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )
        await conn_rec_init.save(self.context)
        assert conn_rec_init._id

        conn_rec_target = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )
        await conn_rec_target.save(self.context)
        assert conn_rec_target._id

        await service.start_introduction(
            init_connection_id=conn_rec_init._id,
            target_connection_id=conn_rec_target._id,
            message="Hello Start",
            outbound_handler=start_responder.send
        )
        messages = start_responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert isinstance(result, demo_service.InvitationRequest)
        assert result.message == "Hello Start"
        assert target["connection_id"] == conn_rec_target._id

        invite = demo_service.Invitation(
            invitation=ConnectionInvitation(
                label=TEST_LABEL,
                did=TEST_DID,
                recipient_keys=[TEST_VERKEY],
                endpoint=TEST_ENDPOINT,
                routing_keys=[TEST_ROUTE_VERKEY],
                image_url=TEST_IMAGE_URL,
            ),
            message="Hello Invite",
            _id=result._id
        ) 
        return_responder = MockResponder()

        await service.return_invitation(
            target_connection_id=conn_rec_target._id,
            invitation=invite,
            outbound_handler=return_responder.send
        )
        messages = return_responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert isinstance(result, demo_service.ForwardInvitation)
        assert result.message == "Hello Invite"
        assert target["connection_id"] == conn_rec_init._id

    async def test_service_return_invitation_not_found(self):
        invite = demo_service.Invitation(
            invitation=ConnectionInvitation(
                label=TEST_LABEL,
                did=TEST_DID,
                recipient_keys=[TEST_VERKEY],
                endpoint=TEST_ENDPOINT,
                routing_keys=[TEST_ROUTE_VERKEY],
                image_url=TEST_IMAGE_URL,
            ),
            message="Hello World",
        ) 

        service = await demo_service.DemoIntroductionService.service_handler()(
            self.context
        )

        conn_rec_target = ConnectionRecord(
            connection_id=None,
            state=ConnectionRecord.STATE_ACTIVE,
        )
        await conn_rec_target.save(self.context)
        assert conn_rec_target._id

        await service.return_invitation(
            target_connection_id=conn_rec_target._id,
            invitation=invite,
            outbound_handler=None
        )
