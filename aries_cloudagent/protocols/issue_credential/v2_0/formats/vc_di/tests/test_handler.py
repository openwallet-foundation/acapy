from copy import deepcopy
from time import time
import json
import datetime
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from marshmallow import ValidationError

from aries_cloudagent.tests import mock

from .......core.in_memory import InMemoryProfile
from .......ledger.base import BaseLedger
from .......ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from aries_cloudagent.wallet.did_info import DIDInfo
from aries_cloudagent.wallet.did_method import DIDMethod
from aries_cloudagent.wallet.key_type import KeyType
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.storage.askar import AskarProfile

from .......multitenant.base import BaseMultitenantManager
from .......multitenant.manager import MultitenantManager
from .......cache.in_memory import InMemoryCache
from .......cache.base import BaseCache
from .......storage.record import StorageRecord
from .......messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from .......messaging.decorators.attach_decorator import AttachDecorator
from .......indy.holder import IndyHolder
from .......anoncreds.issuer import AnonCredsIssuer
from ....models.cred_ex_record import V20CredExRecord
from ....models.detail.vc_di import V20CredExRecordVCDI
from ....messages.cred_proposal import V20CredProposal
from ....messages.cred_format import V20CredFormat
from ....messages.cred_issue import V20CredIssue
from ....messages.inner.cred_preview import V20CredPreview, V20CredAttrSpec
from ....messages.cred_offer import V20CredOffer
from ....messages.cred_request import (
    V20CredRequest,
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
from ..handler import LOGGER as VCDI_LOGGER

# setup any required test data, see "formats/indy/tests/test_handler.py"
# ...


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

# IC - these are the minimal unit tests required for the new VCDI format class
#      they should verify that the formatter generates and receives/handles
#      credential offers/requests/issues with the new VCDI format
#      (see "formats/indy/tests/test_handler.py" for the unit tests for the
#       existing Indy tests, these should work basically the same way)


class TestV20VCDICredFormatHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # any required setup, see "formats/indy/tests/test_handler.py"
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context
        self.askar_profile = mock.create_autospec(AskarProfile, instance=True)


        setattr(self.profile, "session", mock.MagicMock(return_value=self.session))

        # Wallet
        self.public_did_info = mock.MagicMock() 
        self.public_did_info.did = 'mockedDID'
        self.wallet = mock.MagicMock(spec=BaseWallet)
        self.wallet.get_public_did = mock.CoroutineMock(return_value=self.public_did_info)
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
            IndyLedgerRequestsExecutor,
            mock.MagicMock(
                get_ledger_for_identifier=mock.CoroutineMock(
                    return_value=(None, self.ledger)
                )
            ),
        )

        # Context
        self.cache = InMemoryCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        # Issuer
        self.issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
        self.issuer.profile = self.askar_profile
        self.context.injector.bind_instance(AnonCredsIssuer, self.issuer) 

        # Holder
        self.holder = mock.MagicMock(IndyHolder, autospec=True)
        self.context.injector.bind_instance(IndyHolder, self.holder)


        
# async with self.profile.session() as session:
#            wallet = session.inject(BaseWallet)
#            public_did_info = await wallet.get_public_did()
#            public_did = public_did_info.did

        self.handler = VCDICredFormatHandler(self.profile)  # this is the only difference actually
                                                            # we could factor out base tests?

        assert self.handler.profile

    async def test_validate_fields(self):
        # this does not touch the attachment format, so is identical to the indy test

        # this does not touch the attachment format, so is identical to the indy test

        # Test correct data
        self.handler.validate_fields(CRED_20_PROPOSAL, {"cred_def_id": CRED_DEF_ID})
        self.handler.validate_fields(CRED_20_OFFER, INDY_OFFER)
        self.handler.validate_fields(CRED_20_REQUEST, INDY_CRED_REQ)
        self.handler.validate_fields(CRED_20_ISSUE, INDY_CRED)

        # test incorrect proposal
        with self.assertRaises(ValidationError):
            self.handler.validate_fields(
                CRED_20_PROPOSAL, {"some_random_key": "some_random_value"}
            )

        # test incorrect offer
        with self.assertRaises(ValidationError):
            offer = INDY_OFFER.copy()
            offer.pop("nonce")
            self.handler.validate_fields(CRED_20_OFFER, offer)

        # test incorrect request
        with self.assertRaises(ValidationError):
            req = INDY_CRED_REQ.copy()
            req.pop("nonce")
            self.handler.validate_fields(CRED_20_REQUEST, req)

        # test incorrect cred
        with self.assertRaises(ValidationError):
            cred = INDY_CRED.copy()
            cred.pop("schema_id")
            self.handler.validate_fields(CRED_20_ISSUE, cred)

    async def test_get_indy_detail_record(self):
        cred_ex_id = "dummy"
        details_indy = [
            V20CredExRecordVCDI(
                cred_ex_id=cred_ex_id,
                rev_reg_id="rr-id",
                cred_rev_id="0",
            ),
            V20CredExRecordVCDI(
                cred_ex_id=cred_ex_id,
                rev_reg_id="rr-id",
                cred_rev_id="1",
            ),
        ]
        await details_indy[0].save(self.session)
        await details_indy[1].save(self.session)  # exercise logger warning on get()

        with mock.patch.object(
            VCDI_LOGGER, "warning", mock.MagicMock()
        ) as mock_warning:
            assert await self.handler.get_detail_record(cred_ex_id) in details_indy
            mock_warning.assert_called_once()


    async def test_check_uniqueness(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_create_offer(self):
        age = 24
        d = datetime.date.today()
        birth_date = datetime.date(d.year - age, d.month, d.day)
        birth_date_format = "%Y%m%d"

        cred_def_id = CRED_DEF_ID
        connection_id = "test_conn_id"
        cred_attrs = {} 
        cred_attrs[cred_def_id] = {
            "legalName": INDY_CRED["values"]["legalName"],
            "incorporationDate": INDY_CRED["values"]["incorporationDate"],
            "jurisdictionId": INDY_CRED["values"]["jurisdictionId"],
        }

        attributes = [V20CredAttrSpec(name=n, value=v) for n, v in cred_attrs[cred_def_id].items()]

        cred_preview = V20CredPreview(attributes=attributes)

        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64({"cred_def_id": CRED_DEF_ID}, ident="0")
            ],
        )

        self.issuer.create_credential_offer = mock.CoroutineMock(
            return_value=json.dumps(INDY_OFFER)
        )

        (cred_format, attachment) = await self.handler.create_offer(cred_proposal)
        from pprint import pprint
        pprint(cred_format)
        pprint(attachment.content)  # will NOT be INDY_OFFER in our case!

