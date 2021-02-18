from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.error import StorageNotFoundError
from ......transport.inbound.receipt import MessageReceipt

from .....didcomm_prefix import DIDCommPrefix

from ...messages.presentation_request import PresentationRequest
from .. import presentation_request_handler as handler


S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"


class TestPresentationRequestHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec:

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = False

            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        assert not responder.messages

    async def test_called_not_found(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message_receipt = MessageReceipt()
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value=async_mock.MagicMock()
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec:

            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )
            mock_pres_ex_rec.return_value = mock_pres_ex_rec

            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
            mock_pres_mgr.return_value.receive_request.return_value.auto_present = False

            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            mock_pres_ex_rec
        )
        assert not responder.messages

    async def test_called_auto_present(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {"name": "favourite", "cred_def_id": CD_ID, "value": "potato"},
                        {"name": "icon", "cred_def_id": CD_ID, "value": "cG90YXRv"},
                    ],
                    "predicates": [],
                }
            },
            auto_present=True,
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock(
                    return_value=[{"cred_info": {"referent": "dummy"}}]
                )
            )
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_no_preview(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(auto_present=True)

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock(
                    return_value=[
                        {"cred_info": {"referent": "dummy-0"}},
                        {"cred_info": {"referent": "dummy-1"}},
                    ]
                )
            )
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_pred_no_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(auto_present=True)

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock(return_value=[])
            )
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_not_called()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        assert not responder.messages

    async def test_called_auto_present_pred_single_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(auto_present=True)

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock(
                    return_value=[{"cred_info": {"referent": "dummy-0"}}]
                )
            )
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_pred_multi_match(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(auto_present=True)

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock(
                    return_value=[
                        {"cred_info": {"referent": "dummy-0"}},
                        {"cred_info": {"referent": "dummy-1"}},
                    ]
                )
            )
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_multi_cred_match_reft(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {"name": "favourite", "cred_def_id": CD_ID, "value": "potato"},
                        {"name": "icon", "cred_def_id": CD_ID, "value": "cG90YXRv"},
                    ],
                    "predicates": [],
                }
            },
            auto_present=True,
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            mock_holder.get_credentials_for_presentation_request_by_referent = (
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
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_called_once()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "presentation_message"
        assert target == {}

    async def test_called_auto_present_bait_and_switch(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = async_mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.message = PresentationRequest()
        request_context.message.indy_proof_request = async_mock.MagicMock(
            return_value={
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
                    }
                },
                "requested_predicates": {},
            }
        )
        request_context.message_receipt = MessageReceipt()
        px_rec_instance = handler.V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {"name": "favourite", "cred_def_id": CD_ID, "value": "potato"}
                    ],
                    "predicates": [],
                }
            },
            auto_present=True,
        )

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            handler, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex_rec, async_mock.patch.object(
            handler, "IndyHolder", autospec=True
        ) as mock_holder:

            by_reft = async_mock.CoroutineMock(
                return_value=[
                    {
                        "cred_info": {
                            "referent": "dummy-0",
                            "cred_def_id": CD_ID,
                            "attrs": {"ident": "zero", "favourite": "yam"},
                        }
                    },
                    {
                        "cred_info": {
                            "referent": "dummy-1",
                            "cred_def_id": CD_ID,
                            "attrs": {"ident": "one", "favourite": "turnip"},
                        }
                    },
                    {
                        "cred_info": {
                            "referent": "dummy-2",
                            "cred_def_id": CD_ID,
                            "attrs": {
                                "ident": "two",
                                "favourite": "the idea of a potato but not a potato",
                            },
                        }
                    },
                ]
            )
            mock_holder.get_credentials_for_presentation_request_by_referent = by_reft
            request_context.inject = async_mock.MagicMock(return_value=mock_holder)

            mock_pres_ex_rec.return_value = px_rec_instance
            mock_pres_ex_rec.retrieve_by_tag_filter = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_pres_mgr.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(px_rec_instance, "presentation_message")
            )
            request_context.connection_ready = True
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()

            await handler_inst.handle(request_context, responder)
            mock_pres_mgr.return_value.create_presentation.assert_not_called()

        mock_pres_mgr.return_value.receive_request.assert_called_once_with(
            px_rec_instance
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        with async_mock.patch.object(
            handler, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_request = async_mock.CoroutineMock()
            request_context.message = PresentationRequest()
            request_context.connection_ready = False
            handler_inst = handler.PresentationRequestHandler()
            responder = MockResponder()
            with self.assertRaises(handler.HandlerException):
                await handler_inst.handle(request_context, responder)

        assert not responder.messages
