from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....config.injection_context import InjectionContext
from .....issuer.base import BaseIssuer
from .....messaging.request_context import RequestContext
from .....ledger.base import BaseLedger
from .....storage.error import StorageNotFoundError

from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_offer import CredentialOffer
from ..messages.credential_proposal import CredentialProposal
from ..messages.inner.credential_preview import CredentialPreview, CredAttrSpec
from ..models.credential_exchange import V10CredentialExchange


class TestCredentialManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.context.injector.bind_instance(BaseLedger, self.ledger)
        self.manager = CredentialManager(self.context)

    async def test_prepare_send(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )
        proposal = CredentialProposal(
            credential_proposal=preview, cred_def_id=cred_def_id, schema_id=schema_id
        )
        with async_mock.patch.object(
            self.manager, "create_offer", autospec=True
        ) as create_offer:
            create_offer.return_value = (object(), None)
            ret_exchange = await self.manager.prepare_send(connection_id, proposal)
            create_offer.assert_called_once()
            assert ret_exchange is create_offer.return_value[0]
            exchange: V10CredentialExchange = create_offer.call_args[1][
                "credential_exchange_record"
            ]
            assert exchange.auto_issue
            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.role == exchange.ROLE_ISSUER
            assert exchange.credential_proposal_dict == proposal.serialize()

    async def test_create_proposal(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        comment = "comment"
        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=schema_id
        )

        with self.assertRaises(CredentialManagerError):
            await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                credential_definition_id=None,
            )

        with self.assertRaises(CredentialManagerError):
            await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=None,
                credential_definition_id=cred_def_id,
            )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            exchange: V10CredentialExchange = await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                credential_definition_id=cred_def_id,
            )
            save_ex.assert_called_once()
        proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)

        assert exchange.auto_offer
        assert exchange.connection_id == connection_id
        assert exchange.credential_definition_id == cred_def_id
        assert exchange.schema_id == schema_id
        assert exchange.thread_id == proposal._thread_id
        assert exchange.role == exchange.ROLE_HOLDER
        assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        comment = "comment"

        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=schema_id
        )

        with self.assertRaises(CredentialManagerError):
            self.context.message = CredentialProposal(
                credential_proposal=preview, cred_def_id=None, schema_id=None
            )
            await self.manager.receive_proposal()

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            proposal = CredentialProposal(
                credential_proposal=preview, cred_def_id=cred_def_id, schema_id=None
            )
            self.context.message = proposal

            exchange = await self.manager.receive_proposal()
            save_ex.assert_called_once()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_RECEIVED
            assert exchange.schema_id == schema_id
            assert exchange.thread_id == proposal._thread_id

            ret_proposal: CredentialProposal = CredentialProposal.deserialize(
                exchange.credential_proposal_dict
            )
            attrs = ret_proposal.credential_proposal.attributes
            assert attrs == preview.attributes

    async def test_create_free_offer(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        comment = "comment"

        exchange = V10CredentialExchange(
            credential_definition_id=cred_def_id, role=V10CredentialExchange.ROLE_ISSUER
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None
            cred_offer = {"cred_def_id": cred_def_id, "schema_id": schema_id}
            issuer = async_mock.MagicMock()
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=cred_offer
            )
            self.context.injector.bind_instance(BaseIssuer, issuer)

            (ret_exchange, ret_offer) = await self.manager.create_offer(
                credential_exchange_record=exchange, comment=comment
            )
            assert ret_exchange is exchange
            save_ex.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(cred_def_id)

            assert exchange.thread_id == ret_offer._thread_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.schema_id == schema_id
            assert exchange.state == V10CredentialExchange.STATE_OFFER_SENT
            assert exchange.credential_offer == cred_offer

    async def test_create_bound_offer(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        comment = "comment"

        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )
        proposal = CredentialProposal(credential_proposal=preview)
        exchange = V10CredentialExchange(
            credential_definition_id=cred_def_id,
            credential_proposal_dict=proposal.serialize(),
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None
            cred_offer = {"cred_def_id": cred_def_id, "schema_id": schema_id}
            issuer = async_mock.MagicMock()
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=cred_offer
            )
            self.context.injector.bind_instance(BaseIssuer, issuer)

            (ret_exchange, ret_offer) = await self.manager.create_offer(
                credential_exchange_record=exchange, comment=comment
            )
            assert ret_exchange is exchange
            save_ex.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(cred_def_id)

            assert exchange.thread_id == ret_offer._thread_id
            assert exchange.schema_id == schema_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_SENT
            assert exchange.credential_offer == cred_offer

            # additionally check that credential preview was passed through
            assert ret_offer.credential_preview.attributes == preview.attributes

    async def test_receive_offer_proposed(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": schema_id, "cred_def_id": cred_def_id}
        thread_id = "thread-id"

        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )
        proposal = CredentialProposal(credential_proposal=preview)

        offer = CredentialOffer(
            credential_preview=preview,
            offers_attach=[CredentialOffer.wrap_indy_offer(indy_offer)],
        )
        offer.assign_thread_id(thread_id)

        self.context.message = offer
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            credential_definition_id=cred_def_id,
            credential_proposal_dict=proposal.serialize(),
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            schema_id=schema_id,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_offer()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.schema_id == schema_id
            assert exchange.thread_id == offer._thread_id
            assert exchange.role == V10CredentialExchange.ROLE_HOLDER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_RECEIVED
            assert exchange.credential_offer == indy_offer

            proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)
            assert proposal.credential_proposal.attributes == preview.attributes

    async def test_receive_offer_non_proposed(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": schema_id, "cred_def_id": cred_def_id}
        preview = CredentialPreview(
            attributes=(CredAttrSpec(name="attr", value="value"),)
        )
        offer = CredentialOffer(
            credential_preview=preview,
            offers_attach=[CredentialOffer.wrap_indy_offer(indy_offer)],
        )
        self.context.message = offer
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(side_effect=StorageNotFoundError),
        ) as retrieve_ex:
            exchange = await self.manager.receive_offer()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == cred_def_id
            assert exchange.schema_id == schema_id
            assert exchange.thread_id == offer._thread_id
            assert exchange.role == V10CredentialExchange.ROLE_HOLDER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_RECEIVED
            assert exchange.credential_offer == indy_offer

            proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)
            assert proposal.credential_proposal.attributes == preview.attributes