#        offer_request = {
#            "connection_id": connection_id,
#            "comment": f"Offer on cred def id {cred_def_id}",
#            "auto_remove": False,
#            "credential_preview": cred_preview,
#            "filter": {"vc_di": {"cred_def_id": cred_def_id}},
#            "trace": exchange_tracing,
#        }
        # this normally is sent to  "/issue-credential-2.0/send-offer" with offer_request
        # maybe this is a different unit test? 
        # this data is from the faber vc_di


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

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == LD_PROOF_VC_DETAIL

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_create_free_request(self):
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_proposal=self.cred_proposal,
        )

        (cred_format, attachment) = await self.handler.create_request(cred_ex_record)

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == LD_PROOF_VC_DETAIL

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_create_request_x_no_data(self):
        cred_ex_record = V20CredExRecord(state=V20CredExRecord.STATE_OFFER_RECEIVED)

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.create_request(cred_ex_record)
        assert (
            "Cannot create linked data proof request without offer or input data"
            in str(context.exception)
        )

    async def test_receive_request_no_offer(self):
        cred_ex_record = mock.MagicMock()
        cred_ex_record.cred_offer = None
        cred_request_message = mock.MagicMock()

        # Not much to assert. Receive request doesn't do anything if no prior offer
        await self.handler.receive_request(cred_ex_record, cred_request_message)

    async def test_receive_request_with_offer_no_id(self):
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
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            requests_attach=[
                AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")
            ],
        )

        await self.handler.receive_request(cred_ex_record, cred_request)

    async def test_receive_request_with_offer_with_id(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)
        detail["credential"]["credentialSubject"]["id"] = "some id"
        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer,
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
            requests_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )

        await self.handler.receive_request(cred_ex_record, cred_request)

    async def test_receive_request_with_offer_with_id_x_mismatch_id(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)
        detail["credential"]["credentialSubject"]["id"] = "some id"
        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer,
        )
        req_detail = deepcopy(detail)
        req_detail["credential"]["credentialSubject"]["id"] = "other id"
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(req_detail, ident="0")],
        )

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.receive_request(cred_ex_record, cred_request)
        assert "must match offer" in str(context.exception)

    async def test_receive_request_with_offer_with_id_x_changed_cred(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)
        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer,
        )
        req_detail = deepcopy(LD_PROOF_VC_DETAIL_ED25519_2020)
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(req_detail, ident="0")],
        )

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.receive_request(cred_ex_record, cred_request)
        assert "Request must match offer if offer is sent" in str(context.exception)

    async def test_issue_credential(self):
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            requests_attach=[
                AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")
            ],
        )

        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_request=cred_request,
        )

        with mock.patch.object(
            VcLdpManager,
            "issue",
            mock.CoroutineMock(
                return_value=VerifiableCredential.deserialize(LD_PROOF_VC)
            ),
        ) as mock_issue:
            (cred_format, attachment) = await self.handler.issue_credential(
                cred_ex_record
            )

            detail = LDProofVCDetail.deserialize(LD_PROOF_VC_DETAIL)

            mock_issue.assert_called_once_with(
                VerifiableCredential.deserialize(LD_PROOF_VC_DETAIL["credential"]),
                LDProofVCOptions.deserialize(LD_PROOF_VC_DETAIL["options"]),
            )

            # assert identifier match
            assert cred_format.attach_id == self.handler.format.api == attachment.ident

            # assert content of attachment is credential data
            assert attachment.content == LD_PROOF_VC

            # assert data is encoded as base64
            assert attachment.data.base64

    async def test_issue_credential_x_no_data(self):
        cred_ex_record = V20CredExRecord()

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.issue_credential(cred_ex_record)
        assert "Cannot issue credential without credential request" in str(
            context.exception
        )

    async def test_receive_credential(self):
        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
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
            requests_attach=[
                AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")
            ],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="cred-ex-id",
            cred_request=cred_request,
        )

        await self.handler.receive_credential(cred_ex_record, cred_issue)

    async def test_receive_credential_x_credential_ne_request(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)

        # Change date so request is different than issued credential
        detail["credential"]["issuanceDate"] = "2020-01-01"

        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="cred-ex-id",
            cred_request=cred_request,
        )

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.receive_credential(cred_ex_record, cred_issue)
        assert "does not match requested credential" in str(context.exception)

    async def test_receive_credential_x_credential_status_ne(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)

        # Set credential status so it's only set on the detail
        # not the issued credential
        detail["options"]["credentialStatus"] = {"type": "CredentialStatusType"}

        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="cred-ex-id",
            cred_request=cred_request,
        )

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.receive_credential(cred_ex_record, cred_issue)
        assert "Received credential status contains credential status" in str(
            context.exception
        )

    async def test_receive_credential_x_credential_status_ne_both_set(self):
        detail = deepcopy(LD_PROOF_VC_DETAIL)
        status_entry = {"type": "SomeRandomType"}

        # Set credential status in both request and reference credential
        detail["options"]["credentialStatus"] = {"type": "CredentialStatusType"}
        detail["credential"]["credentialStatus"] = deepcopy(status_entry)

        vc = deepcopy(LD_PROOF_VC)
        vc["credentialStatus"] = deepcopy(status_entry)

        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(vc, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(detail, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="cred-ex-id",
            cred_request=cred_request,
        )

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler.receive_credential(cred_ex_record, cred_issue)
        assert (
            "Received credential status type does not match credential request"
            in str(context.exception)
        )

    async def test_receive_credential_x_proof_options_ne(self):
        properties = {
            "challenge": "3f9054c0-70df-497d-9bbb-f373ddf986ce",
            "domain": "example.com",
            "proofType": "SomeType",
            "created": "2000-01-11T03:50:55",
        }
        for property, value in properties.items():
            detail = deepcopy(LD_PROOF_VC_DETAIL)

            detail["options"][property] = value

            cred_issue = V20CredIssue(
                formats=[
                    V20CredFormat(
                        attach_id="0",
                        format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                            V20CredFormat.Format.VC_DI.api
                        ],
                    )
                ],
                credentials_attach=[
                    AttachDecorator.data_base64(LD_PROOF_VC, ident="0")
                ],
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
                requests_attach=[AttachDecorator.data_base64(detail, ident="0")],
            )
            cred_ex_record = V20CredExRecord(
                cred_ex_id="cred-ex-id",
                cred_request=cred_request,
            )

            with self.assertRaises(V20CredFormatError) as context:
                await self.handler.receive_credential(cred_ex_record, cred_issue)
            assert f"does not match options.{property} from credential request" in str(
                context.exception
            )

    async def test_store_credential(self):
        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
        )

        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_issue=cred_issue,
        )

        cred_id = "cred_id"
        self.holder.store_credential = mock.CoroutineMock()

        with mock.patch.object(
            VcLdpManager,
            "verify_credential",
            mock.CoroutineMock(return_value=DocumentVerificationResult(verified=True)),
        ) as mock_verify_credential:
            await self.handler.store_credential(cred_ex_record, cred_id)

            self.holder.store_credential.assert_called_once_with(
                VCRecord(
                    contexts=LD_PROOF_VC["@context"],
                    expanded_types=[
                        "https://www.w3.org/2018/credentials#VerifiableCredential",
                        "https://example.org/examples#UniversityDegreeCredential",
                    ],
                    issuer_id=LD_PROOF_VC["issuer"],
                    subject_ids=[],
                    schema_ids=[],  # Schemas not supported yet
                    proof_types=[LD_PROOF_VC["proof"]["type"]],
                    cred_value=LD_PROOF_VC,
                    given_id=None,
                    record_id=cred_id,
                )
            )

    async def test_store_credential_x_not_verified(self):
        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
        )

        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_issue=cred_issue,
        )

        cred_id = "cred_id"
        self.holder.store_credential = mock.CoroutineMock()

        with mock.patch.object(
            self.manager,
            "_get_suite",
            mock.CoroutineMock(),
        ) as mock_get_suite, mock.patch.object(
            self.manager,
            "verify_credential",
            mock.CoroutineMock(return_value=DocumentVerificationResult(verified=False)),
        ) as mock_verify_credential, mock.patch.object(
            self.manager,
            "_get_proof_purpose",
        ) as mock_get_proof_purpose, self.assertRaises(
            V20CredFormatError
        ) as context:
            await self.handler.store_credential(cred_ex_record, cred_id)
        assert "Received invalid credential: " in str(context.exception)
