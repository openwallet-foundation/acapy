from copy import deepcopy
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from marshmallow import ValidationError

from aries_cloudagent.tests import mock

from .......core.in_memory import InMemoryProfile
from .......messaging.decorators.attach_decorator import AttachDecorator
from .......storage.vc_holder.base import VCHolder
from .......storage.vc_holder.vc_record import VCRecord
from .......vc.ld_proofs import DocumentLoader, DocumentVerificationResult
from .......vc.ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    SECURITY_CONTEXT_ED25519_2020_URL,
)
from .......vc.ld_proofs.error import LinkedDataProofException
from .......vc.tests.document_loader import custom_document_loader
from .......vc.vc_ld.manager import VcLdpManager
from .......vc.vc_ld.models.credential import VerifiableCredential
from .......vc.vc_ld.models.options import LDProofVCOptions
from .......wallet.base import BaseWallet
from .......wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ....message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from ....messages.cred_format import V20CredFormat
from ....messages.cred_issue import V20CredIssue
from ....messages.cred_offer import V20CredOffer
from ....messages.cred_proposal import V20CredProposal
from ....messages.cred_request import V20CredRequest
from ....models.cred_ex_record import V20CredExRecord
from ....models.detail.ld_proof import V20CredExRecordLDProof
from ...handler import V20CredFormatError
from .. import handler as test_module
from ..handler import LOGGER
from ..handler import VCDICredFormatHandler

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"

LD_PROOF_VC_DETAIL = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": TEST_DID_KEY,
    },
    "options": {
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    },
}
LD_PROOF_VC_DETAIL_BBS = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": TEST_DID_KEY,
    },
    "options": {
        "proofType": "BbsBlsSignature2020",
        "created": "2019-12-11T03:50:55",
    },
}
LD_PROOF_VC_DETAIL_ED25519_2020 = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": TEST_DID_KEY,
    },
    "options": {
        "proofType": "Ed25519Signature2020",
        "created": "2019-12-11T03:50:55",
    },
}
LD_PROOF_VC = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "credentialSubject": {"test": "key"},
    "issuanceDate": "2021-04-12",
    "issuer": TEST_DID_KEY,
    "proof": {
        "proofPurpose": "assertionMethod",
        "created": "2019-12-11T03:50:55",
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Q6amIrxGiSbM7Ce6DxlfwLCjVcYyclas8fMxaecspXFUcFW9DAAxKzgHx93FWktnlZjM_biitkMgZdStgvivAQ",
    },
}


