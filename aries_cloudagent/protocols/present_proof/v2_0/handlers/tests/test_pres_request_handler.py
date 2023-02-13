from asynctest import mock as async_mock, TestCase as AsyncTestCase
from copy import deepcopy

from ......core.oob_processor import OobMessageProcessor
from ......indy.holder import IndyHolder
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.error import StorageNotFoundError
from ......transport.inbound.receipt import MessageReceipt

from ...formats.indy import handler as test_indy_handler

from ...messages.pres_format import V20PresFormat
from ...messages.pres_proposal import V20PresProposal
from ...messages.pres_request import V20PresRequest

from .. import pres_request_handler as test_module

S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
INDY_PROOF_REQ = {
    "name": "proof-request",
    "version": "1.0",
    "nonce": "1234567890",
    "requested_attributes": {
        "0_favourite_uuid": {
            "name": "favourite",
            "restrictions": [
                {
                    "cred_def_id": CD_ID,
                }
            ],
        },
        "1_icon_uuid": {
            "name": "icon",
            "restrictions": [
                {
                    "cred_def_id": CD_ID,
                }
            ],
        },
    },
    "requested_predicates": {},
}
INDY_PROOF_REQ_PRED = {
    "name": "proof-request",
    "version": "1.0",
    "nonce": "1234567890",
    "requested_attributes": {},
    "requested_predicates": {
        "0_score_GE_uuid": {
            "name": "score",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [
                {
                    "cred_def_id": CD_ID,
                }
            ],
        }
    },
}
DIF_PROOF_REQ = {
    "options": {
        "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "domain": "4jt78h47fh47",
    },
    "presentation_definition": {
        "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
        "submission_requirements": [
            {
                "name": "Citizenship Information",
                "rule": "pick",
                "count": 1,
                "from_nested": [
                    {
                        "name": "United States Citizenship Proofs",
                        "purpose": "We need you to prove you are a US citizen.",
                        "rule": "all",
                        "from": "A",
                    },
                    {
                        "name": "European Union Citizenship Proofs",
                        "purpose": "We need you to prove you are a citizen of a EU country.",
                        "rule": "all",
                        "from": "B",
                    },
                ],
            }
        ],
        "input_descriptors": [
            {
                "id": "citizenship_input_1",
                "name": "EU Driver's License",
                "group": ["A"],
                "schema": [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"}
                ],
                "constraints": {
                    "fields": [
                        {
                            "path": ["$.issuer.id", "$.issuer", "$.vc.issuer.id"],
                            "purpose": "The claim must be from one of the specified issuers",
                            "filter": {
                                "type": "string",
                                "enum": ["did:sov:4cLztgZYocjqTdAZM93t27"],
                            },
                        }
                    ]
                },
            },
            {
                "id": "citizenship_input_2",
                "name": "US Passport",
                "group": ["B"],
                "schema": [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"}
                ],
                "constraints": {
                    "fields": [
                        {
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "maximum": "2009-5-16",
                            },
                        }
                    ]
                },
            },
        ],
    },
}

