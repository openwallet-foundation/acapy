import json
from copy import deepcopy
from time import time
from unittest import IsolatedAsyncioTestCase

import pytest
from anoncreds import W3cCredential
from marshmallow import ValidationError

from .......anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from .......anoncreds.issuer import AnonCredsIssuer
from .......anoncreds.models.credential_definition import CredDef, GetCredDefResult
from .......anoncreds.models.revocation import GetRevRegDefResult, RevRegDef
from .......anoncreds.registry import AnonCredsRegistry
from .......cache.base import BaseCache
from .......cache.in_memory import InMemoryCache
from .......ledger.base import BaseLedger
from .......ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from .......messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from .......messaging.decorators.attach_decorator import AttachDecorator
from .......multitenant.base import BaseMultitenantManager
from .......multitenant.manager import MultitenantManager
from .......protocols.issue_credential.v2_0.formats.handler import V20CredFormatError
from .......protocols.issue_credential.v2_0.messages.cred_format import V20CredFormat
from .......protocols.issue_credential.v2_0.messages.cred_issue import V20CredIssue
from .......protocols.issue_credential.v2_0.messages.cred_offer import V20CredOffer
from .......protocols.issue_credential.v2_0.messages.cred_proposal import V20CredProposal
from .......protocols.issue_credential.v2_0.messages.cred_request import V20CredRequest
from .......protocols.issue_credential.v2_0.messages.inner.cred_preview import (
    V20CredAttrSpec,
    V20CredPreview,
)
from .......protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from .......protocols.issue_credential.v2_0.models.detail.indy import V20CredExRecordIndy
from .......storage.base import BaseStorage
from .......storage.record import StorageRecord
from .......tests import mock
from .......utils.testing import create_test_profile
from .......wallet.askar import AskarWallet
from .......wallet.base import BaseWallet
from .......wallet.did_info import DIDInfo
from ....message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from .. import handler as test_module
from ..handler import LOGGER as VCDI_LOGGER
from ..handler import VCDICredFormatHandler

# these are from faber
CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"


TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
SCHEMA_NAME = "bc-reg"
SCHEMA_TXN = 12
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:1.0"
SCHEMA = {
    "ver": "1.0",
    "id": SCHEMA_ID,
    "name": SCHEMA_NAME,
    "version": "1.0",
    "attrNames": ["legalName", "jurisdictionId", "incorporationDate"],
    "seqNo": SCHEMA_TXN,
}
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
CRED_DEF = {
    "ver": "1.0",
    "id": CRED_DEF_ID,
    "schemaId": SCHEMA_TXN,
    "type": "CL",
    "tag": "tag1",
    "value": {
        "primary": {
            "n": "...",
            "s": "...",
            "r": {
                "master_secret": "...",
                "legalName": "...",
                "jurisdictionId": "...",
                "incorporationDate": "...",
            },
            "rctxt": "...",
            "z": "...",
        },
        "revocation": {
            "g": "1 ...",
            "g_dash": "1 ...",
            "h": "1 ...",
            "h0": "1 ...",
            "h1": "1 ...",
            "h2": "1 ...",
            "htilde": "1 ...",
            "h_cap": "1 ...",
            "u": "1 ...",
            "pk": "1 ...",
            "y": "1 ...",
        },
    },
}
REV_REG_DEF_TYPE = "CL_ACCUM"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:{REV_REG_DEF_TYPE}:tag1"
TAILS_DIR = "/tmp/indy/revocation/tails_files"
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}/{TAILS_HASH}"
REV_REG_DEF = {
    "ver": "1.0",
    "id": REV_REG_ID,
    "revocDefType": "CL_ACCUM",
    "tag": "tag1",
    "credDefId": CRED_DEF_ID,
    "value": {
        "issuanceType": "ISSUANCE_ON_DEMAND",
        "maxCredNum": 5,
        "publicKeys": {"accumKey": {"z": "1 ..."}},
        "tailsHash": TAILS_HASH,
        "tailsLocation": TAILS_LOCAL,
    },
}
VCDI_OFFER = {
    "data_model_versions_supported": ["1.1"],
    "binding_required": True,
    "binding_method": {
        "anoncreds_link_secret": {
            "cred_def_id": CRED_DEF_ID,
            "key_correctness_proof": {
                "c": "123467890",
                "xz_cap": "12345678901234567890",
                "xr_cap": [
                    ["remainder", "1234567890"],
                    ["number", "12345678901234"],
                ],
            },
            "nonce": "803336938981521544311884",
        },
        "didcomm_signed_attachment": {
            "algs_supported": ["EdDSA"],
            "did_methods_supported": ["key"],
            "nonce": "803336938981521544311884",
        },
    },
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/security/data-integrity/v2",
            {"@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"},
        ],
        "type": ["VerifiableCredential"],
        "issuer": "LSTv7AUoTyfqFxZbuAGqKR",
        "credentialSubject": {
            "name": "Alice Smith",
            "date": "2018-05-28",
            "degree": "Maths",
            "birthdate_dateint": "20000331",
            "timestamp": "1711845568",
        },
        "issuanceDate": "2024-01-10T04:44:29.563418Z",
    },
}

