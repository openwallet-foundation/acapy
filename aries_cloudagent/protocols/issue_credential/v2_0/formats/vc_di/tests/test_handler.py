from copy import deepcopy
from time import time
import json
import datetime
from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock
from marshmallow import ValidationError

from .. import handler as test_module

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
    CRED_20_PROPOSAL,
    CRED_20_OFFER,
    CRED_20_REQUEST,
    CRED_20_ISSUE,
)

from ...handler import V20CredFormatError

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

# corresponds to the test data imported above from indy test_handler
VCDI_ATTACHMENT_DATA = {'binding_method': {'anoncreds_link_secret': {'cred_def_id': 'LjgpST2rjsoxYegQDRm7EL:3:CL:12:tag1',
                                              'key_correctness_proof': {'c': '123467890',
                                                                        'xr_cap': [['remainder',
                                                                                    '1234567890'],
                                                                                   ['number',
                                                                                    '12345678901234'],
                                                                                   ['master_secret',
                                                                                    '12345678901234']],
                                                                        'xz_cap': '12345678901234567890'},
                                              'nonce': '1234567890'},
                    'didcomm_signed_attachment': {'algs_supported': ['EdDSA'],
                                                  'did_methods_supported': ['key'],
                                                  'nonce': '1234567890'}},
 'binding_required': True,
 'credential': {'@context': ['https://www.w3.org/2018/credentials/v1',
                             'https://w3id.org/security/data-integrity/v2',
                             {'@vocab': 'https://www.w3.org/ns/credentials/issuer-dependent#'}],
                'credentialSubject': {'incorporationDate': {'encoded': '121381685682968329568231',
                                                            'raw': '2021-01-01'},
                                      'jurisdictionId': {'encoded': '1',
                                                         'raw': '1'},
                                      'legalName': {'encoded': '108156129846915621348916581250742315326283968964',
                                                    'raw': 'The Original House '
                                                           'of Pies'}},
                'issuanceDate': '2024-01-10T04:44:29.563418Z',
                'issuer': 'mockedDID',
                'type': ['VerifiableCredential']},
 'data_model_versions_supported': ['1.1']}

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

        self.handler = VCDICredFormatHandler(self.profile)  # this is the only difference actually
                                                            # we could factor out base tests?

        assert self.handler.profile

    async def test_validate_fields(self):
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

        original_create_credential_offer = self.issuer.create_credential_offer
        self.issuer.create_credential_offer = mock.CoroutineMock(
            return_value=json.dumps(INDY_OFFER)
        )

        (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

        # this enforces the data format needed for alice-faber demo
        assert attachment.content == VCDI_ATTACHMENT_DATA 

        self.issuer.create_credential_offer.assert_called_once()

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert data is encoded as base64
        assert attachment.data.base64

        self.issuer.create_credential_offer = original_create_credential_offer


    async def test_receive_offer(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_create_request(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_receive_request(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_issue_credential_revocable(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_issue_credential_non_revocable(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False
