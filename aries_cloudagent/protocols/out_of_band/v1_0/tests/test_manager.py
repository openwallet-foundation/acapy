"""Test OOB Manager."""

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import ANY

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .....connections.models.conn_record import ConnRecord
from .....connections.models.connection_target import ConnectionTarget
from .....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .....core.event_bus import EventBus
from .....core.in_memory import InMemoryProfile
from .....core.util import get_version_from_message
from .....core.oob_processor import OobMessageProcessor
from .....did.did_key import DIDKey
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.decorators.service_decorator import ServiceDecorator
from .....messaging.responder import BaseResponder, MockResponder
from .....messaging.util import datetime_now, datetime_to_str, str_to_epoch
from .....multitenant.base import BaseMultitenantManager
from .....multitenant.manager import MultitenantManager
from .....protocols.coordinate_mediation.v1_0.manager import MediationManager
from .....protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from .....protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from .....protocols.didexchange.v1_0.manager import DIDXManager
from .....protocols.issue_credential.v1_0.messages.credential_offer import (
    CredentialOffer as V10CredOffer,
)
from .....protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredAttrSpec as V10CredAttrSpec,
)
from .....protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredentialPreview as V10CredentialPreview,
)
from .....protocols.issue_credential.v1_0.tests import INDY_OFFER
from .....protocols.issue_credential.v2_0.message_types import (
    ATTACHMENT_FORMAT as V20_CRED_ATTACH_FORMAT,
)
from .....protocols.issue_credential.v2_0.message_types import CRED_20_OFFER
from .....protocols.issue_credential.v2_0.messages.cred_format import V20CredFormat
from .....protocols.issue_credential.v2_0.messages.cred_offer import V20CredOffer
from .....protocols.issue_credential.v2_0.messages.inner.cred_preview import (
    V20CredAttrSpec,
    V20CredPreview,
)

from .....protocols.present_proof.v1_0.message_types import (
    ATTACH_DECO_IDS as V10_PRES_ATTACH_FORMAT,
)
from .....protocols.present_proof.v1_0.message_types import PRESENTATION_REQUEST
from .....protocols.present_proof.v1_0.messages.presentation_request import (
    PresentationRequest,
)

from .....protocols.present_proof.v2_0.message_types import (
    ATTACHMENT_FORMAT as V20_PRES_ATTACH_FORMAT,
)
from .....protocols.present_proof.v2_0.message_types import PRES_20_REQUEST
from .....protocols.present_proof.v2_0.messages.pres_format import V20PresFormat
from .....protocols.present_proof.v2_0.messages.pres_request import V20PresRequest
from .....storage.error import StorageNotFoundError
from .....transport.inbound.receipt import MessageReceipt
from .....wallet.did_info import DIDInfo, KeyInfo
from .....wallet.did_method import SOV
from .....wallet.in_memory import InMemoryWallet
from .....wallet.key_type import ED25519
from ....connections.v1_0.messages.connection_invitation import ConnectionInvitation
from ....didcomm_prefix import DIDCommPrefix
from ....issue_credential.v1_0.message_types import CREDENTIAL_OFFER
from ....issue_credential.v1_0.models.credential_exchange import V10CredentialExchange
from .. import manager as test_module
from ..manager import (
    REUSE_ACCEPTED_WEBHOOK_TOPIC,
    REUSE_WEBHOOK_TOPIC,
    OutOfBandManager,
    OutOfBandManagerError,
)
from ..message_types import INVITATION, MESSAGE_REUSE
from ..messages.invitation import HSProto, InvitationMessage
from ..messages.invitation import Service as OobService
from ..messages.problem_report import ProblemReport, ProblemReportReason
from ..messages.reuse import HandshakeReuse
from ..messages.reuse_accept import HandshakeReuseAccept
from ..models.invitation import InvitationRecord
from ..models.oob_record import OobRecord