VCDI_CRED_REQ = {
    "data_model_version": "2.0",
    "binding_proof": {
        "anoncreds_link_secret": {
            "prover_did": f"did:sov:{TEST_DID}",
            "entropy": f"did:sov:{TEST_DID}",
            "cred_def_id": CRED_DEF_ID,
            "blinded_ms": {
                "u": "10047077609650450290609991930929594521921208780899757965398360086992099381832995073955506958821655372681970112562804577530208651675996528617262693958751195285371230790988741041496869140904046414320278189103736789305088489636024127715978439300785989247215275867951013255925809735479471883338351299180591011255281885961242995409072561940244771612447316409017677474822482928698183528232263803799926211692640155689629903898365777273000566450465466723659861801656618726777274689021162957914736922404694190070274236964163273886807208820068271673047750886130307545831668836096290655823576388755329367886670574352063509727295",
                "ur": "1 10047077609650450290609991930929594521921208780899757965398360086992099381832995073955506958821655372681970112562804577530208651675996528617262693958751195285371230790988741041496869140904046414320278189103736789305088489636024127715978439300785989247215275867951013255925809735479471883338351299180591011255281885961242995409072561940244771612447316409017677474822482928698183528232263803799926211692640155689629903898365777273000566450465466723659861801656618726777274689021162957914736922404694190070274236964163273886807208820068271673047750886130307545831668836096290655823576388755329367886670574352063509727295",
                "hidden_attributes": ["master_secret"],
                "committed_attributes": {},
            },
            "blinded_ms_correctness_proof": {
                "c": "114820252909341277169123380270435575009714169580229908332117664809097619479483",
                "v_dash_cap": "2800797042446023854769298889946111553775800551626595767742635719512900304820391485829151945623333206184503230504182991047567531709613146606620747119977967362375975470346540769137309709302645176745785595101997824808807951935607979085748767054924474772855886854081455495367299835633316236603850924206877781343663290011630380243973434735740532318737134036990657225621660855862337569102753069931768335142276913795486645880476005516655059658346071702100939785144477050087370752056081492070366540039114009106296993876935692142991636251707934248460120048734266848191670576929279282843107501392282445417047087792806945845190270343938754413343820710137866411061071233755924209847337885397612906914410338546708562034035772917684",
                "m_caps": {
                    "master_secret": "27860715812851216521476619601374576486949815748604240358820717458669963808683330226247784299086475972693040811857737248781118170534547319442287676278121026619110648625203644115424"
                },
                "r_caps": {},
            },
            "nonce": "866186615577411311009479",
        },
        "didcomm_signed_attachment": {"attachment_id": "test"},
    },
}

