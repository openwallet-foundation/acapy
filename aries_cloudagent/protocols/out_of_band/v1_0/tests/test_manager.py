"""Test OOB Manager."""

import asyncio
import json

from asynctest import mock as async_mock, TestCase as AsyncTestCase
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import UUID

from .....connections.models.conn_record import ConnRecord
from .....connections.models.connection_target import ConnectionTarget
from .....connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .....core.in_memory import InMemoryProfile
from .....core.profile import ProfileSession
from .....did.did_key import DIDKey
from .....indy.holder import IndyHolder
from .....indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
)
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.responder import BaseResponder, MockResponder
from .....messaging.util import str_to_epoch, datetime_now, datetime_to_str
from .....multitenant.base import BaseMultitenantManager
from .....multitenant.manager import MultitenantManager
from .....protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from .....protocols.coordinate_mediation.v1_0.manager import MediationManager
from .....protocols.didexchange.v1_0.manager import DIDXManager
from .....protocols.issue_credential.v1_0.manager import (
    CredentialManager as V10CredManager,
)
from .....protocols.issue_credential.v1_0.messages.credential_offer import (
    CredentialOffer as V10CredOffer,
)
from .....protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredentialPreview as V10CredentialPreview,
    CredAttrSpec as V10CredAttrSpec,
)
from .....protocols.issue_credential.v1_0.tests import (
    INDY_OFFER,
    INDY_CRED_REQ,
)
from .....protocols.issue_credential.v2_0.manager import V20CredManager
from .....protocols.issue_credential.v2_0.messages.cred_format import V20CredFormat
from .....protocols.issue_credential.v2_0.messages.inner.cred_preview import (
    V20CredPreview,
    V20CredAttrSpec,
)
from .....protocols.issue_credential.v2_0.messages.cred_offer import V20CredOffer
from .....protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from .....protocols.issue_credential.v2_0.message_types import (
    ATTACHMENT_FORMAT as V20_CRED_ATTACH_FORMAT,
    CRED_20_OFFER,
)
from .....protocols.present_proof.v1_0.manager import PresentationManager
from .....protocols.present_proof.v1_0.message_types import (
    PRESENTATION_REQUEST,
    ATTACH_DECO_IDS as V10_PRES_ATTACH_FORMAT,
)
from .....protocols.present_proof.v1_0.messages.presentation import Presentation
from .....protocols.present_proof.v1_0.messages.presentation_request import (
    PresentationRequest,
)
from .....protocols.present_proof.v1_0.models.presentation_exchange import (
    V10PresentationExchange,
)
from .....protocols.present_proof.v2_0.manager import V20PresManager
from .....protocols.present_proof.v2_0.message_types import (
    ATTACHMENT_FORMAT as V20_PRES_ATTACH_FORMAT,
    PRES_20,
    PRES_20_REQUEST,
)
from .....protocols.present_proof.v2_0.messages.pres import V20Pres
from .....protocols.present_proof.v2_0.messages.pres_format import V20PresFormat
from .....protocols.present_proof.v2_0.messages.pres_request import V20PresRequest
from .....storage.error import StorageNotFoundError
from .....storage.vc_holder.base import VCHolder
from .....storage.vc_holder.vc_record import VCRecord
from .....transport.inbound.receipt import MessageReceipt
from .....wallet.did_info import DIDInfo, KeyInfo
from .....wallet.did_method import DIDMethod
from .....wallet.in_memory import InMemoryWallet
from .....wallet.key_type import KeyType

from ....didcomm_prefix import DIDCommPrefix
from ....issue_credential.v1_0.models.credential_exchange import V10CredentialExchange

from .. import manager as test_module
from ..manager import (
    OutOfBandManager,
    OutOfBandManagerError,
)
from ..message_types import INVITATION
from ..messages.invitation import HSProto, InvitationMessage
from ..messages.reuse import HandshakeReuse
from ..messages.reuse_accept import HandshakeReuseAccept
from ..messages.problem_report import ProblemReport, ProblemReportReason
from ..models.invitation import InvitationRecord


