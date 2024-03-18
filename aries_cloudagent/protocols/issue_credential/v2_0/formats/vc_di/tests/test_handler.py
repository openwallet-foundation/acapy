from copy import deepcopy
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from marshmallow import ValidationError

from aries_cloudagent.tests import mock

from .......core.in_memory import InMemoryProfile
from aries_askar.store import Entry
from .......ledger.base import BaseLedger
from .......ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from anoncreds import CredentialDefinition, Schema
from aries_cloudagent.core.in_memory.profile import (
    InMemoryProfile,
    InMemoryProfileSession,
)
from aries_cloudagent.anoncreds.tests.test_issuer import MockCredDefEntry
from aries_cloudagent.anoncreds.tests.test_revocation import MockEntry
from aries_cloudagent.anoncreds.models.anoncreds_schema import AnonCredsSchema
from aries_cloudagent.wallet.did_info import DIDInfo
from aries_cloudagent.wallet.did_method import DIDMethod
from aries_cloudagent.wallet.key_type import KeyType
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.multitenant.askar_profile_manager import AskarAnoncredsProfile

from .......multitenant.base import BaseMultitenantManager
from .......multitenant.manager import MultitenantManager
from .......cache.in_memory import InMemoryCache
from .......cache.base import BaseCache
from .......storage.record import StorageRecord
from .......messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
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


# these are from faber
CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"


# these are identical to indy test_handler since the wrappers are also indy compatible
from ...indy.tests.test_handler import (
    TEST_DID,
    SCHEMA_NAME,
    SCHEMA_TXN,
    SCHEMA_ID,
    SCHEMA,
    CRED_DEF,
    CRED_DEF_ID,
    REV_REG_DEF_TYPE,
    REV_REG_ID,
    TAILS_DIR,
    TAILS_HASH,
    TAILS_LOCAL,
    REV_REG_DEF,
    INDY_OFFER,
    INDY_CRED,
)

# corresponds to the test data imported above from indy test_handler
VCDI_ATTACHMENT_DATA = {
    "binding_method": {
        "anoncreds_link_secret": {
            "cred_def_id": "LjgpST2rjsoxYegQDRm7EL:3:CL:12:tag1",
            "key_correctness_proof": {
                "c": "123467890",
                "xr_cap": [
                    ["remainder", "1234567890"],
                    ["number", "12345678901234"],
                    ["master_secret", "12345678901234"],
                ],
                "xz_cap": "12345678901234567890",
            },
            "nonce": "1234567890",
        },
        "didcomm_signed_attachment": {
            "algs_supported": ["EdDSA"],
            "did_methods_supported": ["key"],
            "nonce": "1234567890",
        },
    },
    "binding_required": True,
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/security/data-integrity/v2",
            {"@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"},
        ],
        "credentialSubject": {
            "incorporationDate": {
                "encoded": "121381685682968329568231",
                "raw": "2021-01-01",
            },
            "jurisdictionId": {"encoded": "1", "raw": "1"},
            "legalName": {
                "encoded": "108156129846915621348916581250742315326283968964",
                "raw": "The Original House " "of Pies",
            },
        },
        "issuanceDate": "2024-01-10T04:44:29.563418Z",
        "issuer": "mockedDID",
        "type": ["VerifiableCredential"],
    },
    "data_model_versions_supported": ["1.1"],
}

# IC - these are the minimal unit tests required for the new VCDI format class
#      they should verify that the formatter generates and receives/handles
#      credential offers/requests/issues with the new VCDI format
#      (see "formats/indy/tests/test_handler.py" for the unit tests for the
#       existing Indy tests, these should work basically the same way)


