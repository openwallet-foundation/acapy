from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....config.injection_context import InjectionContext
from .....holder.base import BaseHolder
from .....issuer.base import BaseIssuer
from .....messaging.request_context import RequestContext
from .....ledger.base import BaseLedger
from .....storage.error import StorageNotFoundError

from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_ack import CredentialAck
from ..messages.credential_issue import CredentialIssue
from ..messages.credential_offer import CredentialOffer
from ..messages.credential_proposal import CredentialProposal
from ..messages.credential_request import CredentialRequest
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
            create_offer.return_value = (async_mock.MagicMock(), async_mock.MagicMock())
            ret_exchange, ret_cred_offer = await self.manager.prepare_send(connection_id, proposal)
            create_offer.assert_called_once()
            assert ret_exchange is create_offer.return_value[0]
            arg_exchange = create_offer.call_args[1]["credential_exchange_record"]
            assert arg_exchange.auto_issue
            assert arg_exchange.connection_id == connection_id
            assert arg_exchange.schema_id == None
            assert arg_exchange.credential_definition_id == None
            assert arg_exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert arg_exchange.credential_proposal_dict == proposal.serialize()

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
                credential_preview=None,
                cred_def_id=cred_def_id,
            )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            exchange: V10CredentialExchange = await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                cred_def_id=cred_def_id,
            )
            save_ex.assert_called_once()

            await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                cred_def_id=None,
            )  # OK to leave open until offer

        proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)

        assert exchange.auto_offer
        assert exchange.connection_id == connection_id
        assert not exchange.credential_definition_id  # leave open until offer
        assert not exchange.schema_id  # leave open until offer
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
            assert exchange.credential_definition_id == None
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_RECEIVED
            assert exchange.schema_id == None
            assert exchange.thread_id == proposal._thread_id

            ret_proposal: CredentialProposal = CredentialProposal.deserialize(
                exchange.credential_proposal_dict
            )
            attrs = ret_proposal.credential_proposal.attributes
            assert attrs == preview.attributes

            self.context.message = CredentialProposal(
                credential_proposal=preview, cred_def_id=None, schema_id=None
            )
            await self.manager.receive_proposal()  # OK to leave open until offer

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
            credential_proposal_dict=proposal.serialize(),
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key, async_mock.patch.object(
            CredentialManager, "_match_sent_cred_def_id", autospec=True
        ) as match_cred_def_id:
            get_cached_key.return_value = None
            cred_offer = {"cred_def_id": cred_def_id, "schema_id": schema_id}
            issuer = async_mock.MagicMock()
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=cred_offer
            )
            self.context.injector.bind_instance(BaseIssuer, issuer)
            match_cred_def_id.return_value=cred_def_id

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

    async def test_create_request(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": schema_id, "cred_def_id": cred_def_id, "nonce": "0"}
        indy_cred_req = {"schema_id": schema_id, "cred_def_id": cred_def_id}
        thread_id = "thread-id"
        holder_did = "did"

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            credential_definition_id=cred_def_id,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            schema_id=schema_id,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None

            cred_def = {"cred": "def"}
            self.ledger.get_credential_definition = async_mock.CoroutineMock(
                return_value=cred_def
            )

            cred_req_meta = object()
            holder = async_mock.MagicMock()
            holder.create_credential_request = async_mock.CoroutineMock(
                return_value=(indy_cred_req, cred_req_meta)
            )
            self.context.injector.bind_instance(BaseHolder, holder)

            ret_exchange, ret_request = await self.manager.create_request(
                stored_exchange, holder_did
            )

            holder.create_credential_request.assert_called_once_with(
                indy_offer, cred_def, holder_did
            )

            assert ret_request.indy_cred_req() == indy_cred_req
            assert ret_request._thread_id == thread_id

            assert ret_exchange.state == V10CredentialExchange.STATE_REQUEST_SENT

    async def test_receive_request(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        indy_cred_req = {"schema_id": schema_id, "cred_def_id": cred_def_id}

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        request = CredentialRequest(
            requests_attach=[CredentialRequest.wrap_indy_cred_req(indy_cred_req)]
        )
        self.context.message = request
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_request()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, request._thread_id
            )
            save_ex.assert_called_once()

            assert exchange.state == V10CredentialExchange.STATE_REQUEST_RECEIVED
            assert exchange.credential_request == indy_cred_req

    async def test_issue_credential(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": schema_id, "cred_def_id": cred_def_id, "nonce": "0"}
        indy_cred_req = {"schema_id": schema_id, "cred_def_id": cred_def_id}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            thread_id=thread_id,
        )

        schema = object()
        self.ledger.get_schema = async_mock.CoroutineMock(return_value=schema)

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        cred_revoc = object()
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(cred, cred_revoc)
        )
        self.context.injector.bind_instance(BaseIssuer, issuer)

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:

            ret_exchange, ret_cred_issue = await self.manager.issue_credential(
                stored_exchange, comment=comment, credential_values=cred_values
            )

            save_ex.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                schema, indy_offer, indy_cred_req, cred_values
            )

            assert ret_exchange.credential == cred
            assert ret_cred_issue.indy_credential() == cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_receive_credential(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        indy_cred = {"indy": "credential"}

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        issue = CredentialIssue(
            credentials_attach=[CredentialIssue.wrap_indy_credential(indy_cred)]
        )
        self.context.message = issue
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_credential()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, issue._thread_id
            )
            save_ex.assert_called_once()

            assert exchange.raw_credential == indy_cred
            assert exchange.state == V10CredentialExchange.STATE_CREDENTIAL_RECEIVED

    async def test_store_credential(self):
        schema_id = "LjgpST2rjsoxYegQDRm7EL:2:bc-reg:1.0"
        cred_def_id = "LjgpST2rjsoxYegQDRm7EL:3:CL:18:tag"
        connection_id = "test_conn_id"
        cred = {"cred_def_id": cred_def_id}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            credential_definition_id=cred_def_id,
            credential_request_metadata=cred_req_meta,
            credential_proposal_dict={"credential_proposal": {}},
            raw_credential=cred,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            thread_id=thread_id,
        )

        cred_def = object()
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=cred_def
        )

        cred_id = "cred-id"
        holder = async_mock.MagicMock()
        holder.store_credential = async_mock.CoroutineMock(return_value=cred_id)
        stored_cred = {"stored": "cred"}
        holder.get_credential = async_mock.CoroutineMock(return_value=stored_cred)
        self.context.injector.bind_instance(BaseHolder, holder)

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            ret_exchange, ret_cred_ack = await self.manager.store_credential(
                stored_exchange
            )

            save_ex.assert_called_once()

            self.ledger.get_credential_definition.assert_called_once_with(cred_def_id)

            holder.store_credential.assert_called_once_with(
                cred_def,
                cred,
                cred_req_meta,
                mock_preview_deserialize.return_value.mime_types.return_value,
            )

            holder.get_credential.assert_called_once_with(cred_id)

            assert ret_exchange.credential_id == cred_id
            assert ret_exchange.credential == stored_cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ACKED
            assert ret_cred_ack._thread_id == thread_id

    async def test_credential_ack(self):
        connection_id = "connection-id"
        stored_exchange = V10CredentialExchange(
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        ack = CredentialAck()
        self.context.message = ack
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "delete_record", autospec=True
        ) as delete_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            ret_exchange = await self.manager.receive_credential_ack()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, ack._thread_id
            )
            save_ex.assert_called_once()

            assert ret_exchange.state == V10CredentialExchange.STATE_ACKED
            delete_ex.assert_called_once()