class TestConfig:
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"
    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    their_public_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_service = OobService(
        recipient_keys=[test_verkey],
        routing_keys=[],
        service_endpoint=test_endpoint,
    )
    NOW_8601 = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
    TEST_INVI_MESSAGE_TYPE = "out-of-band/1.1/invitation"
    NOW_EPOCH = str_to_epoch(NOW_8601)
    CD_ID = "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
    INDY_PROOF_REQ = json.loads(
        f"""{{
        "name": "proof-req",
        "version": "1.0",
        "nonce": "12345",
        "requested_attributes": {{
            "0_player_uuid": {{
                "name": "player",
                "restrictions": [
                    {{
                        "cred_def_id": "{CD_ID}"
                    }}
                ],
                "non_revoked": {{
                    "from": {NOW_EPOCH},
                    "to": {NOW_EPOCH}
                }}
            }},
            "0_screencapture_uuid": {{
                "name": "screenCapture",
                "restrictions": [
                    {{
                        "cred_def_id": "{CD_ID}"
                    }}
                ],
                "non_revoked": {{
                    "from": {NOW_EPOCH},
                    "to": {NOW_EPOCH}
                }}
            }}
        }},
        "requested_predicates": {{
            "0_highscore_GE_uuid": {{
                "name": "highScore",
                "p_type": ">=",
                "p_value": 1000000,
                "restrictions": [
                    {{
                        "cred_def_id": "{CD_ID}"
                    }}
                ],
                "non_revoked": {{
                    "from": {NOW_EPOCH},
                    "to": {NOW_EPOCH}
                }}
            }}
        }}
    }}"""
    )
    DIF_PROOF_REQ = {
        "presentation_definition": {
            "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
            "submission_requirements": [
                {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A",
                }
            ],
            "input_descriptors": [
                {
                    "id": "citizenship_input_1",
                    "name": "EU Driver's License",
                    "group": ["A"],
                    "schema": [
                        {
                            "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints": {
                        "limit_disclosure": "required",
                        "fields": [
                            {
                                "path": ["$.credentialSubject.givenName"],
                                "purpose": "The claim must be from one of the specified issuers",
                                "filter": {
                                    "type": "string",
                                    "enum": ["JOHN", "CAI"],
                                },
                            }
                        ],
                    },
                }
            ],
        },
    }

    PRES_REQ_V1 = PresentationRequest(
        comment="Test",
        request_presentations_attach=[
            AttachDecorator.data_base64(
                mapping=INDY_PROOF_REQ,
                ident=V10_PRES_ATTACH_FORMAT[PRESENTATION_REQUEST],
            )
        ],
    )
    pres_req_dict = PRES_REQ_V1.request_presentations_attach[0].serialize()
    req_attach_v1 = {
        "@id": "request-0",
        "mime-type": "application/json",
        "data": {
            "json": {
                "@type": DIDCommPrefix.qualify_current(PRESENTATION_REQUEST),
                "@id": "12345678-0123-4567-1234-567812345678",
                "comment": "some comment",
                "request_presentations~attach": [pres_req_dict],
            }
        },
    }

    PRES_REQ_V2 = V20PresRequest(
        comment="some comment",
        will_confirm=True,
        formats=[
            V20PresFormat(
                attach_id="indy",
                format_=V20_PRES_ATTACH_FORMAT[PRES_20_REQUEST][
                    V20PresFormat.Format.INDY.api
                ],
            )
        ],
        request_presentations_attach=[
            AttachDecorator.data_base64(mapping=INDY_PROOF_REQ, ident="indy")
        ],
    )

    DIF_PRES_REQ_V2 = V20PresRequest(
        comment="some comment",
        will_confirm=True,
        formats=[
            V20PresFormat(
                attach_id="dif",
                format_=V20_PRES_ATTACH_FORMAT[PRES_20_REQUEST][
                    V20PresFormat.Format.DIF.api
                ],
            )
        ],
        request_presentations_attach=[
            AttachDecorator.data_json(mapping=DIF_PROOF_REQ, ident="dif")
        ],
    )

    CRED_OFFER_V1 = V10CredOffer(
        credential_preview=V10CredentialPreview(
            attributes=(
                V10CredAttrSpec(name="legalName", value="value"),
                V10CredAttrSpec(name="jurisdictionId", value="value"),
                V10CredAttrSpec(name="incorporationDate", value="value"),
            )
        ),
        offers_attach=[V10CredOffer.wrap_indy_offer(INDY_OFFER)],
    )

    CRED_OFFER_V2 = V20CredOffer(
        credential_preview=V20CredPreview(
            attributes=V20CredAttrSpec.list_plain(
                {
                    "legalName": "value",
                    "jurisdictionId": "value",
                    "incorporationDate": "value",
                }
            ),
        ),
        formats=[
            V20CredFormat(
                attach_id="indy",
                format_=V20_CRED_ATTACH_FORMAT[CRED_20_OFFER][
                    V20CredFormat.Format.INDY.api
                ],
            )
        ],
        offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="indy")],
    )

    req_attach_v2 = AttachDecorator.data_json(
        mapping=PRES_REQ_V2.serialize(),
        ident="request-0",
    ).serialize()

    indy_cred_req = {
        "schema_id": f"{test_did}:2:bc-reg:1.0",
        "cred_def_id": f"{test_did}:3:CL:12:tag1",
    }
    cred_req_meta = {}

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
            did, "indy", "IndyAgent", recip_keys, router_keys, TestConfig.test_endpoint
        )
        doc.set(service)
        return doc