class TestV20VCDICredFormatHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.holder = mock.MagicMock()
        self.wallet = mock.MagicMock(BaseWallet, autospec=True)

        self.session = InMemoryProfile.test_session(
            bind={VCHolder: self.holder, BaseWallet: self.wallet}
        )
        self.profile = self.session.profile
        self.context = self.profile.context
        setattr(self.profile, "session", mock.MagicMock(return_value=self.session))

        # Issuer
        self.patcher = mock.patch(
            "aries_cloudagent.protocols.issue_credential.v2_0.formats.vc_di.handler.AnonCredsIssuer",
            autospec=True,
        )
        self.MockAnonCredsIssuer = self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.issuer = mock.create_autospec(AnonCredsIssuer, instance=True)
        self.MockAnonCredsIssuer.return_value = self.issuer

        self.issuer.profile = self.profile

        # Wallet
        self.public_did_info = mock.MagicMock()
        self.public_did_info.did = "mockedDID"
        self.wallet = mock.MagicMock(spec=BaseWallet)
        self.wallet.get_public_did = mock.CoroutineMock(
            return_value=self.public_did_info
        )
        self.session.context.injector.bind_instance(BaseWallet, self.wallet)

        # Ledger
        Ledger = mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_schema = mock.CoroutineMock(return_value=SCHEMA)
        self.ledger.get_credential_definition = mock.CoroutineMock(
            return_value=CRED_DEF
        )
        self.ledger.get_revoc_reg_def = mock.CoroutineMock(return_value=REV_REG_DEF)
        self.ledger.__aenter__ = mock.CoroutineMock(return_value=self.ledger)
        self.ledger.credential_definition_id2schema_id = mock.CoroutineMock(
            return_value=SCHEMA_ID
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)
        self.context.injector.bind_instance(
            BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )

        self.manager = VcLdpManager(self.profile)
        self.context.injector.bind_instance(VcLdpManager, self.manager)
        self.handler = VCDICredFormatHandler(self.profile)

        # Holder
        self.holder = mock.MagicMock(IndyHolder, autospec=True)
        self.context.injector.bind_instance(IndyHolder, self.holder)

        self.handler = VCDICredFormatHandler(
            self.profile
        )  # this is the only difference actually
        # we could factor out base tests?

        assert self.handler.profile

    async def test_validate_fields(self):
        # Test correct data
        self.handler.validate_fields(CRED_20_PROPOSAL, {"cred_def_id": CRED_DEF_ID})
        self.handler.validate_fields(
            CRED_20_OFFER, INDY_OFFER
        )  # ok we might have to modify INDY_OFFER
        # getting
        # marshmallow.exceptions.ValidationError: {'cred_def_id': ['Unknown field.'], 'nonce': ['Unknown field.'], 'key_correctness_proof': ['Unknown field.'], 'schema_id': ['Unknown field.']}
        self.handler.validate_fields(CRED_20_REQUEST, INDY_CRED_REQ)
        self.handler.validate_fields(CRED_20_ISSUE, INDY_CRED)

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

    async def test_check_uniqueness(self):
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

        cred_def_id = CRED_DEF_ID
        connection_id = "test_conn_id"
        cred_attrs = {}
        cred_attrs[cred_def_id] = {
            "legalName": INDY_CRED["values"]["legalName"],
            "incorporationDate": INDY_CRED["values"]["incorporationDate"],
            "jurisdictionId": INDY_CRED["values"]["jurisdictionId"],
        }

        attributes = [
            V20CredAttrSpec(name=n, value=v) for n, v in cred_attrs[cred_def_id].items()
        ]

        cred_preview = V20CredPreview(attributes=attributes)

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

        original_create_credential_offer = self.issuer.create_credential_offer
        self.issuer.create_credential_offer = mock.CoroutineMock(
            return_value=json.dumps(INDY_OFFER)
        )

        (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

        # this enforces the data format needed for alice-faber demo
        assert attachment.content == VCDI_ATTACHMENT_DATA

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
            # TODO here
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer,
        )

        cred_def = {"cred": "def"}
        self.ledger.get_credential_definition = mock.CoroutineMock(
            return_value=cred_def
        )

        cred_req_meta = {}
        self.holder.create_credential_request = mock.CoroutineMock(
            return_value=(json.dumps(INDY_CRED_REQ), json.dumps(cred_req_meta))
        )

        (cred_format, attachment) = await self.handler.create_request(
            cred_ex_record, {"holder_did": holder_did}
        )

        self.holder.create_credential_request.assert_called_once_with(
            INDY_OFFER, cred_def, holder_did
        )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == INDY_CRED_REQ

        # assert data is encoded as base64
        assert attachment.data.base64

        # cover case with cache (change ID to prevent already exists error)
        cred_ex_record._id = "dummy-id2"
        await self.handler.create_request(cred_ex_record, {"holder_did": holder_did})

        # cover case with no cache in injection context
        self.context.injector.clear_binding(BaseCache)
        cred_ex_record._id = "dummy-id3"
        self.context.injector.bind_instance(
            BaseMultitenantManager,
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        with mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            mock.CoroutineMock(return_value=(None, self.ledger)),
        ):
            await self.handler.create_request(
                cred_ex_record, {"holder_did": holder_did}
            )

    async def test_receive_request(self):
        cred_ex_record = mock.MagicMock()
        cred_request_message = mock.MagicMock()

        # Not much to assert. Receive request doesn't do anything
        await self.handler.receive_request(cred_ex_record, cred_request_message)

    async def test_issue_credential_revocable(self):
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_offer = V20CredOffer(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            # TODO here
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            # TODO here
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
        )

        cred_rev_id = "1000"
        self.issuer.create_credential = mock.CoroutineMock(
            return_value=(json.dumps(INDY_CRED), cred_rev_id)
        )

        with mock.patch.object(test_module, "IndyRevocation", autospec=True) as revoc:
            revoc.return_value.get_or_create_active_registry = mock.CoroutineMock(
                return_value=(
                    mock.MagicMock(  # active_rev_reg_rec
                        revoc_reg_id=REV_REG_ID,
                    ),
                    mock.MagicMock(  # rev_reg
                        tails_local_path="dummy-path",
                        get_or_fetch_local_tails_path=(mock.CoroutineMock()),
                        max_creds=10,
                    ),
                )
            )

            (cred_format, attachment) = await self.handler.issue_credential(
                cred_ex_record, retries=1
            )

            self.issuer.create_credential.assert_called_once_with(
                SCHEMA,
                INDY_OFFER,
                INDY_CRED_REQ,
                attr_values,
                REV_REG_ID,
                "dummy-path",
            )

            # assert identifier match
            assert cred_format.attach_id == self.handler.format.api == attachment.ident

            # assert content of attachment is proposal data
            assert attachment.content == INDY_CRED

            # assert data is encoded as base64
            assert attachment.data.base64

    async def test_issue_credential_non_revocable(self):
        CRED_DEF_NR = deepcopy(CRED_DEF)
        CRED_DEF_NR["value"]["revocation"] = None
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_offer = V20CredOffer(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            # TODO here
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
        )

        self.issuer.create_credential = mock.CoroutineMock(
            return_value=(json.dumps(INDY_CRED), None)
        )
        self.ledger.get_credential_definition = mock.CoroutineMock(
            return_value=CRED_DEF_NR
        )
        self.context.injector.bind_instance(
            BaseMultitenantManager,
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        with mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ):
            (cred_format, attachment) = await self.handler.issue_credential(
                cred_ex_record, retries=0
            )

            self.issuer.create_credential.assert_called_once_with(
                SCHEMA,
                INDY_OFFER,
                INDY_CRED_REQ,
                attr_values,
                None,
                None,
            )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == INDY_CRED

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_create_proposal(self):
        cred_ex_record = mock.MagicMock()
        proposal_data = {"schema_id": SCHEMA_ID}

        (cred_format, attachment) = await self.handler.create_proposal(
            cred_ex_record, proposal_data
        )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == proposal_data

        # assert data is encoded as base64
        assert attachment.data.base64
