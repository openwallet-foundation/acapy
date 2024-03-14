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
from ..handler import LOGGER as INDY_LOGGER

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
        # Test correct data
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

    async def test_get_indy_detail_record(self):
        # any required tests, see "formats/indy/tests/test_handler.py"
        assert False

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
