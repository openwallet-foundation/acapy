from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....config.injection_context import InjectionContext
from .....holder.base import BaseHolder
from .....holder.indy import IndyHolder
from .....issuer.base import BaseIssuer
from .....ledger.base import BaseLedger
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder, MockResponder
from .....storage.error import StorageNotFoundError
from .....verifier.base import BaseVerifier
from .....verifier.indy import IndyVerifier

from .. import manager as test_module
from ..manager import PresentationManager, PresentationManagerError
from ..messages.presentation import Presentation
from ..messages.presentation_ack import PresentationAck
from ..messages.presentation_proposal import PresentationProposal
from ..messages.presentation_request import PresentationRequest
from ..messages.inner.presentation_preview import (
    PresAttrSpec,
    PresentationPreview,
    PresPredSpec,
)
from ..models.presentation_exchange import V10PresentationExchange
from ..util.indy import indy_proof_request2indy_requested_creds


CONN_ID = "connection_id"
S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
PRES_PREVIEW = PresentationPreview(
    attributes=[
        PresAttrSpec(name="player", cred_def_id=CD_ID, value="Richie Knucklez"),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
        ),
    ],
    predicates=[
        PresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)
PROOF_REQ_NAME="name"
PROOF_REQ_VERSION="1.0"
PROOF_REQ_NONCE="12345"


class TestPresentationManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        Holder = async_mock.MagicMock(IndyHolder, autospec=True)
        self.holder = Holder()
        self.holder.get_credentials_for_presentation_request_by_referent = (
            async_mock.CoroutineMock(
                return_value=(
                    {
                        "cred_info": {
                            "referent": "dummy_reft"
                    }
                },  # leave this comma: return a tuple
                )
            )
        )
        self.holder.get_credential = async_mock.CoroutineMock(
            return_value={
                "schema_id": S_ID,
                "cred_def_id": CD_ID,
            }
        )
        self.holder.create_presentation = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.context.injector.bind_instance(BaseHolder, self.holder)

        Verifier = async_mock.MagicMock(IndyVerifier, autospec=True)
        self.verifier = Verifier()
        self.verifier.verify_presentation = (
            async_mock.CoroutineMock(
                return_value="true"
            )
        )
        self.context.injector.bind_instance(BaseVerifier, self.verifier)

        self.manager = PresentationManager(self.context)

    async def test_create_exchange_for_proposal(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        proposal = PresentationProposal()
        self.context.message = proposal

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            PresentationProposal, "serialize", autospec=True
        ):
            exchange = await self.manager.create_exchange_for_proposal(
                CONN_ID, proposal, auto_present=None
            )
            save_ex.assert_called_once()

            assert exchange.thread_id == proposal._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_PROVER
            assert exchange.state == V10PresentationExchange.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        proposal = PresentationProposal()
        self.context.message = proposal

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.receive_proposal()
            save_ex.assert_called_once()

            assert exchange.state == V10PresentationExchange.STATE_PROPOSAL_RECEIVED

    async def test_create_bound_request(self):
        comment = "comment"

        proposal = PresentationProposal(
            presentation_proposal=PRES_PREVIEW
        )
        exchange = V10PresentationExchange(
            presentation_proposal_dict=proposal.serialize(),
            role=V10PresentationExchange.ROLE_VERIFIER,
        )
        exchange.save = async_mock.CoroutineMock()
        (ret_exchange, pres_req_msg) = await self.manager.create_bound_request(
            presentation_exchange_record=exchange,
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            comment=comment,
        )
        assert ret_exchange is exchange
        exchange.save.assert_called_once()

    async def test_create_exchange_for_request(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.create_exchange_for_request(CONN_ID, request)
            save_ex.assert_called_once()

            assert exchange.thread_id == request._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_VERIFIER
            assert exchange.state == V10PresentationExchange.STATE_REQUEST_SENT

    async def test_receive_request(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        request = PresentationRequest()
        self.context.message = request

        exchange_in = V10PresentationExchange()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.receive_request(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == V10PresentationExchange.STATE_REQUEST_RECEIVED

    async def test_create_presentation(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
        )

        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator:
            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_request2indy_requested_creds(
                indy_proof_req, self.holder
            )

            (exchange_out, pres_msg) = (
                await self.manager.create_presentation(exchange_in, req_creds)
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_no_matching_creds_for_proof_req(self):
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
        )
        self.holder.get_credentials_for_presentation_request_by_referent.return_value = ()

        with self.assertRaises(ValueError):
            await indy_proof_request2indy_requested_creds(
                indy_proof_req, self.holder
            )

        self.holder.get_credentials_for_presentation_request_by_referent.return_value = (
            {
                "cred_info": {
                    "referent": "dummy_reft"
                }
            },  # leave this comma: return a tuple
        )

    async def test_receive_presentation(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_dummy = V10PresentationExchange()
        self.context.message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation()
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_verify_presentation(self):
        exchange_in = V10PresentationExchange()
        exchange_in.presentation = {
            "identifiers": [
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                }
            ]
        }

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.verify_presentation(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_VERIFIED
            )

    async def test_send_presentation_ack(self):
        exchange = V10PresentationExchange()
        proposal = PresentationProposal()
        self.context.message = proposal

        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_presentation_ack(exchange)
        messages = responder.messages
        assert len(messages) == 1

    async def test_send_presentation_ack_no_responder(self):
        exchange = V10PresentationExchange()
        proposal = PresentationProposal()
        self.context.message = proposal

        self.context.injector.clear_binding(BaseResponder)
        await self.manager.send_presentation_ack(exchange)

    async def test_receive_presentation_ack(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_dummy = V10PresentationExchange()
        self.context.message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation_ack()
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_ACKED
            )