class TestConfig:

    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"
    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    their_public_did = "55GkHamhTU1ZbTbV2ab9DE"
    NOW_8601 = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
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

    PRES_PREVIEW = IndyPresPreview(
        attributes=[
            IndyPresAttrSpec(name="player", cred_def_id=CD_ID, value="Richie Knucklez"),
            IndyPresAttrSpec(
                name="screenCapture",
                cred_def_id=CD_ID,
                mime_type="image/png",
                value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
            ),
        ],
        predicates=[
            IndyPresPredSpec(
                name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
            )
        ],
    )

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

        self.profile = InMemoryProfile.test_profile(
            {
                "default_endpoint": TestConfig.test_endpoint,
                "default_label": "This guy",
                "additional_endpoints": ["http://aries.ca/another-endpoint"],
                "debug.auto_accept_invites": True,
                "debug.auto_accept_requests": True,
            }
        )

        self.profile.context.injector.bind_instance(BaseResponder, self.responder)
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

        self.test_conn_rec = ConnRecord(
            my_did=TestConfig.test_did,
            their_did=TestConfig.test_target_did,
            their_role=None,
            state=ConnRecord.State.COMPLETED,
            their_public_did=self.their_public_did,
        )

        self.test_mediator_routing_keys = [
            "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRR"
        ]
        self.test_mediator_conn_id = "mediator-conn-id"
        self.test_mediator_endpoint = "http://mediator.example.com"

    async def test_create_invitation_handshake_succeeds(self):
        self.profile.context.update_settings({"public_invites": True})

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                TestConfig.test_did,
                TestConfig.test_verkey,
                None,
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=True,
                hs_protos=[HSProto.RFC23],
            )

            assert invi_rec._invitation.ser["@type"] == DIDCommPrefix.qualify_current(
                INVITATION
            )
            assert not invi_rec._invitation.ser.get("requests~attach")
            assert (
                DIDCommPrefix.qualify_current(HSProto.RFC23.name)
                in invi_rec.invitation.handshake_protocols
            )
            assert invi_rec._invitation.ser["services"] == [
                f"did:sov:{TestConfig.test_did}"
            ]

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
                assert invite._invitation.ser["@type"] == DIDCommPrefix.qualify_current(
                    INVITATION
                )
                assert invite.invitation.label == "test123"
                mock_get_default_mediator.assert_not_called()

    async def test_create_invitation_multitenant_local(self):
        self.profile.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
            }
        )

        self.multitenant_mgr.add_key = async_mock.CoroutineMock()

        with async_mock.patch.object(
            InMemoryWallet, "create_signing_key", autospec=True
        ) as mock_wallet_create_signing_key, async_mock.patch.object(
            self.multitenant_mgr, "get_default_mediator"
        ) as mock_get_default_mediator:
            mock_wallet_create_signing_key.return_value = KeyInfo(
                TestConfig.test_verkey, None, KeyType.ED25519
            )
            mock_get_default_mediator.return_value = MediationRecord()
            await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                hs_protos=[HSProto.RFC23],
                multi_use=False,
            )

            self.multitenant_mgr.add_key.assert_called_once_with(
                "test_wallet", TestConfig.test_verkey
            )

    async def test_create_invitation_multitenant_public(self):
        self.profile.context.update_settings(
            {
                "multitenant.enabled": True,
                "wallet.id": "test_wallet",
                "public_invites": True,
            }
        )

        self.multitenant_mgr.add_key = async_mock.CoroutineMock()

        with async_mock.patch.object(
            InMemoryWallet, "get_public_did", autospec=True
        ) as mock_wallet_get_public_did:
            mock_wallet_get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None,
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
            )
            await self.manager.create_invitation(
                hs_protos=[HSProto.RFC23],
                public=True,
                multi_use=False,
            )

            self.multitenant_mgr.add_key.assert_called_once_with(
                "test_wallet", TestConfig.test_verkey, skip_if_exists=True
            )

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
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

            assert isinstance(invi_rec, InvitationRecord)

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
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

            assert isinstance(invi_rec, InvitationRecord)
            assert not invi_rec._invitation.ser["handshake_protocols"]

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
            )
            mock_retrieve_cxid_v1.side_effect = test_module.StorageNotFoundError()
            mock_retrieve_cxid_v2.return_value = async_mock.MagicMock(
                cred_offer=async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value=json.dumps({"cred": "offer"})
                    )
                )
            )
            invi_rec = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                public=False,
                hs_protos=None,
                multi_use=False,
                attachments=[{"type": "credential-offer", "id": "dummy-id"}],
            )

            assert invi_rec._invitation.ser["requests~attach"]

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
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

            assert invi_rec._invitation.ser["requests~attach"]
            mock_retrieve_pxid.assert_called_once()
            assert isinstance(mock_retrieve_pxid.call_args[0][0], ProfileSession)
            assert mock_retrieve_pxid.call_args[0][1] == "dummy-id"

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
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

            assert invi_rec._invitation.ser["requests~attach"]
            mock_retrieve_pxid_1.assert_called_once()
            assert isinstance(mock_retrieve_pxid_1.call_args[0][0], ProfileSession)
            assert mock_retrieve_pxid_1.call_args[0][1] == "dummy-id"
            mock_retrieve_pxid_2.assert_called_once()
            assert isinstance(mock_retrieve_pxid_2.call_args[0][0], ProfileSession)
            assert mock_retrieve_pxid_2.call_args[0][1] == "dummy-id"

    async def test_dif_req_v2_attach_pres_existing_conn_auto_present_pres_msg_with_challenge(
        self,
    ):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            dif_proof_req = deepcopy(TestConfig.DIF_PROOF_REQ)
            dif_proof_req["options"] = {}
            dif_proof_req["options"][
                "challenge"
            ] = "3fa85f64-5717-4562-b3fc-2c963f66afa7"
            dif_pres_req_v2 = V20PresRequest(
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
                    AttachDecorator.data_json(mapping=dif_proof_req, ident="dif")
                ],
            )

            px2_rec = test_module.V20PresExRecord(
                auto_present=True,
                pres_request=dif_pres_req_v2.serialize(),
            )

            dif_req_attach_v2 = AttachDecorator.data_json(
                mapping=dif_pres_req_v2.serialize(),
                ident="request-0",
            ).serialize()

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20PresManager,
                "receive_pres_request",
                autospec=True,
            ) as pres_mgr_receive_pres_req, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20PresManager,
                "create_pres",
                autospec=True,
            ) as pres_mgr_create_pres:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_pres_req.return_value = px2_rec
                pres_mgr_create_pres.return_value = (
                    px2_rec,
                    V20Pres(
                        formats=[
                            V20PresFormat(
                                attach_id="dif",
                                format_=V20_PRES_ATTACH_FORMAT[PRES_20][
                                    V20PresFormat.Format.DIF.api
                                ],
                            )
                        ],
                        presentations_attach=[
                            AttachDecorator.data_json(
                                mapping={"bogus": "proof"},
                                ident="dif",
                            )
                        ],
                    ),
                )
                self.profile.context.injector.bind_instance(
                    VCHolder,
                    async_mock.MagicMock(
                        search_credentials=async_mock.MagicMock(
                            return_value=async_mock.MagicMock(
                                fetch=async_mock.CoroutineMock(
                                    return_value=[
                                        VCRecord(
                                            contexts=[
                                                "https://www.w3.org/2018/credentials/v1",
                                                "https://www.w3.org/2018/credentials/examples/v1",
                                            ],
                                            expanded_types=[
                                                "https://www.w3.org/2018/credentials#VerifiableCredential",
                                                "https://example.org/examples#UniversityDegreeCredential",
                                            ],
                                            issuer_id="https://example.edu/issuers/565049",
                                            subject_ids=[
                                                "did:example:ebfeb1f712ebc6f1c276e12ec21"
                                            ],
                                            proof_types=["Ed25519Signature2018"],
                                            schema_ids=[
                                                "https://example.org/examples/degree.json"
                                            ],
                                            cred_value={"...": "..."},
                                            given_id="http://example.edu/credentials/3732",
                                            cred_tags={"some": "tag"},
                                        )
                                    ]
                                )
                            )
                        )
                    ),
                )
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(dif_req_attach_v2)],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

    async def test_dif_req_v2_attach_pres_existing_conn_auto_present_pres_msg_with_nonce(
        self,
    ):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            dif_proof_req = deepcopy(TestConfig.DIF_PROOF_REQ)
            dif_proof_req["options"] = {}
            dif_proof_req["options"]["nonce"] = "12345"
            dif_pres_req_v2 = V20PresRequest(
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
                    AttachDecorator.data_json(mapping=dif_proof_req, ident="dif")
                ],
            )

            px2_rec = test_module.V20PresExRecord(
                auto_present=True,
                pres_request=dif_pres_req_v2.serialize(),
            )

            dif_req_attach_v2 = AttachDecorator.data_json(
                mapping=dif_pres_req_v2.serialize(),
                ident="request-0",
            ).serialize()

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20PresManager,
                "receive_pres_request",
                autospec=True,
            ) as pres_mgr_receive_pres_req, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20PresManager,
                "create_pres",
                autospec=True,
            ) as pres_mgr_create_pres:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_pres_req.return_value = px2_rec
                pres_mgr_create_pres.return_value = (
                    px2_rec,
                    V20Pres(
                        formats=[
                            V20PresFormat(
                                attach_id="dif",
                                format_=V20_PRES_ATTACH_FORMAT[PRES_20][
                                    V20PresFormat.Format.DIF.api
                                ],
                            )
                        ],
                        presentations_attach=[
                            AttachDecorator.data_json(
                                mapping={"bogus": "proof"},
                                ident="dif",
                            )
                        ],
                    ),
                )
                self.profile.context.injector.bind_instance(
                    VCHolder,
                    async_mock.MagicMock(
                        search_credentials=async_mock.MagicMock(
                            return_value=async_mock.MagicMock(
                                fetch=async_mock.CoroutineMock(
                                    return_value=[
                                        VCRecord(
                                            contexts=[
                                                "https://www.w3.org/2018/credentials/v1",
                                                "https://www.w3.org/2018/credentials/examples/v1",
                                            ],
                                            expanded_types=[
                                                "https://www.w3.org/2018/credentials#VerifiableCredential",
                                                "https://example.org/examples#UniversityDegreeCredential",
                                            ],
                                            issuer_id="https://example.edu/issuers/565049",
                                            subject_ids=[
                                                "did:example:ebfeb1f712ebc6f1c276e12ec21"
                                            ],
                                            proof_types=["Ed25519Signature2018"],
                                            schema_ids=[
                                                "https://example.org/examples/degree.json"
                                            ],
                                            cred_value={"...": "..."},
                                            given_id="http://example.edu/credentials/3732",
                                            cred_tags={"some": "tag"},
                                        )
                                    ]
                                )
                            )
                        )
                    ),
                )
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(dif_req_attach_v2)],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    public=False,
                    hs_protos=[test_module.HSProto.RFC23],
                    multi_use=True,
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
                )

                assert invi_rec._invitation.ser[
                    "@type"
                ] == DIDCommPrefix.qualify_current(INVITATION)
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
                        self.test_mediator_routing_keys[0], KeyType.ED25519
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
                method=DIDMethod.SOV,
                key_type=KeyType.ED25519,
            )
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.create_invitation(
                    public=True,
                    hs_protos=[test_module.HSProto.RFC23],
                    metadata={"hello": "world"},
                    multi_use=False,
                )
            assert "Cannot store metadata on public" in str(context.exception)

    async def test_receive_invitation_with_valid_mediation(self):
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
            ) as mock_didx_recv_invi:
                invite = await self.manager.create_invitation(
                    my_endpoint=TestConfig.test_endpoint,
                    my_label="test123",
                    hs_protos=[HSProto.RFC23],
                )
                invi_msg = invite.invitation
                invitee_record = await self.manager.receive_invitation(
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
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            DIDXManager,
            "receive_invitation",
            async_mock.CoroutineMock(),
        ) as mock_didx_recv_invi:
            invite = await self.manager.create_invitation(
                my_endpoint=TestConfig.test_endpoint,
                my_label="test123",
                hs_protos=[HSProto.RFC23],
            )
            invi_msg = invite.invitation
            invitee_record = await self.manager.receive_invitation(
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
        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls:
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                requests_attach=[],
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[
                    async_mock.MagicMock(
                        recipient_keys=["dummy"],
                        routing_keys=[],
                    )
                ],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi

            await self.manager.receive_invitation(mock_oob_invi)

    async def test_receive_invitation_connection_mock(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr_cls, async_mock.patch.object(
            test_module,
            "InvitationMessage",
            autospec=True,
        ) as invi_msg_cls, async_mock.patch.object(
            self.manager,
            "receive_invitation",
            async_mock.CoroutineMock(),
        ) as mock_receive_invitation:
            mock_receive_invitation.return_value = self.test_conn_rec.serialize()
            conn_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC160.name) for pfx in DIDCommPrefix
                ],
                label="test",
                _id="test123",
                services=[
                    async_mock.MagicMock(
                        recipient_keys=[
                            DIDKey.from_public_key_b58(
                                "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC",
                                KeyType.ED25519,
                            ).did
                        ],
                        routing_keys=[],
                        service_endpoint="http://localhost",
                    )
                ],
                requests_attach=[],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi
            result = await self.manager.receive_invitation(mock_oob_invi)
            assert result == self.test_conn_rec.serialize()

    async def test_receive_invitation_connection(self):
        self.profile.context.update_settings({"public_invites": True})
        oob_invi_rec = await self.manager.create_invitation(
            auto_accept=True,
            public=False,
            hs_protos=[test_module.HSProto.RFC160],
            multi_use=False,
        )

        result = await self.manager.receive_invitation(
            invitation=oob_invi_rec.invitation,
            use_existing_connection=True,
            auto_accept=True,
        )
        connection_id = UUID(result.connection_id, version=4)
        assert (
            connection_id.hex == result.connection_id.replace("-", "")
            and len(result.connection_id) > 5
        )

    async def test_receive_invitation_services_with_neither_service_blocks_nor_dids(
        self,
    ):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "InvitationMessage", async_mock.MagicMock()
        ) as invi_msg_cls:
            mock_invi_msg = async_mock.MagicMock(
                services=[],
            )
            invi_msg_cls.deserialize.return_value = mock_invi_msg
            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(mock_invi_msg)

    async def test_receive_invitation_services_with_service_did(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as didx_mgr_cls, async_mock.patch.object(
            test_module, "InvitationMessage", autospec=True
        ) as invi_msg_cls:
            didx_mgr_cls.return_value = async_mock.MagicMock(
                receive_invitation=async_mock.CoroutineMock()
            )
            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_did],
                requests_attach=[],
            )
            invi_msg_cls.deserialize.return_value = mock_oob_invi

            invi_rec = await self.manager.receive_invitation(mock_oob_invi)
            assert invi_rec._invitation.ser["services"]

    async def test_receive_invitation_attachment_x(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:

            mock_oob_invi = async_mock.MagicMock(
                services=[TestConfig.test_did],
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                requests_attach=[{"having": "attachment", "is": "no", "good": "here"}],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.receive_invitation(mock_oob_invi)
            assert "requests~attach is not properly formatted" in str(context.exception)

    async def test_receive_invitation_req_pres_v1_0_attachment_x(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:
            mock_oob_invi = async_mock.MagicMock(
                handshake_protocols=[
                    pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                ],
                services=[TestConfig.test_did],
                requests_attach=[
                    async_mock.MagicMock(
                        data=async_mock.MagicMock(
                            json={
                                "@type": DIDCommPrefix.qualify_current(
                                    PRESENTATION_REQUEST
                                )
                            }
                        )
                    ),
                ],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError) as context:
                result = await self.manager.receive_invitation(mock_oob_invi)
                connection_id = UUID(result.connection_id, version=4)
                assert (
                    connection_id.hex == result.connection_id
                    and len(result.connection_id) > 5
                )
            assert "requests~attach is not properly formatted" in str(context.exception)

    async def test_receive_invitation_invalid_request_type_x(self):
        self.profile.context.update_settings({"public_invites": True})
        with async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls:

            mock_oob_invi = async_mock.MagicMock(
                services=[TestConfig.test_did],
                handshake_protocols=[],
                requests_attach=[],
            )
            inv_message_cls.deserialize.return_value = mock_oob_invi

            with self.assertRaises(OutOfBandManagerError):
                await self.manager.receive_invitation(mock_oob_invi)

    async def test_find_existing_connection(self):
        async with self.profile.session() as session:
            test_conn_rec = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_role=None,
                state=ConnRecord.State.COMPLETED,
                their_public_did=self.their_public_did,
            )
            await test_conn_rec.save(session)
            conn_record = await ConnRecord.find_existing_connection(
                session=session, their_public_did="not_addded"
            )
            assert conn_record == None

            conn_record = await ConnRecord.find_existing_connection(
                session=session, their_public_did=self.their_public_did
            )
            assert conn_record == test_conn_rec
            await test_conn_rec.delete_record(session)

    async def test_check_reuse_msg_state(self):
        async with self.profile.session() as session:
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(
                session, "reuse_msg_state", "accepted"
            )
            assert await self.manager.check_reuse_msg_state(self.test_conn_rec) is None

    async def test_create_handshake_reuse_msg(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            await self.test_conn_rec.save(session)
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn:
                oob_mgr_fetch_conn.return_value = ConnectionTarget(
                    did=TestConfig.test_did,
                    endpoint=TestConfig.test_endpoint,
                    recipient_keys=TestConfig.test_verkey,
                    sender_key=TestConfig.test_verkey,
                )
                oob_invi = InvitationMessage()

                await self.manager.create_handshake_reuse_message(
                    oob_invi, self.test_conn_rec
                )
                assert (
                    len(await self.test_conn_rec.metadata_get(session, "reuse_msg_id"))
                    > 6
                )
                assert (
                    await self.test_conn_rec.metadata_get(session, "reuse_msg_state")
                    == "initial"
                )

    async def test_create_handshake_reuse_msg_catch_exception(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            await self.test_conn_rec.save(session)
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn:
                oob_mgr_fetch_conn.side_effect = StorageNotFoundError()
                oob_invi = InvitationMessage()
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.create_handshake_reuse_message(
                        oob_invi, self.test_conn_rec
                    )
                assert "Error on creating and sending a handshake reuse message" in str(
                    context.exception
                )

    async def test_receive_reuse_message_existing_found(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
            )
            reuse_msg = HandshakeReuse()
            reuse_msg.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                InvitationRecord,
                "retrieve_by_tag_filter",
                autospec=True,
            ) as retrieve_invi_rec, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:
                oob_mgr_find_existing_conn.return_value = self.test_conn_rec
                oob_mgr_fetch_conn.return_value = ConnectionTarget(
                    did=TestConfig.test_did,
                    endpoint=TestConfig.test_endpoint,
                    recipient_keys=TestConfig.test_verkey,
                    sender_key=TestConfig.test_verkey,
                )
                oob_invi = InvitationMessage()
                retrieve_invi_rec.return_value = InvitationRecord(
                    invi_msg_id="test_123"
                )
                await self.manager.receive_reuse_message(
                    reuse_msg, receipt, self.test_conn_rec
                )
                mock_notify.assert_called_once()
                assert (
                    len(
                        await ConnRecord.query(
                            session=session,
                            tag_filter={"invitation_msg_id": "test_123"},
                            post_filter_positive={},
                            alt=True,
                        )
                    )
                    == 1
                )

    async def test_receive_reuse_message_existing_not_found(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            reuse_msg = HandshakeReuse()
            reuse_msg.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.REQUEST.rfc160
            await self.test_conn_rec.save(session)
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                InvitationRecord,
                "retrieve_by_tag_filter",
                autospec=True,
            ) as retrieve_invi_rec, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:
                oob_mgr_find_existing_conn.return_value = None
                oob_mgr_fetch_conn.return_value = ConnectionTarget(
                    did=TestConfig.test_did,
                    endpoint=TestConfig.test_endpoint,
                    recipient_keys=TestConfig.test_verkey,
                    sender_key=TestConfig.test_verkey,
                )
                oob_invi = InvitationMessage()
                retrieve_invi_rec.return_value = InvitationRecord(
                    invi_msg_id="test_123"
                )
                await self.manager.receive_reuse_message(
                    reuse_msg, receipt, self.test_conn_rec
                )
                mock_notify.assert_called_once()
                assert len(self.responder.messages) == 0

    async def test_receive_reuse_message_problem_report_logic(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            reuse_msg = HandshakeReuse()
            reuse_msg.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_456"
            self.test_conn_rec.their_did = "test_did"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            with async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:
                oob_mgr_fetch_conn.return_value = ConnectionTarget(
                    did=TestConfig.test_did,
                    endpoint=TestConfig.test_endpoint,
                    recipient_keys=TestConfig.test_verkey,
                    sender_key=TestConfig.test_verkey,
                )
                await self.manager.receive_reuse_message(
                    reuse_msg, receipt, self.test_conn_rec
                )
                mock_notify.assert_called_once()

    async def test_receive_reuse_accepted(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            reuse_msg_accepted = HandshakeReuseAccept()
            reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(session, "reuse_msg_id", "test_123")
            await self.test_conn_rec.metadata_set(session, "reuse_msg_state", "initial")
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:

                await self.manager.receive_reuse_accepted_message(
                    reuse_msg_accepted, receipt, self.test_conn_rec
                )
                mock_notify.assert_called_once()
                assert (
                    await self.test_conn_rec.metadata_get(session, "reuse_msg_state")
                    == "accepted"
                )

    async def test_receive_reuse_accepted(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            reuse_msg_accepted = HandshakeReuseAccept()
            reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(session, "reuse_msg_id", "test_123")
            await self.test_conn_rec.metadata_set(session, "reuse_msg_state", "initial")
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:

                await self.manager.receive_reuse_accepted_message(
                    reuse_msg_accepted, receipt, self.test_conn_rec
                )
                mock_notify.assert_called_once()
                assert (
                    await self.test_conn_rec.metadata_get(session, "reuse_msg_state")
                    == "accepted"
                )

    async def test_receive_reuse_accepted_invalid_conn(self):
        self.profile.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        reuse_msg_accepted = HandshakeReuseAccept()
        reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
        test_invalid_conn = ConnRecord(
            my_did="Test",
            their_did="Test",
            invitation_msg_id="test_456",
            connection_id="12345678-0123-4567-1234-567812345678",
        )
        with async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn, async_mock.patch.object(
            self.profile, "notify", autospec=True
        ) as mock_notify:
            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.receive_reuse_accepted_message(
                    reuse_msg_accepted, receipt, test_invalid_conn
                )
            mock_notify.assert_called_once()
            assert "Error processing reuse accepted message" in str(context.exception)

    async def test_receive_reuse_accepted_message_catch_exception(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            reuse_msg_accepted = HandshakeReuseAccept()
            reuse_msg_accepted.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(session, "reuse_msg_id", "test_123")
            await self.test_conn_rec.metadata_set(session, "reuse_msg_state", "initial")

            with async_mock.patch.object(
                self.test_conn_rec,
                "metadata_set",
                async_mock.CoroutineMock(side_effect=StorageNotFoundError),
            ), async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_reuse_accepted_message(
                        reuse_msg_accepted, receipt, self.test_conn_rec
                    )
                mock_notify.assert_called_once()
                assert "Error processing reuse accepted message" in str(
                    context.exception
                )

    async def test_problem_report_received_not_active(self):
        async with self.profile.session() as session:
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
            problem_report.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(session, "reuse_msg_id", "test_123")
            await self.test_conn_rec.metadata_set(session, "reuse_msg_state", "initial")
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn:

                await self.manager.receive_problem_report(
                    problem_report, receipt, self.test_conn_rec
                )
                assert (
                    await self.test_conn_rec.metadata_get(session, "reuse_msg_state")
                    == "not_accepted"
                )

    async def test_problem_report_received_not_exists(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did="test_did",
            )
            problem_report = ProblemReport(
                description={
                    "en": "test",
                    "code": ProblemReportReason.NO_EXISTING_CONNECTION.value,
                }
            )
            problem_report.assign_thread_id(thid="test_123", pthid="test_123")
            self.test_conn_rec.invitation_msg_id = "test_123"
            self.test_conn_rec.state = ConnRecord.State.COMPLETED.rfc160
            await self.test_conn_rec.save(session)
            await self.test_conn_rec.metadata_set(session, "reuse_msg_id", "test_123")
            await self.test_conn_rec.metadata_set(session, "reuse_msg_state", "initial")
            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn:

                await self.manager.receive_problem_report(
                    problem_report, receipt, self.test_conn_rec
                )
                assert (
                    await self.test_conn_rec.metadata_get(session, "reuse_msg_state")
                    == "not_accepted"
                )

    async def test_problem_report_received_invalid_conn(self):
        self.profile.context.update_settings({"public_invites": True})
        receipt = MessageReceipt(
            recipient_did=TestConfig.test_did,
            recipient_did_public=False,
            sender_did="test_did",
        )
        problem_report = ProblemReport(
            description={
                "en": "test",
                "code": ProblemReportReason.NO_EXISTING_CONNECTION.value,
            }
        )
        problem_report.assign_thread_id(thid="test_123", pthid="test_123")
        test_invalid_conn = ConnRecord(
            my_did="Test",
            their_did="Test",
            invitation_msg_id="test_456",
            connection_id="12345678-0123-4567-1234-567812345678",
        )
        with async_mock.patch.object(
            DIDXManager, "receive_invitation", autospec=True
        ) as didx_mgr_receive_invitation, async_mock.patch(
            "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
            autospec=True,
        ) as inv_message_cls, async_mock.patch.object(
            OutOfBandManager,
            "fetch_connection_targets",
            autospec=True,
        ) as oob_mgr_fetch_conn:

            with self.assertRaises(OutOfBandManagerError) as context:
                await self.manager.receive_problem_report(
                    problem_report, receipt, test_invalid_conn
                )
            assert "Error processing problem report message" in str(context.exception)

    async def test_existing_conn_record_public_did(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_mgr_check_reuse_state.return_value = None
                oob_mgr_create_reuse_msg.return_value = None
                oob_mgr_receive_reuse_msg.return_value = None
                oob_mgr_receive_accept_msg.return_value = None
                oob_mgr_receive_problem_report.return_value = None
                await test_exist_conn.metadata_set(
                    session, "reuse_msg_state", "accepted"
                )
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi

                result = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                retrieved_conn_records = await ConnRecord.query(
                    session=session,
                    tag_filter={
                        "invitation_msg_id": "12345678-0123-4567-1234-567812345678"
                    },
                    post_filter_positive={},
                    alt=True,
                )
                assert (
                    await retrieved_conn_records[0].metadata_get(
                        session, "reuse_msg_id"
                    )
                    is None
                )
                assert (
                    await retrieved_conn_records[0].metadata_get(
                        session, "reuse_msg_state"
                    )
                    is None
                )
                assert result.connection_id == retrieved_conn_records[0].connection_id

    async def test_existing_conn_record_public_did_not_accepted(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                their_public_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")

            test_new_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                their_public_did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                invitation_msg_id="12345678-0123-4567-1234-1234545454487",
                their_role=ConnRecord.Role.REQUESTER,
            )

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_mgr_check_reuse_state.return_value = None
                oob_mgr_create_reuse_msg.return_value = None
                oob_mgr_receive_reuse_msg.return_value = None
                oob_mgr_receive_accept_msg.return_value = None
                oob_mgr_receive_problem_report.return_value = None
                await test_exist_conn.metadata_set(
                    session, "reuse_msg_state", "not_accepted"
                )
                didx_mgr_receive_invitation.return_value = test_new_conn
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi

                result = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                retrieved_conn_records = await ConnRecord.query(
                    session=session,
                    tag_filter={
                        "invitation_msg_id": "12345678-0123-4567-1234-567812345678"
                    },
                    post_filter_positive={},
                    alt=True,
                )
                assert (
                    await retrieved_conn_records[0].metadata_get(
                        session, "reuse_msg_state"
                    )
                    == "not_accepted"
                )
                assert result.connection_id != retrieved_conn_records[0].connection_id

    async def test_existing_conn_record_public_did_inverse_cases(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await self.test_conn_rec.save(session)
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                didx_mgr_receive_invitation.return_value = self.test_conn_rec
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi

                result = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=False
                )
                retrieved_conn_records = await ConnRecord.query(
                    session=session,
                    tag_filter={
                        "invitation_msg_id": "12345678-0123-4567-1234-567812345678"
                    },
                    post_filter_positive={},
                    alt=True,
                )
                assert result.connection_id != retrieved_conn_records[0].connection_id

    async def test_existing_conn_record_public_did_timeout(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                self.profile, "notify", autospec=True
            ) as mock_notify:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_mgr_check_reuse_state.side_effect = asyncio.TimeoutError
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi

                result = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                mock_notify.assert_called()
                retrieved_conn_records = await ConnRecord.query(
                    session=session,
                    tag_filter={"their_public_did": TestConfig.test_target_did},
                )
                assert (
                    retrieved_conn_records[0].state == ConnRecord.State.ABANDONED.rfc160
                )

    async def test_existing_conn_record_public_did_timeout_no_handshake_protocol(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        {"having": "attachment", "is": "no", "good": "here"}
                    ],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    result = await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=False
                    )
                assert "No existing connection exists and " in str(context.exception)

    async def test_req_v1_attach_presentation_existing_conn_no_auto_present(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            exchange_rec = V10PresentationExchange()

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                PresentationManager, "receive_request", autospec=True
            ) as pres_mgr_receive_request, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_request.return_value = exchange_rec

                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v1)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                with self.assertRaises(OutOfBandManagerError) as context:
                    result = await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "Configuration sets auto_present false" in str(context.exception)

    async def test_req_v1_attach_presentation_existing_conn_auto_present_pres_msg(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            exchange_rec = V10PresentationExchange()
            exchange_rec.auto_present = True
            exchange_rec.presentation_request = TestConfig.INDY_PROOF_REQ

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                PresentationManager,
                "receive_request",
                autospec=True,
            ) as pres_mgr_receive_request, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                PresentationManager,
                "create_presentation",
                autospec=True,
            ) as pres_mgr_create_presentation:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_request.return_value = exchange_rec
                pres_mgr_create_presentation.return_value = (
                    exchange_rec,
                    Presentation(
                        presentations_attach=[
                            AttachDecorator.data_base64({"bogus": "proof"})
                        ]
                    ),
                )
                holder = async_mock.MagicMock(IndyHolder, autospec=True)
                get_creds = async_mock.CoroutineMock(
                    return_value=(
                        {
                            "cred_info": {"referent": "dummy_reft"},
                            "attrs": {
                                "player": "Richie Knucklez",
                                "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                                "highScore": "1234560",
                            },
                        },
                    )
                )
                holder.get_credentials_for_presentation_request_by_referent = get_creds
                holder.create_credential_request = async_mock.CoroutineMock(
                    return_value=(
                        json.dumps(TestConfig.indy_cred_req),
                        json.dumps(TestConfig.cred_req_meta),
                    )
                )
                self.profile.context.injector.bind_instance(IndyHolder, holder)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v1)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

    async def test_req_v1_attach_pres_catch_value_error(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            exchange_rec = V10PresentationExchange()
            exchange_rec.auto_present = True
            exchange_rec.presentation_request = TestConfig.INDY_PROOF_REQ

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                PresentationManager,
                "receive_request",
                autospec=True,
            ) as pres_mgr_receive_request, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                PresentationManager,
                "create_presentation",
                autospec=True,
            ) as pres_mgr_create_presentation:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_request.return_value = exchange_rec
                pres_mgr_create_presentation.return_value = (
                    exchange_rec,
                    Presentation(comment="this is test"),
                )
                holder = async_mock.MagicMock(IndyHolder, autospec=True)
                get_creds = async_mock.CoroutineMock(return_value=())
                holder.get_credentials_for_presentation_request_by_referent = get_creds
                holder.create_credential_request = async_mock.CoroutineMock(
                    return_value=(
                        json.dumps(TestConfig.indy_cred_req),
                        json.dumps(TestConfig.cred_req_meta),
                    )
                )
                self.profile.context.injector.bind_instance(IndyHolder, holder)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v1)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "Cannot auto-respond" in str(context.exception)

    async def test_req_v2_attach_presentation_existing_conn_no_auto_present(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            px2_rec = test_module.V20PresExRecord()

            with async_mock.patch.object(
                DIDXManager, "receive_invitation", autospec=True
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20PresManager, "receive_pres_request", autospec=True
            ) as pres_mgr_receive_pres_req, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_pres_req.return_value = px2_rec

                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v2)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert (
                    "Configuration set auto_present false: cannot respond automatically to presentation requests"
                    == str(context.exception)
                )

    async def test_req_v2_attach_presentation_existing_conn_auto_present_pres_msg(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            px2_rec = test_module.V20PresExRecord(
                auto_present=True,
                pres_request=TestConfig.PRES_REQ_V2.serialize(),
            )

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20PresManager,
                "receive_pres_request",
                autospec=True,
            ) as pres_mgr_receive_pres_req, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20PresManager,
                "create_pres",
                autospec=True,
            ) as pres_mgr_create_pres:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_pres_req.return_value = px2_rec
                pres_mgr_create_pres.return_value = (
                    px2_rec,
                    V20Pres(
                        formats=[
                            V20PresFormat(
                                attach_id="indy",
                                format_=V20_PRES_ATTACH_FORMAT[PRES_20][
                                    V20PresFormat.Format.INDY.api
                                ],
                            )
                        ],
                        presentations_attach=[
                            AttachDecorator.data_base64(
                                mapping={"bogus": "proof"},
                                ident="indy",
                            )
                        ],
                    ),
                )
                holder = async_mock.MagicMock(IndyHolder, autospec=True)
                get_creds = async_mock.CoroutineMock(
                    return_value=(
                        {
                            "cred_info": {"referent": "dummy_reft"},
                            "attrs": {
                                "player": "Richie Knucklez",
                                "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                                "highScore": "1234560",
                            },
                        },
                    )
                )
                holder.get_credentials_for_presentation_request_by_referent = get_creds
                holder.create_credential_request = async_mock.CoroutineMock(
                    return_value=(
                        json.dumps(TestConfig.indy_cred_req),
                        json.dumps(TestConfig.cred_req_meta),
                    )
                )
                self.profile.context.injector.bind_instance(IndyHolder, holder)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v2)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi

                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

    async def test_req_v2_attach_pres_catch_value_error(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_presentation_request": False}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")
            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )

            px2_rec = test_module.V20PresExRecord(
                auto_present=False,
                pres_request=TestConfig.PRES_REQ_V2.serialize(),
            )

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20PresManager,
                "receive_pres_request",
                autospec=True,
            ) as pres_mgr_receive_pres_req, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20PresManager,
                "create_pres",
                autospec=True,
            ) as pres_mgr_create_pres:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                pres_mgr_receive_pres_req.return_value = px2_rec
                pres_mgr_create_pres.return_value = (
                    px2_rec,
                    V20Pres(
                        formats=[
                            V20PresFormat(
                                attach_id="indy",
                                format_=V20_PRES_ATTACH_FORMAT[PRES_20][
                                    V20PresFormat.Format.INDY.api
                                ],
                            )
                        ],
                        presentations_attach=[
                            AttachDecorator.data_base64(
                                mapping={"bogus": "proof"},
                                ident="indy",
                            )
                        ],
                    ),
                )
                holder = async_mock.MagicMock(IndyHolder, autospec=True)
                get_creds = async_mock.CoroutineMock(return_value=())
                holder.get_credentials_for_presentation_request_by_referent = get_creds
                holder.create_credential_request = async_mock.CoroutineMock(
                    return_value=(
                        json.dumps(TestConfig.indy_cred_req),
                        json.dumps(TestConfig.cred_req_meta),
                    )
                )
                self.profile.context.injector.bind_instance(IndyHolder, holder)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[
                        AttachDecorator.deserialize(TestConfig.req_attach_v2)
                    ],
                )

                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "cannot respond automatically" in str(context.exception)

    async def test_req_attach_cred_offer_v1(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
                state=ConnRecord.State.COMPLETED,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V1.serialize()
            exchange_rec = V10CredentialExchange()
            exchange_rec.credential_offer = TestConfig.CRED_OFFER_V1

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V10CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V10CredManager,
                "create_request",
                autospec=True,
            ) as cred_mgr_request_receive:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_mgr_check_conn_rec_active.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                cred_mgr_request_receive.return_value = (exchange_rec, INDY_CRED_REQ)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

        async def test_req_attach_cred_offer_v1_no_issue(self):
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": False}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
                state=ConnRecord.State.COMPLETED,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V1.serialize()

            exchange_rec = V10CredentialExchange()
            exchange_rec.credential_offer = TestConfig.CRED_OFFER_V1

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V10CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "Configuration sets auto_offer false" in str(context.exception)

    async def test_req_attach_cred_offer_v2(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
                state=ConnRecord.State.COMPLETED,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V2.serialize()

            exchange_rec = V20CredExRecord()
            exchange_rec.cred_offer = TestConfig.CRED_OFFER_V2

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20CredManager,
                "create_request",
                autospec=True,
            ) as cred_mgr_request_receive:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                oob_mgr_check_conn_rec_active.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                cred_mgr_request_receive.return_value = (exchange_rec, INDY_CRED_REQ)
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                assert conn_rec is not None

    async def test_req_attach_cred_offer_v2_no_issue(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": False}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
                state=ConnRecord.State.COMPLETED,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V2.serialize()

            exchange_rec = V20CredExRecord()
            exchange_rec.cred_offer = TestConfig.CRED_OFFER_V2

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "Configuration sets auto_offer false" in str(context.exception)

    async def test_catch_unsupported_request_attach(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": False}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V1.serialize()
            req_attach["data"]["json"]["@type"] = "test"

            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                with self.assertRaises(OutOfBandManagerError) as context:
                    await self.manager.receive_invitation(
                        mock_oob_invi, use_existing_connection=True
                    )
                assert "Unsupported requests~attach type" in str(context.exception)

    async def test_check_conn_rec_active_a(self):
        async with self.profile.session() as session:
            await self.test_conn_rec.save(session)
            conn_rec = await self.manager.conn_rec_is_active(
                self.test_conn_rec.connection_id
            )
            assert conn_rec.connection_id == self.test_conn_rec.connection_id

    async def test_check_conn_rec_active_b(self):
        connection_id = self.test_conn_rec.connection_id
        conn_rec_request = deepcopy(self.test_conn_rec)
        conn_rec_request.state = "request"
        conn_rec_active = deepcopy(self.test_conn_rec)
        conn_rec_active.state = "active"
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            autospec=True,
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = [conn_rec_request, conn_rec_active]
            conn_rec = await self.manager.conn_rec_is_active(connection_id)
            assert conn_rec.state == "active"

    async def test_request_attach_cred_offer_v1_check_conn_rec_active_timeout(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V1.serialize()
            exchange_rec = V20CredExRecord()
            exchange_rec.cred_offer = TestConfig.CRED_OFFER_V1
            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ), async_mock.patch.object(
                V10CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ), async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ), async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ), async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ), async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ), async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ), async_mock.patch.object(
                V10CredManager,
                "create_request",
                autospec=True,
            ) as cred_mgr_request_receive, async_mock.patch.object(
                test_module.LOGGER, "warning", async_mock.MagicMock()
            ) as mock_logger_warning:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                cred_mgr_request_receive.return_value = (exchange_rec, INDY_CRED_REQ)
                oob_mgr_check_conn_rec_active.side_effect = asyncio.TimeoutError
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                mock_logger_warning.assert_called_once()
                assert conn_rec is not None

    async def test_request_attach_cred_offer_v2_check_conn_rec_active_timeout(self):
        async with self.profile.session() as session:
            self.profile.context.update_settings({"public_invites": True})
            self.profile.context.update_settings(
                {"debug.auto_respond_credential_offer": True}
            )
            test_exist_conn = ConnRecord(
                my_did=TestConfig.test_did,
                their_did=TestConfig.test_target_did,
                their_public_did=TestConfig.test_target_did,
                invitation_msg_id="12345678-0123-4567-1234-567812345678",
                their_role=ConnRecord.Role.REQUESTER,
            )
            await test_exist_conn.save(session)
            await test_exist_conn.metadata_set(session, "reuse_msg_state", "initial")
            await test_exist_conn.metadata_set(session, "reuse_msg_id", "test_123")

            receipt = MessageReceipt(
                recipient_did=TestConfig.test_did,
                recipient_did_public=False,
                sender_did=TestConfig.test_target_did,
            )
            req_attach = deepcopy(TestConfig.req_attach_v1)
            del req_attach["data"]["json"]
            req_attach["data"]["json"] = TestConfig.CRED_OFFER_V2.serialize()
            exchange_rec = V20CredExRecord()
            exchange_rec.cred_offer = TestConfig.CRED_OFFER_V2
            with async_mock.patch.object(
                DIDXManager,
                "receive_invitation",
                autospec=True,
            ) as didx_mgr_receive_invitation, async_mock.patch.object(
                V20CredManager,
                "receive_offer",
                autospec=True,
            ) as cred_mgr_offer_receive, async_mock.patch(
                "aries_cloudagent.protocols.out_of_band.v1_0.manager.InvitationMessage",
                autospec=True,
            ) as inv_message_cls, async_mock.patch.object(
                OutOfBandManager,
                "fetch_connection_targets",
                autospec=True,
            ) as oob_mgr_fetch_conn, async_mock.patch.object(
                ConnRecord,
                "find_existing_connection",
                async_mock.CoroutineMock(),
            ) as oob_mgr_find_existing_conn, async_mock.patch.object(
                OutOfBandManager,
                "check_reuse_msg_state",
                autospec=True,
            ) as oob_mgr_check_reuse_state, async_mock.patch.object(
                OutOfBandManager,
                "conn_rec_is_active",
                autospec=True,
            ) as oob_mgr_check_conn_rec_active, async_mock.patch.object(
                OutOfBandManager,
                "create_handshake_reuse_message",
                autospec=True,
            ) as oob_mgr_create_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_message",
                autospec=True,
            ) as oob_mgr_receive_reuse_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_reuse_accepted_message",
                autospec=True,
            ) as oob_mgr_receive_accept_msg, async_mock.patch.object(
                OutOfBandManager,
                "receive_problem_report",
                autospec=True,
            ) as oob_mgr_receive_problem_report, async_mock.patch.object(
                V20CredManager,
                "create_request",
                autospec=True,
            ) as cred_mgr_request_receive, async_mock.patch.object(
                test_module.LOGGER, "warning", async_mock.MagicMock()
            ) as mock_logger_warning:
                oob_mgr_find_existing_conn.return_value = test_exist_conn
                cred_mgr_offer_receive.return_value = exchange_rec
                cred_mgr_request_receive.return_value = (exchange_rec, INDY_CRED_REQ)
                oob_mgr_check_conn_rec_active.side_effect = asyncio.TimeoutError
                mock_oob_invi = async_mock.MagicMock(
                    handshake_protocols=[
                        pfx.qualify(HSProto.RFC23.name) for pfx in DIDCommPrefix
                    ],
                    services=[TestConfig.test_target_did],
                    requests_attach=[AttachDecorator.deserialize(req_attach)],
                )
                inv_message_cls.deserialize.return_value = mock_oob_invi
                conn_rec = await self.manager.receive_invitation(
                    mock_oob_invi, use_existing_connection=True
                )
                mock_logger_warning.assert_called_once()
                assert conn_rec is not None

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
