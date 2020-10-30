import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....cache.base import BaseCache
from .....cache.basic import BasicCache
from .....config.base import InjectorError
from .....config.injection_context import InjectionContext
from .....connections.models.conn23rec import Conn23Record
from .....connections.models.connection_target import ConnectionTarget
from .....connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from .....ledger.base import BaseLedger
from .....messaging.responder import BaseResponder, MockResponder
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....storage.base import BaseStorage
from .....storage.basic import BasicStorage
from .....storage.error import StorageNotFoundError
from .....transport.inbound.receipt import MessageReceipt
from .....wallet.base import BaseWallet, DIDInfo
from .....wallet.basic import BasicWallet
from .....wallet.error import WalletNotFoundError
from .....wallet.util import naked_to_did_key

from ....out_of_band.v1_0.messages.invitation import InvitationMessage
from ....out_of_band.v1_0.messages.service import Service as OOBService
from ....routing.v1_0.manager import RoutingManager

from .. import manager as test_module
from ..manager import Conn23Manager, Conn23ManagerError
from ..messages.request import Conn23Request
from ..messages.response import Conn23Response
from ..messages.complete import Conn23Complete


class TestConfig:

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

    def make_did_doc(self, did, verkey):
        doc = DIDDoc(did=did)
        controller = did
        ident = "1"
        pk_value = verkey
        pk = PublicKey(
            did, ident, pk_value, PublicKeyType.ED25519_SIG_2018, controller, False
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            did,
            "indy",
            "IndyAgent",
            recip_keys,  # naked
            router_keys,  # naked
            self.test_endpoint
        )
        doc.set(service)

        return doc


class TestConnectionManager(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.storage = BasicStorage()
        self.cache = BasicCache()
        self.wallet = BasicWallet()
        self.did_info = await self.wallet.create_local_did()

        self.responder = MockResponder()
        self.responder.send = async_mock.CoroutineMock()

        self.context = InjectionContext(enforce_typing=False)
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.context.injector.bind_instance(BaseResponder, self.responder)
        self.context.injector.bind_instance(BaseCache, self.cache)
        self.context.update_settings(
            {
                "default_endpoint": "http://aries.ca/endpoint",
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )

        self.manager = Conn23Manager(self.context)
        self.test_conn_rec = Conn23Record(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=Conn23Record.Role.REQUESTER.rfc23,
            state=Conn23Record.STATE_COMPLETED,
        )

    async def test_key_x(self):
        connect_record, connect_invite = await self.manager.create_invitation(
            include_handshake=True
        )

        receipt = MessageReceipt(recipient_verkey=connect_record.invitation_key)

        did_doc = self.make_did_doc(self.test_target_did, self.test_target_verkey)
        did_doc_attach = AttachDecorator.from_indy_dict(did_doc.serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        requestA = Conn23Request(
            label="SameInviteRequestA",
            did=self.test_target_did,
            did_doc_attach=did_doc_attach,
        )
        await self.manager.receive_request(requestA, receipt)