class TestOOBManager(AsyncTestCase, TestConfig):
    def setUp(self):
        self.responder = MockResponder()
        self.responder.send = async_mock.CoroutineMock()

        self.test_mediator_routing_keys = [
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRR"
        ]
        self.test_mediator_conn_id = "mediator-conn-id"
        self.test_mediator_endpoint = "http://mediator.example.com"

        self.route_manager = async_mock.MagicMock(RouteManager)
        self.route_manager.routing_info = async_mock.CoroutineMock(
            return_value=(self.test_mediator_routing_keys, self.test_mediator_endpoint)
        )

        self.profile = InMemoryProfile.test_profile(
            {
                "default_endpoint": TestConfig.test_endpoint,
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            },
            bind={
                RouteManager: self.route_manager,
            },
        )

        self.profile.context.injector.bind_instance(BaseResponder, self.responder)
        self.profile.context.injector.bind_instance(
            EventBus, async_mock.MagicMock(notify=async_mock.CoroutineMock())
        )
        self.mt_mgr = async_mock.MagicMock()
        self.mt_mgr = async_mock.create_autospec(MultitenantManager)
        self.profile.context.injector.bind_instance(BaseMultitenantManager, self.mt_mgr)

        self.multitenant_mgr = async_mock.MagicMock(MultitenantManager, autospec=True)
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, self.multitenant_mgr
        )
        self.manager = OutOfBandManager(self.profile)
        assert self.manager.profile
        self.manager.resolve_invitation = async_mock.CoroutineMock()
        self.manager.resolve_invitation.return_value = (
            TestConfig.test_endpoint,
            [TestConfig.test_verkey],
            [],
        )

        self.test_conn_rec = async_mock.MagicMock(
            connection_id="dummy",
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=ConnRecord.Role.REQUESTER,
            state=ConnRecord.State.COMPLETED,
            their_public_did=self.their_public_did,
            save=async_mock.CoroutineMock(),
        )

    async def test_create_invitation_handshake_succeeds(self):
        self.profile.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=[HSProto.RFC23],
            )

            assert invi_rec.invitation._type == DIDCommPrefix.qualify_current(
                self.TEST_INVI_MESSAGE_TYPE
            )
            assert not invi_rec.invitation.requests_attach
            assert (
                DIDCommPrefix.qualify_current(HSProto.RFC23.name)
                in invi_rec.invitation.handshake_protocols
            )
            assert invi_rec.invitation.services == [f"did:sov:{TestConfig.test_did}"]

    async def test_create_invitation_multitenant_local(self):
        self.profile.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
            }
        )

        with async_mock.patch.object(
            InMemoryWallet, "create_signing_key", autospec=True
        ) as mock_wallet_create_signing_key, async_mock.patch.object(
            self.multitenant_mgr, "get_default_mediator"
        ) as mock_get_default_mediator:
            mock_wallet_create_signing_key.return_value = KeyInfo(
                TestConfig.test_verkey, None, ED25519
            )
            mock_get_default_mediator.return_value = MediationRecord()
            await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                hs_protos=[HSProto.RFC23],
                multi_use=False,
            )

            self.route_manager.route_invitation.assert_called_once()

    async def test_create_invitation_multitenant_public(self):
        self.profile.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
                "public_invites": True,
            }
        )

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            await self.manager.create_invitation(
                hs_protos=[HSProto.RFC23],
                public=True,
                multi_use=False,
            )

            self.route_manager.route_invitation.assert_called_once()

    async def test_create_invitation_mediation_overwrites_routing_and_endpoint(self):
        async with self.profile.session() as session:
            mock_conn_rec = async_mock.MagicMock()

            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                MediationManager,
                "get_default_mediator_id",
            ) as mock_get_default_mediator, async_mock.patch.object(
                mock_conn_rec, "metadata_set", async_mock.CoroutineMock()
            ) as mock_metadata_set:
                invite = await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    my_label="test123",
                    hs_protos=[HSProto.RFC23],
                    mediation_id=mediation_record.mediation_id,
                )
                assert isinstance(invite, InvitationRecord)
                assert invite.invitation._type == DIDCommPrefix.qualify_current(
                    self.TEST_INVI_MESSAGE_TYPE
                )
                assert invite.invitation.label == "test123"
                assert (
                    DIDKey.from_did(
                        invite.invitation.services[0].routing_keys[0]
                    ).public_key_b58
                    == self.test_mediator_routing_keys[0]
                )
                assert (
                    invite.invitation.services[0].service_endpoint
                    == self.test_mediator_endpoint
                )
                mock_get_default_mediator.assert_not_called()

    async def test_create_invitation_no_handshake_no_attachments_x(self):
        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=None,
                multi_use=False,
            )
        assert "Invitation must include" in str(context.exception)

    async def test_create_invitation_attachment_v1_0_cred_offer(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            mock_retrieve_cxid.return_value = async_mock.MagicMock(
                credential_offer_dict=self.CRED_OFFER_V1
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=[HSProto.RFC23],
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            mock_retrieve_cxid.assert_called_once_with(ANY, "dummy-id")
            assert isinstance(invi_rec, InvitationRecord)
            assert invi_rec.invitation.handshake_protocols
            assert invi_rec.invitation.requests_attach[0].content[
                "@type"
            ] == DIDCommPrefix.qualify_current(CREDENTIAL_OFFER)

    async def test_create_invitation_attachment_v1_0_cred_offer_no_handshake(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            mock_retrieve_cxid.return_value = async_mock.MagicMock(
                credential_offer_dict=self.CRED_OFFER_V1
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=None,
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            mock_retrieve_cxid.assert_called_once_with(ANY, "dummy-id")
            assert isinstance(invi_rec, InvitationRecord)
            assert not invi_rec.invitation.handshake_protocols
            assert invi_rec.invitation.requests_attach[0].content == {
                **self.CRED_OFFER_V1.serialize(),
                "~thread": {"pthid": invi_rec.invi_msg_id},
            }

    async def test_create_invitation_attachment_v2_0_cred_offer(self):
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module.V10CredentialExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid_v1, async_mock.patch.object(
            test_module.V20CredExRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_cxid_v2:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            mock_retrieve_cxid_v1.side_effect = test_module.StorageNotFoundError()
            mock_retrieve_cxid_v2.return_value = async_mock.MagicMock(
                cred_offer=async_mock.MagicMock(
                    serialize=async_mock.MagicMock(return_value={"cred": "offer"})
                )
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=False,
                hs_protos=None,
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            mock_retrieve_cxid_v2.assert_called_once_with(ANY, "dummy-id")
            assert isinstance(invi_rec, InvitationRecord)
            assert not invi_rec.invitation.handshake_protocols
            assert invi_rec.invitation.requests_attach[0].content == {
                "cred": "offer",
                "~thread": {"pthid": invi_rec.invi_msg_id},
            }

    async def test_create_invitation_attachment_present_proof_v1_0(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module.V10PresentationExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_pxid:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            mock_retrieve_pxid.return_value = async_mock.MagicMock(
                presentation_request_dict=self.PRES_REQ_V1
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=[test_module.HSProto.RFC23],
                multi_use=False,
                attachments=[{"type": "present-proof", "id": "dummy-id"}],
            )

            mock_retrieve_pxid.assert_called_once_with(ANY, "dummy-id")
            assert isinstance(invi_rec, InvitationRecord)
            assert invi_rec.invitation.handshake_protocols
            assert invi_rec.invitation.requests_attach[0].content == {
                **self.PRES_REQ_V1.serialize(),
                "~thread": {"pthid": invi_rec.invi_msg_id},
            }

    async def test_create_invitation_attachment_present_proof_v2_0(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module.V10PresentationExchange,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_pxid_1, async_mock.patch.object(
            test_module.V20PresExRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_pxid_2:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            mock_retrieve_pxid_1.side_effect = StorageNotFoundError()
            mock_retrieve_pxid_2.return_value = async_mock.MagicMock(
                pres_request=TestConfig.PRES_REQ_V2
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=[test_module.HSProto.RFC23],
                multi_use=False,
                attachments=[{"type": "present-proof", "id": "dummy-id"}],
            )

            mock_retrieve_pxid_2.assert_called_once_with(ANY, "dummy-id")
            assert isinstance(invi_rec, InvitationRecord)
            assert invi_rec.invitation.handshake_protocols
            assert invi_rec.invitation.requests_attach[0].content == {
                **TestConfig.PRES_REQ_V2.serialize(),
                "~thread": {"pthid": invi_rec.invi_msg_id},
            }

    async def test_create_invitation_public_x_no_public_invites(self):
        self.profile.context.update_settings({"public_invites": False})

        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                public=True,
                my_endpoint="testendpoint",
                hs_protos=[test_module.HSProto.RFC23],
                multi_use=False,
            )
        assert "Public invitations are not enabled" in str(context.exception)

    async def test_create_invitation_public_x_multi_use(self):
        self.profile.context.update_settings({"public_invites": True})

        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                public=True,
                my_endpoint="testendpoint",
                hs_protos=[test_module.HSProto.RFC23],
                multi_use=True,
            )
        assert "Cannot create public invitation with" in str(context.exception)

    async def test_create_invitation_requests_attach_x_multi_use(self):
        with self.assertRaises(OutOfBandManagerError) as context:
            await self.manager.create_invitation(
                public=False,
                my_endpoint="testendpoint",
                hs_protos=[test_module.HSProto.RFC23],
                attachments=[{"some": "attachment"}],
                multi_use=True,
            )
        assert "Cannot create multi use invitation with attachments" in str(
            context.exception
        )

    async def test_create_invitation_public_x_no_public_did(self):
        self.profile.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = None
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=True,
                    my_endpoint="testendpoint",
                    hs_protos=[test_module.HSProto.RFC23],
                    multi_use=False,
                )
            assert "Cannot create public invitation with no public DID" in str(
                context.exception
            )

    async def test_create_invitation_attachment_x(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    public=False,
                    hs_protos=[test_module.HSProto.RFC23],
                    multi_use=False,
                    attachments=[{"having": "attachment", "is": "no", "good": "here"}],
                )
            assert "Unknown attachment type" in str(context.exception)

    async def test_create_invitation_peer_did(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings(
                {
                    "multitenant.enabled": True,
                    "wallet.id": "my-wallet",
                }
            )
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                self.multitenant_mgr, "get_default_mediator"
            ) as mock_get_default_mediator:
                mock_get_default_mediator.return_value = mediation_record
                invi_rec = await self.manager.create_invitation(
                    my_label="That guy",
                    my_endpoint=None,
                    public=False,
                    hs_protos=[test_module.HSProto.RFC23],
                    multi_use=False,
                    service_accept=["didcomm/aip1", "didcomm/aip2;env=rfc19"],
                )

                assert invi_rec._invitation.ser[
                    "@type"
                ] == DIDCommPrefix.qualify_current(self.TEST_INVI_MESSAGE_TYPE)
                assert not invi_rec._invitation.ser.get("requests~attach")
                assert invi_rec.invitation.label == "That guy"
                assert (
                    DIDCommPrefix.qualify_current(HSProto.RFC23.name)
                    in invi_rec.invitation.handshake_protocols
                )
                service = invi_rec._invitation.ser["services"][0]
                assert service["id"] == "#inline"
                assert service["type"] == "did-communication"
                assert len(service["recipientKeys"]) == 1
                assert (
                    service["routingKeys"][0]
                    == DIDKey.from_public_key_b58(
                        self.test_mediator_routing_keys[0], ED25519
                    ).did
                )
                assert service["serviceEndpoint"] == self.test_mediator_endpoint

    async def test_create_invitation_metadata_assigned(self):
        async with self.profile.session() as session:
            invi_rec = await self.manager.create_invitation(
                hs_protos=[test_module.HSProto.RFC23],
                metadata={"hello": "world"},
            )
            service = invi_rec._invitation.ser["services"][0]
            invitation_key = DIDKey.from_did(service["recipientKeys"][0]).public_key_b58
            record = await ConnRecord.retrieve_by_invitation_key(
                session, invitation_key
            )
            assert await record.metadata_get_all(session) == {"hello": "world"}

    async def test_create_invitation_x_public_metadata(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=SOV,
                key_type=ED25519,
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=False,
                    hs_protos=[],
                    attachments=[{"an": "attachment"}],
                    metadata={"hello": "world"},
                    multi_use=False,
                )
            assert "Cannot store metadata without handshake protocols" in str(
                context.exception
            )

    async def test_wait_for_conn_rec_active_retrieve_by_id(self):
        with async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    connection_id="the-retrieved-connection-id"
                )
            ),
        ):
            conn_rec = await self.manager._wait_for_conn_rec_active("a-connection-id")
            assert conn_rec.connection_id == "the-retrieved-connection-id"

    async def test_create_handshake_reuse_msg(self):
        self.profile.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=self.test_conn_rec),
        ):
            oob_mgr_fetch_conn.return_value = ConnectionTarget(
                did=TestConfig.test_did,
                endpoint=TestConfig.test_endpoint,
                recipient_keys=[TestConfig.test_verkey],
                sender_key=TestConfig.test_verkey,
            )

            invitation = InvitationMessage()
            oob_record = OobRecord(
                invitation=invitation,
                invi_msg_id=invitation._id,
                role=OobRecord.ROLE_RECEIVER,
                connection_id=self.test_conn_rec.connection_id,
                state=OobRecord.STATE_INITIAL,
            )

            oob_record = await self.manager._create_handshake_reuse_message(
                oob_record, self.test_conn_rec, get_version_from_message(invitation)
            )

            _, kwargs = self.responder.send.call_args
            reuse_message: HandshakeReuse = kwargs.get("message")

            assert oob_record.state == OobRecord.STATE_AWAIT_RESPONSE

            # Assert responder has been called with the reuse message
            assert reuse_message._type == DIDCommPrefix.qualify_current(
                "out-of-band/1.1/handshake-reuse"
            )
            assert oob_record.reuse_msg_id == reuse_message._id

    async def test_create_handshake_reuse_msg_catch_exception(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:
            oob_mgr_fetch_conn.side_effect = StorageNotFoundError()
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager._create_handshake_reuse_message(
                    async_mock.MagicMock(), self.test_conn_rec, "1.0"
                )
            assert "Error on creating and sending a handshake reuse message" in str(
                context.exception
            )

    async def test_receive_reuse_message_existing_found(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
        )

        reuse_msg = HandshakeReuse()
        reuse_msg.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160

        with async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            autospec=True,
        ) as mock_retrieve_oob, async_mock.patch.object(
            self.profile, "notify", autospec=True
        ) as mock_notify:
            mock_retrieve_oob.return_value = async_mock.MagicMock(
                emit_event=async_mock.CoroutineMock(),
                delete_record=async_mock.CoroutineMock(),
                multi_use=False,
            )

            await self.manager.receive_reuse_message(
                reuse_msg, receipt, self.test_conn_rec
            )
            mock_notify.assert_called_once_with(
                REUSE_WEBHOOK_TOPIC,
                {
                    "thread_id": "the-thread-id",
                    "connection_id": self.test_conn_rec.connection_id,
                    "comment": "Connection dummy is being reused for invitation the-pthid",
                },
            )

            # delete should be called if multi_use == False
            mock_retrieve_oob.return_value.delete_record.assert_called_once()
            mock_retrieve_oob.return_value.emit_event.assert_called_once()
            self.responder.send.assert_called_once_with(
                message=ANY, target_list=oob_mgr_fetch_conn.return_value
            )

            assert mock_retrieve_oob.return_value.state == OobRecord.STATE_DONE
            assert mock_retrieve_oob.return_value.reuse_msg_id == reuse_msg._thread_id
            assert (
                mock_retrieve_oob.return_value.connection_id
                == self.test_conn_rec.connection_id
            )

    async def test_receive_reuse_message_existing_found_multi_use(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
        )

        reuse_msg = HandshakeReuse(version="1.0")
        reuse_msg.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        self.test_conn_rec.invitation_msg_id = "test_123"
        self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160

        with async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            OobRecord,
            "retrieve_by_tag_filter",
            autospec=True,
        ) as mock_retrieve_oob, async_mock.patch.object(
            self.profile, "notify", autospec=True
        ) as mock_notify:
            mock_retrieve_oob.return_value = async_mock.MagicMock(
                emit_event=async_mock.CoroutineMock(),
                delete_record=async_mock.CoroutineMock(),
                multi_use=True,
            )

            await self.manager.receive_reuse_message(
                reuse_msg, receipt, self.test_conn_rec
            )
            mock_notify.assert_called_once_with(
                REUSE_WEBHOOK_TOPIC,
                {
                    "thread_id": "the-thread-id",
                    "connection_id": self.test_conn_rec.connection_id,
                    "comment": "Connection dummy is being reused for invitation the-pthid",
                },
            )

            # delete should be called if multi_use == False
            mock_retrieve_oob.return_value.delete_record.assert_not_called()
            mock_retrieve_oob.return_value.emit_event.assert_called_once()
            self.responder.send.assert_called_once_with(
                message=ANY, target_list=oob_mgr_fetch_conn.return_value
            )

            assert mock_retrieve_oob.return_value.state == OobRecord.STATE_DONE
            assert mock_retrieve_oob.return_value.reuse_msg_id == reuse_msg._thread_id
            assert (
                mock_retrieve_oob.return_value.connection_id
                == self.test_conn_rec.connection_id
            )

    async def test_receive_reuse_accepted(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg_accepted = HandshakeReuseAccept()
        reuse_msg_accepted.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        with async_mock.patch.object(
            self.profile, "notify", autospec=True
        ) as mock_notify, async_mock.patch.object(
            OobRecord, "retrieve_by_tag_filter", autospec=True
        ) as mock_retrieve_oob:
            mock_retrieve_oob.return_value = async_mock.MagicMock(
                emit_event=async_mock.CoroutineMock(),
                delete_record=async_mock.CoroutineMock(),
            )

            await self.manager.receive_reuse_accepted_message(
                reuse_msg_accepted, receipt, self.test_conn_rec
            )

            mock_retrieve_oob.return_value.emit_event.assert_called_once()
            mock_retrieve_oob.return_value.delete_record.assert_called_once()
            mock_notify.assert_called_once_with(
                REUSE_ACCEPTED_WEBHOOK_TOPIC,
                {
                    "thread_id": "the-thread-id",
                    "connection_id": self.test_conn_rec.connection_id,
                    "state": "accepted",
                    "comment": f"Connection {self.test_conn_rec.connection_id} is being reused for invitation the-pthid",
                },
            )

    async def test_receive_reuse_accepted_x(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg_accepted = HandshakeReuseAccept()
        reuse_msg_accepted.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        with async_mock.patch.object(
            self.profile, "notify", autospec=True
        ) as mock_notify, async_mock.patch.object(
            OobRecord, "retrieve_by_tag_filter", autospec=True
        ) as mock_retrieve_oob:
            mock_retrieve_oob.side_effect = (StorageNotFoundError,)

            with self.assertRaises(test_module.OutOfBandManagerError) as err:
                await self.manager.receive_reuse_accepted_message(
                    reuse_msg_accepted, receipt, self.test_conn_rec
                )
            assert "Error processing reuse accepted message " in err.exception.message

            mock_notify.assert_called_once_with(
                REUSE_ACCEPTED_WEBHOOK_TOPIC,
                {
                    "thread_id": "the-thread-id",
                    "state": "rejected",
                    "connection_id": self.test_conn_rec.connection_id,
                    "comment": f"Unable to process HandshakeReuseAccept message, connection {self.test_conn_rec.connection_id} and invitation the-pthid",
                },
            )

    async def test_receive_problem_report(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            description={
                "en": "test",
                "code": ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
            }
        )
        problem_report.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        with async_mock.patch.object(
            OobRecord, "retrieve_by_tag_filter", autospec=True
        ) as mock_retrieve_oob:
            mock_retrieve_oob.return_value = async_mock.MagicMock(
                emit_event=async_mock.CoroutineMock(),
                delete_record=async_mock.CoroutineMock(),
                save=async_mock.CoroutineMock(),
            )

            await self.manager.receive_problem_report(
                problem_report, receipt, self.test_conn_rec
            )

            mock_retrieve_oob.assert_called_once_with(
                ANY, {"invi_msg_id": "the-pthid", "reuse_msg_id": "the-thread-id"}
            )
            assert mock_retrieve_oob.return_value.state == OobRecord.STATE_NOT_ACCEPTED

    async def test_receive_problem_report_x(self):
        self.profile.context.update_settings({"public_invites": True})

        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            description={
                "en": "test",
                "code": ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
            }
        )
        problem_report.assign_thread_id(thid="the-thread-id", pthid="the-pthid")

        with async_mock.patch.object(
            OobRecord, "retrieve_by_tag_filter", autospec=True
        ) as mock_retrieve_oob:
            mock_retrieve_oob.side_effect = (StorageNotFoundError(),)

            with self.assertRaises(OutOfBandManagerError) as err:
                await self.manager.receive_problem_report(
                    problem_report, receipt, self.test_conn_rec
                )
            assert "Error processing problem report message " in err.exception.message

    async def test_receive_invitation_with_valid_mediation(self):
        mock_conn = async_mock.MagicMock(connection_id="dummy-connection")

        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            mediation_record = MediationRecord(
                role=MediationRecord.ROLE_CLIENT,
                state=MediationRecord.STATE_GRANTED,
                connection_id=self.test_mediator_conn_id,
                routing_keys=self.test_mediator_routing_keys,
                endpoint=self.test_mediator_endpoint,
            )
            await mediation_record.save(session)
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", async_mock.CoroutineMock()
            ) as mock_didx_recv_invi, async_mock.patch.object(
                ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
            ) as mock_retrieve_conn_by_id:
                invite = await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    my_label="test123",
                    hs_protos=[HSProto.RFC23],
                )

                mock_retrieve_conn_by_id.return_value = mock_conn
                mock_didx_recv_invi.return_value = mock_conn
                invi_msg = invite.invitation
                await self.manager.receive_invitation(
                    invitation=invi_msg,
                    mediation_id=mediation_record._id,
                )
                mock_didx_recv_invi.assert_called_once_with(
                    invitation=invi_msg,
                    their_public_did=None,
                    auto_accept=None,
                    alias=None,
                    mediation_id=mediation_record._id,
                )

    async def test_receive_invitation_with_invalid_mediation(self):
        mock_conn = async_mock.MagicMock(connection_id="dummy-connection")

        with async_mock.patch.object(
            DIDXManager,
            "receive_invitation",
            async_mock.CoroutineMock(),
        ) as mock_didx_recv_invi, async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve_conn_by_id:
            invite = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                my_label="test123",
                hs_protos=[HSProto.RFC23],
            )
            mock_didx_recv_invi.return_value = mock_conn
            mock_retrieve_conn_by_id.return_value = mock_conn
            invi_msg = invite.invitation
            self.route_manager.mediation_record_if_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )
            await self.manager.receive_invitation(
                invi_msg,
                mediation_id="test-mediation-id",
            )
            mock_didx_recv_invi.assert_called_once_with(
                invitation=invi_msg,
                their_public_did=None,
                auto_accept=None,
                alias=None,
                mediation_id=None,
            )

    async def test_receive_invitation_didx_services_with_service_block(self):
        self.profile.context.update_settings({"public_invites": True})

        mock_conn = async_mock.MagicMock(connection_id="dummy-connection")

        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve_conn_by_id:
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock(return_value=mock_conn)
            )
            mock_retrieve_conn_by_id.return_value = mock_conn
            oob_invitation = InvitationMessage(
                requests_attach=[],
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[
                    OobService(
                        recipient_keys=["dummy"],
                        routing_keys=[],
                    )
                ],
            )

            await self.manager.receive_invitation(oob_invitation)

    async def test_receive_invitation_connection_protocol(self):
        self.profile.context.update_settings({"public_invites": True})

        mock_conn = async_mock.MagicMock(connection_id="dummy-connection")

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr_cls, async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_retrieve_by_id:
            conn_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock(return_value=mock_conn)
            )
            mock_conn_retrieve_by_id.return_value = mock_conn
            oob_invitation = InvitationMessage(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC160.name) for pfx in DIDCommPrefix
                ],
                label="test",
                _id="test123",
                services=[
                    OobService(
                        recipient_keys=[
                            DIDKey.from_public_key_b58(
                                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC",
                                ED25519,
                            ).did
                        ],
                        routing_keys=[],
                        service_endpoint="http://localhost",
                    )
                ],
                requests_attach=[],
            )
            oob_record = await self.manager.receive_invitation(oob_invitation)
            conn_mgr_cls.return_value.receive_invitation.assert_called_once_with(
                invitation=ANY,
                their_public_did=None,
                auto_accept=None,
                alias=None,
                mediation_id=None,
            )
            _, kwargs = conn_mgr_cls.return_value.receive_invitation.call_args
            invitation = kwargs["invitation"]
            assert isinstance(invitation, ConnectionInvitation)

            assert invitation.endpoint == "http://localhost"
            assert invitation.recipient_keys == [
                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
            ]
            assert not invitation.routing_keys

            assert oob_record.state == "deleted"
            assert oob_record._previous_state == OobRecord.STATE_DONE

    async def test_receive_invitation_services_with_neither_service_blocks_nor_dids(
        self,
    ):
        self.profile.context.update_settings({"public_invites": True})
        oob_invitation = InvitationMessage(
            services=[],
        )
        with self.assertRaises(OutOfBandManagerError) as err:
            await self.manager.receive_invitation(oob_invitation)

        assert "service array must have exactly one element" in err.exception.message

    async def test_receive_invitation_no_hs_protos_no_attach(
        self,
    ):
        self.profile.context.update_settings({"public_invites": True})
        oob_invitation = InvitationMessage(
            services=["did:sov:something"],
        )
        with self.assertRaises(OutOfBandManagerError) as err:
            await self.manager.receive_invitation(oob_invitation)

        assert (
            "Invitation must specify handshake_protocols, requests_attach, or both"
            in err.exception.message
        )

    async def test_existing_conn_record_public_did(self):
        self.profile.context.update_settings({"public_invites": True})

        test_exist_conn = ConnRecord(
            connection_id="connection_id",
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_public_did=TestConfig.test_target_did,
            invitation_msg_id="12345678-0123-4567-1234-567812345678",
            their_role=ConnRecord.Role.REQUESTER,
        )

        with async_mock.patch.object(
            ConnRecord,
            "find_existing_connection",
            async_mock.CoroutineMock(),
        ) as oob_mgr_find_existing_conn, async_mock.patch.object(
            OobRecord, "save", async_mock.CoroutineMock()
        ) as oob_record_save, async_mock.patch.object(
            OobRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as oob_record_retrieve_by_id, async_mock.patch.object(
            OutOfBandManager, "fetch_connection_targets", autospec=True
        ) as oob_mgr_fetch_conn:
            oob_mgr_find_existing_conn.return_value = test_exist_conn
            oob_mgr_fetch_conn.return_value = []
            oob_invitation = InvitationMessage(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_target_did],
                requests_attach=[],
            )

            oob_record_retrieve_by_id.return_value = async_mock.MagicMock(
                state=OobRecord.STATE_ACCEPTED
            )

            result = await self.manager.receive_invitation(
                oob_invitation, use_existing_connection=True
            )

            oob_mgr_find_existing_conn.assert_called_once()
            assert result.state == OobRecord.STATE_ACCEPTED
            oob_record_save.assert_called_once_with(
                ANY, reason="Storing reuse msg data"
            )

    async def test_receive_invitation_handshake_reuse(self):
        self.profile.context.update_settings({"public_invites": True})

        test_exist_conn = ConnRecord(
            connection_id="connection_id",
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_public_did=TestConfig.test_target_did,
            invitation_msg_id="12345678-0123-4567-1234-567812345678",
            their_role=ConnRecord.Role.REQUESTER,
        )

        with async_mock.patch.object(
            test_module.OutOfBandManager,
            "_handle_hanshake_reuse",
            async_mock.CoroutineMock(),
        ) as handle_handshake_reuse, async_mock.patch.object(
            test_module.OutOfBandManager,
            "_perform_handshake",
            async_mock.CoroutineMock(),
        ) as perform_handshake, async_mock.patch.object(
            ConnRecord,
            "find_existing_connection",
            async_mock.CoroutineMock(return_value=test_exist_conn),
        ):
            oob_invitation = InvitationMessage(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_target_did],
                requests_attach=[],
            )

            handle_handshake_reuse.return_value = async_mock.MagicMock(
                state=OobRecord.STATE_ACCEPTED
            )

            result = await self.manager.receive_invitation(
                oob_invitation, use_existing_connection=True
            )

            perform_handshake.assert_not_called()
            handle_handshake_reuse.assert_called_once_with(
                ANY, test_exist_conn, get_version_from_message(oob_invitation)
            )

            assert result.state == OobRecord.STATE_ACCEPTED

    async def test_receive_invitation_handshake_reuse_failed(self):
        self.profile.context.update_settings({"public_invites": True})

        test_exist_conn = ConnRecord(
            connection_id="connection_id",
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_public_did=TestConfig.test_target_did,
            invitation_msg_id="12345678-0123-4567-1234-567812345678",
            their_role=ConnRecord.Role.REQUESTER,
        )

        with async_mock.patch.object(
            test_module.OutOfBandManager,
            "_handle_hanshake_reuse",
            async_mock.CoroutineMock(),
        ) as handle_handshake_reuse, async_mock.patch.object(
            test_module.OutOfBandManager,
            "_perform_handshake",
            async_mock.CoroutineMock(),
        ) as perform_handshake, async_mock.patch.object(
            ConnRecord,
            "find_existing_connection",
            async_mock.CoroutineMock(return_value=test_exist_conn),
        ), async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=test_exist_conn),
        ):
            oob_invitation = InvitationMessage(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_target_did],
                requests_attach=[],
            )

            mock_oob = async_mock.MagicMock(
                delete_record=async_mock.CoroutineMock(),
                emit_event=async_mock.CoroutineMock(),
            )
            perform_handshake.return_value = mock_oob

            handle_handshake_reuse.return_value = async_mock.MagicMock(
                state=OobRecord.STATE_NOT_ACCEPTED
            )

            result = await self.manager.receive_invitation(
                oob_invitation,
                use_existing_connection=True,
                alias="alias",
                auto_accept=True,
                mediation_id="mediation_id",
            )

            handle_handshake_reuse.assert_called_once_with(
                ANY, test_exist_conn, get_version_from_message(oob_invitation)
            )
            perform_handshake.assert_called_once_with(
                oob_record=ANY,
                alias="alias",
                auto_accept=True,
                mediation_id="mediation_id",
                service_accept=None,
            )

            assert mock_oob.state == OobRecord.STATE_DONE
            assert result is mock_oob
            mock_oob.emit_event.assert_called_once()
            mock_oob.delete_record.assert_called_once()

    async def test_receive_invitation_services_with_service_did(self):
        self.profile.context.update_settings({"public_invites": True})

        mock_conn = async_mock.MagicMock(connection_id="dummy")

        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=mock_conn),
        ):
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock(return_value=mock_conn)
            )
            oob_invitation = InvitationMessage(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_did],
                requests_attach=[],
            )

            invitation_record = await self.manager.receive_invitation(oob_invitation)
            assert invitation_record.invitation.services

    async def test_request_attach_oob_message_processor_connectionless(self):
        requests_attach: List[AttachDecorator] = [
            AttachDecorator.deserialize(deepcopy(TestConfig.req_attach_v1))
        ]

        mock_oob_processor = async_mock.MagicMock(
            handle_message=async_mock.CoroutineMock()
        )
        self.profile.context.injector.bind_instance(
            OobMessageProcessor, mock_oob_processor
        )

        mock_service_decorator = ServiceDecorator(
            endpoint=self.test_endpoint, recipient_keys=[self.test_verkey]
        )

        with async_mock.patch.object(
            InMemoryWallet,
            "create_signing_key",
            async_mock.CoroutineMock(),
        ) as mock_create_signing_key, async_mock.patch.object(
            OutOfBandManager,
            "_service_decorator_from_service",
            async_mock.CoroutineMock(),
        ) as mock_service_decorator_from_service:
            mock_create_signing_key.return_value = KeyInfo(
                verkey="a-verkey", metadata={}, key_type=ED25519
            )
            mock_service_decorator_from_service.return_value = mock_service_decorator
            oob_invitation = InvitationMessage(
                handshake_protocols=[],
                services=[self.test_service],
                requests_attach=requests_attach,
            )

            oob_record = await self.manager.receive_invitation(
                oob_invitation, use_existing_connection=True
            )

            assert oob_record.our_recipient_key == "a-verkey"
            assert oob_record.our_service
            assert oob_record.state == OobRecord.STATE_PREPARE_RESPONSE

            mock_create_signing_key.assert_called_once_with(ED25519)
            mock_oob_processor.handle_message.assert_called_once_with(
                self.profile,
                [attachment.content for attachment in requests_attach],
                oob_record=oob_record,
                their_service=mock_service_decorator,
            )

    async def test_request_attach_oob_message_processor_connection(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                connection_id="a-connection-id",
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
                state=ConnRecord.State.COMPLETED.rfc160,
            )

            requests_attach: List[AttachDecorator] = [
                AttachDecorator.deserialize(deepcopy(TestConfig.req_attach_v1))
            ]

            mock_oob_processor = async_mock.MagicMock(
                handle_message=async_mock.CoroutineMock()
            )
            self.profile.context.injector.bind_instance(
                OobMessageProcessor, mock_oob_processor
            )

            with async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_invitation = InvitationMessage(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=requests_attach,
                )

                oob_record = await self.manager.receive_invitation(
                    oob_invitation, use_existing_connection=True
                )

                mock_oob_processor.handle_message.assert_called_once_with(
                    self.profile,
                    [attachment.content for attachment in requests_attach],
                    oob_record=oob_record,
                    their_service=None,
                )

    async def test_request_attach_wait_for_conn_rec_active(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )

            with async_mock.patch.object(
                OutOfBandManager, "_wait_for_conn_rec_active"
            ) as mock_wait_for_conn_rec_active, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                mock_wait_for_conn_rec_active.return_value = None
                oob_invitation = InvitationMessage(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(deepcopy(TestConfig.req_attach_v1))
                    ],
                )

                with self.assertRaises(test_module.OutOfBandManagerError) as err:
                    oob_record = await self.manager.receive_invitation(
                        oob_invitation, use_existing_connection=True
                    )
                assert (
                    "Connection not ready to process attach message for connection_id:"
                    in err.exception.message
                )

    async def test_service_decorator_from_service_did(self):
        did = "did:sov:something"

        self.manager.resolve_invitation = async_mock.CoroutineMock()
        self.manager.resolve_invitation.return_value = (
            TestConfig.test_endpoint,
            [TestConfig.test_verkey],
            self.test_mediator_routing_keys,
        )

        service = await self.manager._service_decorator_from_service(did)

        assert service.endpoint == TestConfig.test_endpoint
        assert service.recipient_keys == [TestConfig.test_verkey]
        assert service.routing_keys == self.test_mediator_routing_keys

    async def test_service_decorator_from_service_object(self):
        oob_service = OobService(
            service_endpoint=TestConfig.test_endpoint,
            recipient_keys=[
                DIDKey.from_public_key_b58(TestConfig.test_verkey, ED25519).did
            ],
            routing_keys=[
                DIDKey.from_public_key_b58(verkey, ED25519).did
                for verkey in self.test_mediator_routing_keys
            ],
        )
        service = await self.manager._service_decorator_from_service(oob_service)

        assert service.endpoint == TestConfig.test_endpoint
        assert service.recipient_keys == [TestConfig.test_verkey]
        assert service.routing_keys == self.test_mediator_routing_keys

    async def test_delete_stale_connection_by_invitation(self):
        current_datetime = datetime_now()
        older_datetime = current_datetime - timedelta(hours=4)
        records = [
            ConnRecord(
                my_did=self.test_did,
                their_did="FBmi5JLf5g58kDnNXMy4QM",
                their_role=ConnRecord.Role.RESPONDER.rfc160,
                state=ConnRecord.State.INVITATION.rfc160,
                invitation_key="dummy2",
                invitation_mode="once",
                invitation_msg_id="test123",
                updated_at=datetime_to_str(older_datetime),
            )
        ]
        with async_mock.patch.object(
            ConnRecord, "query", async_mock.CoroutineMock()
        ) as mock_connrecord_query, async_mock.patch.object(
            ConnRecord, "delete_record", async_mock.CoroutineMock()
        ) as mock_connrecord_delete:
            mock_connrecord_query.return_value = records
            await self.manager.delete_stale_connection_by_invitation("test123")
            mock_connrecord_delete.assert_called_once()