DIF_PROP_REQ = {
    "input_descriptors": [
        {
            "id": "citizenship_input_1",
            "name": "EU Driver's License",
            "group": ["A"],
            "schema": [
                {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"}
            ],
            "constraints": {
                "fields": [
                    {
                        "path": ["$.issuer.id", "$.issuer", "$.vc.issuer.id"],
                        "purpose": "The claim must be from one of the specified issuers",
                        "filter": {
                            "type": "string",
                            "enum": ["did:sov:4cLztgZYocjqTdAZM93t27"],
                        },
                    }
                ]
            },
        },
        {
            "id": "citizenship_input_2",
            "name": "US Passport",
            "group": ["B"],
            "schema": [
                {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"}
            ],
            "constraints": {
                "fields": [
                    {
                        "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                        "filter": {
                            "type": "string",
                            "format": "date",
                            "maximum": "2009-5-16",
                        },
                    }
                ]
            },
        },
    ]
}


class TestPresRequestHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = V20PresRequest()
        request_context.message.attachment = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )
        px_rec_instance = test_module.V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
        )

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(auto_present=False)
            )

            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        assert not responder.messages

    async def test_called_not_found(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = V20PresRequest()
        request_context.message.attachment = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )
        px_rec_instance = test_module.V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
        )

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )
            mock_px_rec_cls.return_value = px_rec_instance

            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(auto_present=False)
            )

            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        assert not responder.messages

    async def test_called_auto_present_x(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest()
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()

        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )
        mock_px_rec = async_mock.MagicMock(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
            save_error_state=async_mock.CoroutineMock(),
        )

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[{"cred_info": {"referent": "dummy"}}]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = mock_px_rec
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                side_effect=test_module.IndyHolderError()
            )

            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()

            with async_mock.patch.object(
                handler._logger, "exception", async_mock.MagicMock()
            ) as mock_log_exc:
                await handler.handle(request_context, responder)
                mock_log_exc.assert_called_once()

    async def test_called_auto_present_indy(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest()
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )
        mock_px_rec = test_module.V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
        )

        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[{"cred_info": {"referent": "dummy"}}]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = mock_px_rec
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(mock_px_rec, "pres message")
            )

            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()

            await handler.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            mock_px_rec
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_auto_present_dif(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="dif",
                    format_=V20PresFormat.Format.DIF.aries,
                )
            ]
        )
        request_context.message.attachment = async_mock.MagicMock(
            return_value=DIF_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="dif",
                    format_=V20PresFormat.Format.DIF.aries,
                )
            ],
            proposals_attach=[AttachDecorator.data_json(DIF_PROP_REQ, ident="dif")],
        )

        px_rec_instance = test_module.V20PresExRecord(
            pres_proposal=pres_proposal,
            auto_present=True,
        )
        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = px_rec_instance
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "pres message")
            )
            request_context.connection_ready = True
            handler_inst = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_auto_present_no_preview(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ]
        )
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = test_module.V20PresExRecord(auto_present=True)

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)
        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[
                        {"cred_info": {"referent": "dummy-0"}},
                        {"cred_info": {"referent": "dummy-1"}},
                    ]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = px_rec_instance
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "pres message")
            )
            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_auto_present_pred_no_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest()
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )
        mock_px_rec = async_mock.MagicMock(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
            save_error_state=async_mock.CoroutineMock(),
        )

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(return_value=[])
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = mock_px_rec
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                side_effect=test_indy_handler.V20PresFormatHandlerError
            )
            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()

            await handler.handle(request_context, responder)
            mock_px_rec.save_error_state.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            mock_px_rec
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )

    async def test_called_auto_present_pred_single_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ]
        )
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ_PRED
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = test_module.V20PresExRecord(auto_present=True)

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[{"cred_info": {"referent": "dummy-0"}}]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = px_rec_instance
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "pres message")
            )
            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_auto_present_pred_multi_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ]
        )
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ_PRED
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = test_module.V20PresExRecord(auto_present=True)

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[
                        {"cred_info": {"referent": "dummy-0"}},
                        {"cred_info": {"referent": "dummy-1"}},
                    ]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = px_rec_instance
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "pres message")
            )
            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_auto_present_multi_cred_match_reft(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ]
        )
        request_context.message.attachment = async_mock.MagicMock(
            return_value=INDY_PROOF_REQ
        )
        request_context.message_receipt = MessageReceipt()
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")
            ],
        )

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        mock_holder = async_mock.MagicMock(
            get_credentials_for_presentation_request_by_referent=(
                async_mock.CoroutineMock(
                    return_value=[
                        {
                            "cred_info": {
                                "referent": "dummy-0",
                                "cred_def_id": CD_ID,
                                "attrs": {
                                    "ident": "zero",
                                    "favourite": "potato",
                                    "icon": "cG90YXRv",
                                },
                            }
                        },
                        {
                            "cred_info": {
                                "referent": "dummy-1",
                                "cred_def_id": CD_ID,
                                "attrs": {
                                    "ident": "one",
                                    "favourite": "spud",
                                    "icon": "c3B1ZA==",
                                },
                            }
                        },
                        {
                            "cred_info": {
                                "referent": "dummy-2",
                                "cred_def_id": CD_ID,
                                "attrs": {
                                    "ident": "two",
                                    "favourite": "patate",
                                    "icon": "cGF0YXRl",
                                },
                            }
                        },
                    ]
                )
            )
        )
        request_context.injector.bind_instance(IndyHolder, mock_holder)

        px_rec_instance = test_module.V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            auto_present=True,
        )
        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.return_value = px_rec_instance
            mock_pres_ex_rec_cls.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_pres = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "pres message")
            )
            request_context.connection_ready = True
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)
            mock_pres_mgr.return_value.create_pres.assert_called_once()

        mock_pres_mgr.return_value.receive_pres_request.assert_called_once_with(
            px_rec_instance
        )
        mock_oob_processor.find_oob_record_for_inbound_message.assert_called_once_with(
            request_context
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "pres message"
        assert target == {}

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_pres_request = async_mock.CoroutineMock()
            request_context.message = V20PresRequest()
            request_context.connection_ready = False
            handler = test_module.V20PresRequestHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException) as err:
                await handler.handle(request_context, responder)
            assert (
                err.exception.message
                == "Connection used for presentation request not ready"
            )

        assert not responder.messages

    async def test_no_conn_no_oob(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                # No oob record found
                return_value=None
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        request_context.message = V20PresRequest()
        handler = test_module.V20PresRequestHandler()
        responder = MockResponder()
        with self.assertRaises(test_module.HandlerException) as err:
            await handler.handle(request_context, responder)
        assert (
            err.exception.message
            == "No connection or associated connectionless exchange found for presentation request"
        )

        assert not responder.messages