class TestV20LDProofCredFormatHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.holder = mock.MagicMock()
        self.wallet = mock.MagicMock(BaseWallet, autospec=True)

        self.session = InMemoryProfile.test_session(
            bind={VCHolder: self.holder, BaseWallet: self.wallet}
        )
        self.profile = self.session.profile
        self.context = self.profile.context
        setattr(self.profile, "session", mock.MagicMock(return_value=self.session))

        # Set custom document loader
        self.context.injector.bind_instance(DocumentLoader, custom_document_loader)

        # Set default verkey ID strategy
        self.context.injector.bind_instance(
            BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )

        self.manager = VcLdpManager(self.profile)
        self.context.injector.bind_instance(VcLdpManager, self.manager)
        self.handler = VCDICredFormatHandler(self.profile)

        self.cred_proposal = V20CredProposal(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            filters_attach=[AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")],
        )

        assert self.handler.profile

    async def test_validate_fields(self):
        # Test correct data
        self.handler.validate_fields(CRED_20_PROPOSAL, LD_PROOF_VC_DETAIL)
        self.handler.validate_fields(CRED_20_OFFER, LD_PROOF_VC_DETAIL)
        self.handler.validate_fields(CRED_20_REQUEST, LD_PROOF_VC_DETAIL)
        self.handler.validate_fields(CRED_20_ISSUE, LD_PROOF_VC)

        incorrect_detail = {
            **LD_PROOF_VC_DETAIL,
            "credential": {**LD_PROOF_VC_DETAIL["credential"], "issuanceDate": None},
        }

        # test incorrect proposal
        with self.assertRaises(ValidationError):
            self.handler.validate_fields(CRED_20_PROPOSAL, incorrect_detail)

        # test incorrect offer
        with self.assertRaises(ValidationError):
            self.handler.validate_fields(CRED_20_OFFER, incorrect_detail)

        # test incorrect request
        with self.assertRaises(ValidationError):
            self.handler.validate_fields(CRED_20_REQUEST, incorrect_detail)

        # test incorrect cred
        with self.assertRaises(ValidationError):
            incorrect_cred = LD_PROOF_VC.copy()
            incorrect_cred.pop("issuanceDate")

            self.handler.validate_fields(CRED_20_ISSUE, incorrect_cred)

    async def test_get_ld_proof_detail_record(self):
        cred_ex_id = "dummy"
        details_ld_proof = [
            V20CredExRecordLDProof(
                cred_ex_id=cred_ex_id,
            ),
            V20CredExRecordLDProof(
                cred_ex_id=cred_ex_id,
            ),
        ]
        await details_ld_proof[0].save(self.session)
        await details_ld_proof[1].save(self.session)  # exercise logger warning on get()

        with mock.patch.object(
            LOGGER, "warning", mock.MagicMock()
        ) as mock_warning:
            assert await self.handler.get_detail_record(cred_ex_id) in details_ld_proof
            mock_warning.assert_called_once()

    async def test_create_proposal(self):
        cred_ex_record = mock.MagicMock()

        (cred_format, attachment) = await self.handler.create_proposal(
            cred_ex_record, deepcopy(LD_PROOF_VC_DETAIL)
        )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == LD_PROOF_VC_DETAIL

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_create_proposal_adds_bbs_context(self):
        cred_ex_record = mock.MagicMock()

        (cred_format, attachment) = await self.handler.create_proposal(
            cred_ex_record, deepcopy(LD_PROOF_VC_DETAIL_BBS)
        )

        # assert BBS url added to context
        assert SECURITY_CONTEXT_BBS_URL in attachment.content["credential"]["@context"]

    async def test_create_proposal_adds_ed25519_2020_context(self):
        cred_ex_record = mock.MagicMock()

        (cred_format, attachment) = await self.handler.create_proposal(
            cred_ex_record, deepcopy(LD_PROOF_VC_DETAIL_ED25519_2020)
        )

        # assert ED25519-2020 url added to context
        assert (
            SECURITY_CONTEXT_ED25519_2020_URL
            in attachment.content["credential"]["@context"]
        )

    async def test_receive_proposal(self):
        cred_ex_record = mock.MagicMock()
        cred_proposal_message = mock.MagicMock()

        # Not much to assert. Receive proposal doesn't do anything
        await self.handler.receive_proposal(cred_ex_record, cred_proposal_message)

    async def test_create_offer(self):
        with mock.patch.object(
            VcLdpManager,
            "assert_can_issue_with_id_and_proof_type",
            mock.CoroutineMock(),
        ) as mock_can_issue, patch.object(
            test_module, "get_properties_without_context", return_value=[]
        ):
            (cred_format, attachment) = await self.handler.create_offer(
                self.cred_proposal
            )

            mock_can_issue.assert_called_once_with(
                LD_PROOF_VC_DETAIL["credential"]["issuer"],
                LD_PROOF_VC_DETAIL["options"]["proofType"],
            )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == LD_PROOF_VC_DETAIL

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_create_offer_adds_bbs_context(self):
        cred_proposal = V20CredProposal(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(LD_PROOF_VC_DETAIL_BBS, ident="0")
            ],
        )

        with mock.patch.object(
            VcLdpManager,
            "assert_can_issue_with_id_and_proof_type",
            mock.CoroutineMock(),
        ), patch.object(test_module, "get_properties_without_context", return_value=[]):
            (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

        # assert BBS url added to context
        assert SECURITY_CONTEXT_BBS_URL in attachment.content["credential"]["@context"]

    async def test_create_offer_adds_ed25519_2020_context(self):
        cred_proposal = V20CredProposal(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(LD_PROOF_VC_DETAIL_ED25519_2020, ident="0")
            ],
        )

        with mock.patch.object(
            VcLdpManager,
            "assert_can_issue_with_id_and_proof_type",
            mock.CoroutineMock(),
        ), patch.object(test_module, "get_properties_without_context", return_value=[]):
            (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

        # assert BBS url added to context
        assert (
            SECURITY_CONTEXT_ED25519_2020_URL
            in attachment.content["credential"]["@context"]
        )

    async def test_create_offer_x_no_proposal(self):
        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.create_offer(None)
        assert "Cannot create linked data proof offer without proposal data" in str(
            context.exception
        )

    async def test_create_offer_x_wrong_attributes(self):
        missing_properties = ["foo"]
        with mock.patch.object(
            self.manager,
            "assert_can_issue_with_id_and_proof_type",
            mock.CoroutineMock(),
        ), patch.object(
            test_module,
            "get_properties_without_context",
            return_value=missing_properties,
        ), self.assertRaises(
            LinkedDataProofException
        ) as context:
            await self.handler.create_offer(self.cred_proposal)

        assert (
            f"{len(missing_properties)} attributes dropped. "
            f"Provide definitions in context to correct. {missing_properties}"
            in str(context.exception)
        )

    async def test_receive_offer(self):
        cred_ex_record = mock.MagicMock()
        cred_offer_message = mock.MagicMock()

        # Not much to assert. Receive offer doesn't do anything
        await self.handler.receive_offer(cred_ex_record, cred_offer_message)

    async def test_create_bound_request(self):
        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer,
        )

        (cred_format, attachment) = await self.handler.create_request(cred_ex_record)

    async def test_issue_credential_non_revocable(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False