VCDI_CRED = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/security/data-integrity/v2",
            {"@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"},
        ],
        "type": ["VerifiableCredential"],
        "issuer": "LSTv7AUoTyfqFxZbuAGqKR",
        "credentialSubject": {
            "name": "Alice Smith",
            "timestamp": "1711845568",
            "birthdate_dateint": "20000331",
            "date": "2018-05-28",
            "degree": "Maths",
        },
        "proof": [
            {
                "cryptosuite": "anoncreds-2023",
                "type": "DataIntegrityProof",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "LSTv7AUoTyfqFxZbuAGqKR:3:CL:536199:faber.agent.degree_schema",
                "proofValue": "ukgGEqXNjaGVtYV9pZNkvTFNUdjdBVW9UeWZxRnhaYnVBR3FLUjoyOmRlZ3JlZSBzY2hlbWE6MzUuNzguNzSrY3JlZF9kZWZfaWTZPExTVHY3QVVvVHlmcUZ4WmJ1QUdxS1I6MzpDTDo1MzYxOTk6ZmFiZXIuYWdlbnQuZGVncmVlX3NjaGVtYalzaWduYXR1cmWCrHBfY3JlZGVudGlhbISjbV8y3AAgzP_Ml8zXzOpNYcyXIxROzNHMvlk9zNnMsAkSzK7Mq0jMwxN0zMAMZMz4QszbzPkioWHcAQA3UnhCzPTM8syhS0vMjcygzJUAV8yYzLlAUcz-KszVEC0ADS7MhFMszIPMlczRf8zmd8ykzPxHzOzMkn02WA93WADM5czczOhlTk7M3szBR2jM_3bMpCnMmlIRWMy6zIQnzOkFei80ZljM_FY4zNHMn21izIBLzNDMuMyKzIYIzOh-zKF_Hcz0zNMTzNbMsczazJl4OsyBWsyMzJkrzJnMwMypzJdjzOksS05gzN7M4TfM3hrMix5HzLoyzI7Mt8z4zJIiRTHMysz-zIUidsyKzIrMn8yKzOfMuW3MoEXMsUjMzno6zNVheMyFzPMqFgk6zK1HI3HM-0bMwxcQzJDMysz-b8zMBSDMqsyQzMzMwEslF8z4zPfM5cyWzITMiMyCGQg6IzBVYszAG8z5zJtfzPVPZn5lzIzM3hctzMHM5My5F1LMhsyJzILMy1PM98z0fsyEJ1LMsMzzzN4tzMB5BVLMxsz5zNHMh8yYzKMgEzLMiUotzLLM-EYEzIshoWXcAEsQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASzPfMkcz8fn_M4syUOszEP215zNwLoXbcAVUIzLZHzLnMyiLM0czSUjzM_EJ-zLsmzKnMncyRzO5UFTfMpcynzIE6Vsz3EVnMx1EhG8yMbszKzNxadsyKzLPM3XhcZMyWIEzM81vM1nwdE8zVzN7Mzyd4zMjM78yjG0TMuWXMiMzIF3fMyRJdK8yczLYgIi3MwczOUczRNcyuRDzMhWBGPhnMiXbMp0PMj8z8zMgiVzk_HcyDPxjMmTDM917M88z4GczIacyfzLVCR2rM21zMjloMzI44zNsPzMrMnczIfVQXzPdYzLBuzPY5zIp9cMzaBRfM0j7MoAjMucysawHM3MyrzIrMz8ymzIvMl8zzH8yCfczhzMvM5nVUTAhDUhXMkRjM717M7szWO8y8IcyYAV3M6RnM0cyrPmXMmMyKzMsEzNzM4cyTY8zTzITMqsz3HcyMLMzjfXZCK8yZXMzIMsy3zMNazJPMjMzBzMBXPHYyzI5bKsyuGczzDcy4zJvMknYTzJHMpcyYzMjMtmPM-czuzMrMycz_zLfM7MzzY8yezL3MqnnM00wXJsy9zMfM08z-zMLMugE9YszzzLsTzIQrCwPMucyqzIHMmGpozOjMrl5OzOfM7cy1KEvMqxIsP1LM-ETM_8yHzIJFUMy5zMg_zIXMwQEdGcy_zKrMh8zpzKvM0szlzNdQzPNFzLwWzMrMvQkTzK5czJU7QUYarHJfY3JlZGVudGlhbMC7c2lnbmF0dXJlX2NvcnJlY3RuZXNzX3Byb29mgqJzZdwBAFTMpszvdjHM9hBoWczmzIJiOBXM9szdzM1-zK0zcR7M9hsLzNfMuXDM4mxLzJwsYC3MuMzKacz3zK5yGRPM_QUmCMylzNfM48zvzPDMzk7MuVxtMsyZzPIXeszgzOrM_My5zL3M9czJzLR7zLrMxEAfzKsBdR_M7WPM2gvM-FYNzMtZCsytzJkra8y3aXcczODMg8z5zIIaUXrM9sySV1XM2MyCdHgazILMv3htzJ9VMjtDKxNGFMz4OsyXf8zyZHHMx8ynO09-TGp_JczPVGsSfcygG8zvGQtnbnLMzCDMycyCR23M0szca2VRW0hSzKPMrMyWzK3M8EnM_BpmQXMNGszHzIDM0MywK2sQJszjzNHM-XbMki3M68yxzON8zNR6fMy8zOgKzOZazMrMzw9nzIvMrkXM4UAGdjDMvczPIjsscFYaC8ySdRtNzOTMyDcVFsyDLMygaldrT8zwzPDMzSkHzPPM_w4wVszAoWPcACDM9Mz1zOMmzIdgfDJPQMyjzNVqF0PM3syRzLliSMyRZcy9AW3MoWTMmh9pDszs",
            }
        ],
        "issuanceDate": "2024-03-31T00:39:32.220900632Z",
    }
}


class TestV20VCDICredFormatHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        # Ledger
        self.ledger = mock.MagicMock(BaseLedger, autospec=True)
        self.ledger.get_schema = mock.CoroutineMock(return_value=SCHEMA)
        self.ledger.get_credential_definition = mock.CoroutineMock(return_value=CRED_DEF)
        self.ledger.get_revoc_reg_def = mock.CoroutineMock(return_value=REV_REG_DEF)
        self.ledger.credential_definition_id2schema_id = mock.CoroutineMock(
            return_value=SCHEMA_ID
        )
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)
        mock_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_executor
        )
        # Context
        self.cache = InMemoryCache()
        self.profile.context.injector.bind_instance(BaseCache, self.cache)

        # Issuer
        self.issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
        self.profile.context.injector.bind_instance(AnonCredsIssuer, self.issuer)

        # Holder
        self.holder = mock.MagicMock(AnonCredsHolder, autospec=True)
        self.profile.context.injector.bind_instance(AnonCredsHolder, self.holder)

        mock_wallet = mock.MagicMock(BaseWallet, autospec=True)
        mock_wallet.get_public_did = mock.CoroutineMock(
            return_value=DIDInfo(TEST_DID, None, None, None, True)
        )
        self.profile.context.injector.bind_instance(BaseWallet, mock_wallet)

        self.handler = VCDICredFormatHandler(self.profile)

        assert self.handler.profile

    async def test_validate_fields(self):
        # Test correct data
        self.handler.validate_fields(CRED_20_PROPOSAL, {"cred_def_id": CRED_DEF_ID})
        self.handler.validate_fields(CRED_20_OFFER, VCDI_OFFER)
        # getting
        self.handler.validate_fields(CRED_20_REQUEST, VCDI_CRED_REQ)
        self.handler.validate_fields(CRED_20_ISSUE, VCDI_CRED)

        # test incorrect proposal
        with self.assertRaises(ValidationError):
            self.handler.validate_fields(
                CRED_20_PROPOSAL, {"some_random_key": "some_random_value"}
            )

        # test incorrect offer
        with self.assertRaises(ValidationError):
            offer = VCDI_OFFER.copy()
            offer.pop("binding_method")
            self.handler.validate_fields(CRED_20_OFFER, offer)

        # test incorrect request
        with self.assertRaises(ValidationError):
            req = VCDI_CRED_REQ.copy()
            req.pop("data_model_version")
            self.handler.validate_fields(CRED_20_REQUEST, req)

        # test incorrect cred
        with self.assertRaises(ValidationError):
            cred = VCDI_CRED.copy()
            cred.pop("credential")
            self.handler.validate_fields(CRED_20_ISSUE, cred)

    async def test_get_vcdi_detail_record(self):
        cred_ex_id = "dummy"
        details_vcdi = [
            V20CredExRecordIndy(
                cred_ex_id=cred_ex_id,
                rev_reg_id="rr-id",
                cred_rev_id="0",
            ),
            V20CredExRecordIndy(
                cred_ex_id=cred_ex_id,
                rev_reg_id="rr-id",
                cred_rev_id="1",
            ),
        ]
        async with self.profile.session() as session:
            await details_vcdi[0].save(session)
            await details_vcdi[1].save(session)  # exercise logger warning on get()

        with mock.patch.object(VCDI_LOGGER, "warning", mock.MagicMock()) as mock_warning:
            assert await self.handler.get_detail_record(cred_ex_id) in details_vcdi
            mock_warning.assert_called_once()

    async def test_check_uniqueness(self):
        with mock.patch.object(
            self.handler.format.detail,
            "query_by_cred_ex_id",
            mock.CoroutineMock(),
        ) as mock_vcdi_query:
            mock_vcdi_query.return_value = []
            await self.handler._check_uniqueness("dummy-cx-id")

        with mock.patch.object(
            self.handler.format.detail,
            "query_by_cred_ex_id",
            mock.CoroutineMock(),
        ) as mock_vcdi_query:
            mock_vcdi_query.return_value = [mock.MagicMock()]
            with self.assertRaises(V20CredFormatError) as context:
                await self.handler._check_uniqueness("dummy-cx-id")
            assert "detail record already exists" in str(context.exception)

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

    async def test_create_proposal_none(self):
        cred_ex_record = mock.MagicMock()
        proposal_data = None

        (cred_format, attachment) = await self.handler.create_proposal(
            cred_ex_record, proposal_data
        )

        # assert content of attachment is proposal data
        assert attachment.content == {}

    async def test_receive_proposal(self):
        cred_ex_record = mock.MagicMock()
        cred_proposal_message = mock.MagicMock()

        # Not much to assert. Receive proposal doesn't do anything
        await self.handler.receive_proposal(cred_ex_record, cred_proposal_message)

    @mock.patch.object(
        AskarWallet,
        "get_public_did",
        return_value=DIDInfo(TEST_DID, None, None, None, True),
    )
    async def test_create_offer(self, _):
        schema_id_parts = SCHEMA_ID.split(":")

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

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

        cred_def_record = StorageRecord(
            CRED_DEF_SENT_RECORD_TYPE,
            CRED_DEF_ID,
            {
                "schema_id": SCHEMA_ID,
                "schema_issuer_did": schema_id_parts[0],
                "schema_name": schema_id_parts[-2],
                "schema_version": schema_id_parts[-1],
                "issuer_did": TEST_DID,
                "cred_def_id": CRED_DEF_ID,
                "epoch": str(int(time())),
            },
        )
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.add_record(cred_def_record)

        with mock.patch.object(test_module, "AnonCredsIssuer", return_value=self.issuer):
            self.issuer.create_credential_offer = mock.CoroutineMock(
                return_value=json.dumps(
                    VCDI_OFFER["binding_method"]["anoncreds_link_secret"]
                )
            )

            self.issuer.match_created_credential_definitions = mock.CoroutineMock(
                return_value=CRED_DEF_ID
            )

            (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

            self.issuer.create_credential_offer.assert_called_once_with(CRED_DEF_ID)

            assert cred_format.attach_id == self.handler.format.api == attachment.ident

            assert (
                attachment.content["binding_method"]["anoncreds_link_secret"]
                == VCDI_OFFER["binding_method"]["anoncreds_link_secret"]
            )

            # Assert data is encoded as base64
            assert attachment.data.base64
            # TODO: fix this get_public_did return None in the sc
            # (cred_format, attachment) = await self.handler.create_offer(cred_proposal)

            # self.issuer.create_credential_offer.assert_not_called()

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_receive_offer(self):
        cred_ex_record = mock.MagicMock()
        cred_offer_message = mock.MagicMock()

        # Not much to assert. Receive offer doesn't do anything
        await self.handler.receive_offer(cred_ex_record, cred_offer_message)

    async def test_create_request(self):
        # Define your mock credential definition
        mock_credential_definition_result = GetCredDefResult(
            credential_definition=CredDef(
                issuer_id=TEST_DID, schema_id=SCHEMA_ID, type="CL", tag="tag1", value={}
            ),
            credential_definition_id=CRED_DEF_ID,
            resolution_metadata={},
            credential_definition_metadata={},
        )
        mock_creds_registry = mock.MagicMock(AnonCredsRegistry, autospec=True)
        mock_creds_registry.get_credential_definition = mock.AsyncMock(
            return_value=mock_credential_definition_result
        )

        # Inject the MagicMock into the context
        self.profile.context.injector.bind_instance(
            AnonCredsRegistry, mock_creds_registry
        )

        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(VCDI_OFFER, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-id",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            cred_offer=cred_offer.serialize(),
        )

        cred_req_meta = {}
        self.holder.create_credential_request = mock.CoroutineMock(
            return_value=(json.dumps(VCDI_CRED_REQ), json.dumps(cred_req_meta))
        )

        self.profile = await create_test_profile(
            {
                "wallet.type": "askar-anoncreds",
            }
        )
        with mock.patch.object(
            AnonCredsHolder, "create_credential_request", mock.CoroutineMock()
        ) as mock_create:
            mock_create.return_value = (
                json.dumps(VCDI_CRED_REQ["binding_proof"]["anoncreds_link_secret"]),
                json.dumps(cred_req_meta),
            )
            (cred_format, attachment) = await self.handler.create_request(
                cred_ex_record, {"holder_did": holder_did}
            )

            legacy_offer = await self.handler._prepare_legacy_offer(VCDI_OFFER, SCHEMA_ID)
            mock_create.assert_called_once_with(
                legacy_offer,
                mock_credential_definition_result.credential_definition,
                holder_did,
            )
            assert cred_format.attach_id == self.handler.format.api == attachment.ident

            del VCDI_CRED_REQ["binding_proof"]["anoncreds_link_secret"]["prover_did"]
            assert attachment.content == VCDI_CRED_REQ
            assert attachment.data.base64

            cred_ex_record._id = "dummy-id2"
            await self.handler.create_request(cred_ex_record, {"holder_did": holder_did})

            self.profile.context.injector.clear_binding(BaseCache)
            cred_ex_record._id = "dummy-id3"
            self.profile.context.injector.bind_instance(
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

    @pytest.mark.skip(reason="AnonCreds-break")
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
            offers_attach=[AttachDecorator.data_base64(VCDI_OFFER, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(VCDI_CRED_REQ, ident="0")],
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
        dummy_registry = "dummy-registry"
        expected_credential = json.dumps(VCDI_CRED)

        # Mock AnonCredsRevocation and its method create_credential_w3c
        with mock.patch.object(
            test_module, "AnonCredsRevocation", autospec=True
        ) as MockAnonCredsRevocation:
            mock_issuer = MockAnonCredsRevocation.return_value
            mock_issuer.create_credential_w3c = mock.CoroutineMock(
                return_value=(expected_credential, cred_rev_id, dummy_registry)
            )

            # Call the method under test
            (cred_format, attachment) = await self.handler.issue_credential(
                cred_ex_record, retries=1
            )
            legacy_offer = await self.handler._prepare_legacy_offer(VCDI_OFFER, SCHEMA_ID)
            legacy_request = await self.handler._prepare_legacy_request(
                VCDI_CRED_REQ, CRED_DEF_ID
            )
            # Verify the mocked method was called with the expected parameters
            mock_issuer.create_credential_w3c.assert_called_once_with(
                legacy_offer,
                legacy_request,
                attr_values,
            )

            # Assert the results are as expected
            assert cred_format.attach_id == self.handler.format.api == attachment.ident
            assert attachment.data.base64
            assert attachment.content == {"credential": VCDI_CRED}

    @pytest.mark.skip(reason="AnonCreds-break")
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
            offers_attach=[AttachDecorator.data_base64(VCDI_OFFER, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(VCDI_CRED_REQ, ident="0")],
        )

        cred_ex_record = V20CredExRecordIndy(
            cred_ex_id="dummy-cxid",
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecordIndy.INITIATOR_SELF,
            role=V20CredExRecordIndy.ROLE_ISSUER,
            state=V20CredExRecordIndy.STATE_REQUEST_RECEIVED,
        )

        self.issuer.create_credential = mock.CoroutineMock(
            return_value=(json.dumps(VCDI_CRED), None)
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
                VCDI_OFFER,
                VCDI_CRED_REQ,
                attr_values,
                None,
                None,
            )

        # assert identifier match
        assert cred_format.attach_id == self.handler.format.api == attachment.ident

        # assert content of attachment is proposal data
        assert attachment.content == VCDI_CRED

        # assert data is encoded as base64
        assert attachment.data.base64

    async def test_match_sent_cred_def_id_error(self):
        tag_query = {"tag": "test_tag"}

        with self.assertRaises(V20CredFormatError) as context:
            await self.handler._match_sent_cred_def_id(tag_query)
        assert "Issuer has no operable cred def for proposal spec " in str(
            context.exception
        )

    async def test_store_credential(self):
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
            offers_attach=[AttachDecorator.data_base64(VCDI_OFFER, ident="0")],
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
            requests_attach=[AttachDecorator.data_base64(VCDI_CRED_REQ, ident="0")],
        )
        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.VC_DI.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(VCDI_CRED, ident="0")],
        )
        cred_ex_record = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            cred_issue=cred_issue.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
        )
        cred_id = "dummy-cred-id"

        # Define your mock credential definition
        mock_credential_definition_result = GetCredDefResult(
            credential_definition=CredDef(
                issuer_id=TEST_DID, schema_id=SCHEMA_ID, type="CL", tag="tag1", value={}
            ),
            credential_definition_id=CRED_DEF_ID,
            resolution_metadata={},
            credential_definition_metadata={},
        )
        mock_creds_registry = mock.MagicMock(AnonCredsRegistry, autospec=True)
        mock_creds_registry.get_credential_definition = mock.AsyncMock(
            return_value=mock_credential_definition_result
        )

        revocation_registry = RevRegDef(
            cred_def_id=CRED_DEF_ID,
            issuer_id=TEST_DID,
            tag="tag1",
            type="CL_ACCUM",
            value={},
        )

        mock_creds_registry.get_revocation_registry_definition = mock.AsyncMock(
            return_value=GetRevRegDefResult(
                revocation_registry=revocation_registry,
                revocation_registry_id="rr-id",
                resolution_metadata={},
                revocation_registry_metadata={},
            )
        )
        # Inject the MagicMock into the context
        self.profile.context.injector.bind_instance(
            AnonCredsRegistry, mock_creds_registry
        )
        self.profile = await create_test_profile(
            {
                "wallet.type": "askar-anoncreds",
            }
        )
        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_or_fetch_local_tails_path",
            mock.CoroutineMock(),
        ):
            with self.assertRaises(V20CredFormatError) as context:
                await self.handler.store_credential(cred_ex_record, cred_id)
            assert (
                "No credential exchange didcomm/ detail record found for cred ex id dummy-cxid"
                in str(context.exception)
            )

            record = V20CredExRecordIndy(
                cred_ex_indy_id="dummy-cxid",
                rev_reg_id="rr-id",
                cred_ex_id="dummy-cxid",
                cred_id_stored=cred_id,
                cred_request_metadata="dummy-metadata",
                cred_rev_id="0",
            )

            record.save = mock.CoroutineMock()
            self.handler.get_detail_record = mock.AsyncMock(return_value=record)
            with mock.patch.object(
                W3cCredential,
                "rev_reg_id",
                return_value="rr-id",
            ):
                with mock.patch.object(
                    AnonCredsHolder,
                    "store_credential_w3c",
                    mock.AsyncMock(),
                ) as mock_store_credential:
                    # Error case: no cred ex record found

                    await self.handler.store_credential(cred_ex_record, cred_id)

                    mock_store_credential.assert_called_once_with(
                        mock_credential_definition_result.credential_definition.serialize(),
                        VCDI_CRED["credential"],
                        record.cred_request_metadata,
                        None,
                        credential_id=cred_id,
                        rev_reg_def=revocation_registry.serialize(),
                    )

            with mock.patch.object(
                AnonCredsHolder,
                "store_credential_w3c",
                mock.AsyncMock(side_effect=AnonCredsHolderError),
            ) as mock_store_credential:
                with self.assertRaises(AnonCredsHolderError) as context:
                    await self.handler.store_credential(cred_ex_record, cred_id)
