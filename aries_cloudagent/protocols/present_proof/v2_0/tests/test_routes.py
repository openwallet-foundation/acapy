from copy import deepcopy
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from marshmallow import ValidationError
from time import time
from unittest.mock import ANY

from .....admin.request_context import AdminRequestContext
from .....indy.holder import IndyHolder
from .....indy.models.proof_request import IndyProofReqAttrSpecSchema
from .....indy.verifier import IndyVerifier
from .....ledger.base import BaseLedger
from .....storage.error import StorageNotFoundError
from .....storage.vc_holder.base import VCHolder
from .....storage.vc_holder.vc_record import VCRecord

from ...dif.pres_exch import SchemaInputDescriptor

from .. import routes as test_module
from ..messages.pres_format import V20PresFormat
from ..models.pres_exchange import V20PresExRecord

ISSUER_DID = "NcYxiDXkpYi6ov5FcYDi1e"
S_ID = f"{ISSUER_DID}:2:vidya:1.0"
CD_ID = f"{ISSUER_DID}:3:CL:{S_ID}:tag1"
RR_ID = f"{ISSUER_DID}:4:{CD_ID}:CL_ACCUM:0"
PROOF_REQ_NAME = "name"
PROOF_REQ_VERSION = "1.0"
PROOF_REQ_NONCE = "12345"

NOW = int(time())
INDY_PROOF_REQ = {
    "name": PROOF_REQ_NAME,
    "version": PROOF_REQ_VERSION,
    "nonce": PROOF_REQ_NONCE,
    "requested_attributes": {
        "0_player_uuid": {
            "name": "player",
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        },
        "1_screencapture_uuid": {
            "name": "screenCapture",
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        },
    },
    "requested_predicates": {
        "0_highscore_GE_uuid": {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
    },
}

DIF_PROOF_REQ = {
    "options": {
        "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
        "domain": "4jt78h47fh47",
    },
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
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
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


DIF_PRES_PROPOSAL = {
    "input_descriptors": [
        {
            "id": "citizenship_input_1",
            "name": "EU Driver's License",
            "group": ["A"],
            "schema": [
                {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
            ],
            "constraints": {
                "limit_disclosure": "required",
                "fields": [
                    {
                        "path": ["$.credentialSubject.givenName"],
                        "purpose": "The claim must be from one of the specified issuers",
                        "filter": {"type": "string", "enum": ["JOHN", "CAI"]},
                    }
                ],
            },
        }
    ]
}


class TestPresentProofRoutes(AsyncTestCase):
    def setUp(self):
        self.context = AdminRequestContext.test_context()
        self.profile = self.context.profile
        injector = self.profile.context.injector

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"value": {"revocation": {"...": "..."}}}
        )
        self.ledger.get_revoc_reg_def = async_mock.CoroutineMock(
            return_value={
                "ver": "1.0",
                "id": RR_ID,
                "revocDefType": "CL_ACCUM",
                "tag": RR_ID.split(":")[-1],
                "credDefId": CD_ID,
                "value": {
                    "IssuanceType": "ISSUANCE_BY_DEFAULT",
                    "maxCredNum": 1000,
                    "publicKeys": {"accumKey": {"z": "1 ..."}},
                    "tailsHash": "3MLjUFQz9x9n5u9rFu8Ba9C5bo4HNFjkPNc54jZPSNaZ",
                    "tailsLocation": "http://sample.ca/path",
                },
            }
        )
        self.ledger.get_revoc_reg_delta = async_mock.CoroutineMock(
            return_value=(
                {
                    "ver": "1.0",
                    "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1]},
                },
                NOW,
            )
        )
        self.ledger.get_revoc_reg_entry = async_mock.CoroutineMock(
            return_value=(
                {
                    "ver": "1.0",
                    "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1]},
                },
                NOW,
            )
        )
        injector.bind_instance(BaseLedger, self.ledger)

        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_validate(self):
        schema = test_module.V20PresProposalByFormatSchema()
        schema.validate_fields({"indy": {"attributes": [], "predicates": []}})
        schema.validate_fields({"dif": {"some_dif_criterion": "..."}})
        schema.validate_fields(
            {
                "indy": {"attributes": [], "predicates": []},
                "dif": {"some_dif_criterion": "..."},
            }
        )
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"veres-one": {"no": "support"}})

        schema = test_module.V20PresRequestByFormatSchema()
        schema.validate_fields({"indy": {"...": "..."}})
        schema.validate_fields({"dif": {"...": "..."}})
        schema.validate_fields({"indy": {"...": "..."}, "dif": {"...": "..."}})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"veres-one": {"no": "support"}})

        schema = test_module.V20PresSpecByFormatRequestSchema()
        schema.validate_fields({"indy": {"...": "..."}})
        schema.validate_fields({"dif": {"...": "..."}})
        schema.validate_fields({"indy": {"...": "..."}, "dif": {"...": "..."}})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"veres-one": {"no": "support"}})

    async def test_validate_proof_req_attr_spec(self):
        aspec = IndyProofReqAttrSpecSchema()
        aspec.validate_fields({"name": "attr0"})
        aspec.validate_fields(
            {
                "names": ["attr0", "attr1"],
                "restrictions": [{"attr::attr1::value": "my-value"}],
            }
        )
        aspec.validate_fields(
            {"name": "attr0", "restrictions": [{"schema_name": "preferences"}]}
        )
        with self.assertRaises(ValidationError):
            aspec.validate_fields({})
        with self.assertRaises(ValidationError):
            aspec.validate_fields({"name": "attr0", "names": ["attr1", "attr2"]})
        with self.assertRaises(ValidationError):
            aspec.validate_fields({"names": ["attr1", "attr2"]})
        with self.assertRaises(ValidationError):
            aspec.validate_fields({"names": ["attr0", "attr1"], "restrictions": []})
        with self.assertRaises(ValidationError):
            aspec.validate_fields({"names": ["attr0", "attr1"], "restrictions": [{}]})

    async def test_present_proof_list(self):
        self.request.query = {
            "thread_id": "thread_id_0",
            "connection_id": "conn_id_0",
            "role": "dummy",
            "state": "dummy",
        }

        mock_pres_ex_rec_inst = async_mock.MagicMock(
            serialize=async_mock.MagicMock(
                return_value={"thread_id": "sample-thread-id"}
            )
        )
        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.query = async_mock.CoroutineMock(
                return_value=[mock_pres_ex_rec_inst]
            )

            await test_module.present_proof_list(self.request)
            mock_response.assert_called_once_with(
                {"results": [mock_pres_ex_rec_inst.serialize.return_value]}
            )

    async def test_present_proof_list_x(self):
        self.request.query = {
            "thread_id": "thread_id_0",
            "connection_id": "conn_id_0",
            "role": "dummy",
            "state": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_list(self.request)

    async def test_present_proof_credentials_list_not_found(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad presentation exchange id)
            mock_pres_ex_rec_cls.retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_x(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
            "referent": "myReferent1",
        }
        self.request.query = {"extra_query": {}}
        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock(side_effect=test_module.IndyHolderError())
                )
            ),
        )
        mock_px_rec = async_mock.MagicMock(save_error_state=async_mock.CoroutineMock())

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_list_single_referent(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
            "referent": "myReferent1",
        }
        self.request.query = {"extra_query": {}}

        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock(return_value=returned_credentials)
                )
            ),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.return_value = async_mock.MagicMock(
                retrieve_by_id=async_mock.CoroutineMock()
            )

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(returned_credentials)

    async def test_present_proof_credentials_list_multiple_referents(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
            "referent": "myReferent1,myReferent2",
        }
        self.request.query = {"extra_query": {}}

        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock(return_value=returned_credentials)
                )
            ),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.return_value = async_mock.MagicMock(
                retrieve_by_id=async_mock.CoroutineMock()
            )

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(returned_credentials)

    async def test_present_proof_credentials_list_dif(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}

        returned_credentials = [
            async_mock.MagicMock(cred_value={"name": "Credential1"}),
            async_mock.MagicMock(cred_value={"name": "Credential2"}),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": DIF_PROOF_REQ},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": ANY},
                    {"name": "Credential2", "record_id": ANY},
                ]
            )

    async def test_present_proof_credentials_list_dif_one_of_filter(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}

        returned_credentials = [
            async_mock.MagicMock(
                cred_value={"name": "Credential1"}, record_id="test_1"
            ),
            async_mock.MagicMock(
                cred_value={"name": "Credential2"}, record_id="test_2"
            ),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )
        pres_request = deepcopy(DIF_PROOF_REQ)
        pres_request["presentation_definition"]["input_descriptors"][0]["schema"] = {
            "oneof_filter": [
                [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
                ],
                [{"uri": "https://www.w3.org/Test#Test"}],
            ]
        }
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": pres_request},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": "test_1"},
                    {"name": "Credential2", "record_id": "test_2"},
                ]
            )

    async def test_present_proof_credentials_dif_no_tag_query(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["input_descriptors"][0]["schema"][0][
            "required"
        ] = False
        test_pd["presentation_definition"]["input_descriptors"][0]["schema"][1][
            "required"
        ] = False
        returned_credentials = [
            async_mock.MagicMock(cred_value={"name": "Credential1"}),
            async_mock.MagicMock(cred_value={"name": "Credential2"}),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": ANY},
                    {"name": "Credential2", "record_id": ANY},
                ]
            )

    async def test_present_proof_credentials_single_ldp_vp_claim_format(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vp": {"proof_type": ["Ed25519Signature2018"]}
        }
        del test_pd["presentation_definition"]["input_descriptors"][0]["constraints"][
            "limit_disclosure"
        ]
        returned_credentials = [
            async_mock.MagicMock(cred_value={"name": "Credential1"}),
            async_mock.MagicMock(cred_value={"name": "Credential2"}),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": ANY},
                    {"name": "Credential2", "record_id": ANY},
                ]
            )

    async def test_present_proof_credentials_double_ldp_vp_claim_format(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vp": {"proof_type": ["BbsBlsSignature2020", "Ed25519Signature2018"]}
        }
        del test_pd["presentation_definition"]["input_descriptors"][0]["constraints"][
            "limit_disclosure"
        ]
        returned_credentials = [
            async_mock.MagicMock(cred_value={"name": "Credential1"}),
            async_mock.MagicMock(cred_value={"name": "Credential2"}),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record

            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": ANY},
                    {"name": "Credential2", "record_id": ANY},
                ]
            )

    async def test_present_proof_credentials_single_ldp_vp_error(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vp": {"proof_type": ["test"]}
        }
        del test_pd["presentation_definition"]["input_descriptors"][0]["constraints"][
            "limit_disclosure"
        ]
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(search_credentials=async_mock.CoroutineMock()),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_double_ldp_vp_error(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vp": {"proof_type": ["test1", "test2"]}
        }
        del test_pd["presentation_definition"]["input_descriptors"][0]["constraints"][
            "limit_disclosure"
        ]
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(search_credentials=async_mock.CoroutineMock()),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_list_limit_disclosure_no_bbs(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vp": {"proof_type": ["Ed25519Signature2018"]}
        }
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(search_credentials=async_mock.CoroutineMock()),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_no_ldp_vp(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["format"] = {
            "ldp_vc": {"proof_type": ["test"]}
        }
        del test_pd["presentation_definition"]["input_descriptors"][0]["constraints"][
            "limit_disclosure"
        ]
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(search_credentials=async_mock.CoroutineMock()),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_credentials_list_schema_uri(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}
        test_pd = deepcopy(DIF_PROOF_REQ)
        test_pd["presentation_definition"]["input_descriptors"][0]["schema"][0][
            "uri"
        ] = "https://example.org/test.json"
        test_pd["presentation_definition"]["input_descriptors"][0]["schema"].pop(1)
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": test_pd},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        returned_credentials = [
            async_mock.MagicMock(cred_value={"name": "Credential1"}),
            async_mock.MagicMock(cred_value={"name": "Credential2"}),
        ]
        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=returned_credentials
                        )
                    )
                )
            ),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
            await test_module.present_proof_credentials_list(self.request)
            mock_response.assert_called_once_with(
                [
                    {"name": "Credential1", "record_id": ANY},
                    {"name": "Credential2", "record_id": ANY},
                ]
            )

    async def test_present_proof_credentials_list_dif_error(self):
        self.request.match_info = {
            "pres_ex_id": "123-456-789",
        }
        self.request.query = {"extra_query": {}}

        self.profile.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock()
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            VCHolder,
            async_mock.MagicMock(
                search_credentials=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            side_effect=test_module.StorageNotFoundError()
                        )
                    )
                )
            ),
        )
        record = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": DIF_PROOF_REQ},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                mock_pres_ex_rec_cls.retrieve_by_id.return_value = record
                await test_module.present_proof_credentials_list(self.request)

    async def test_present_proof_retrieve(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_pres_ex_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={"thread_id": "sample-thread-id"}
                    )
                )
            )

            await test_module.present_proof_retrieve(self.request)
            mock_response.assert_called_once_with({"thread_id": "sample-thread-id"})

    async def test_present_proof_retrieve_not_found(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.present_proof_retrieve(self.request)

    async def test_present_proof_retrieve_x(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        mock_pres_ex_rec_inst = async_mock.MagicMock(
            connection_id="abc123",
            thread_id="thid123",
            serialize=async_mock.MagicMock(side_effect=test_module.BaseModelError()),
            save_error_state=async_mock.CoroutineMock(),
        )
        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls:
            mock_pres_ex_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_retrieve(self.request)

    async def test_present_proof_send_proposal(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy-conn-id",
                "presentation_proposal": {
                    V20PresFormat.Format.INDY.api: INDY_PROOF_REQ
                },
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(is_ready=True)
            )
            mock_px_rec_inst = async_mock.MagicMock()
            mock_pres_mgr.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock(return_value=mock_px_rec_inst)
            )

            await test_module.present_proof_send_proposal(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_send_proposal_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec:
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_proposal(self.request)

    async def test_present_proof_send_proposal_not_ready(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresProposal", autospec=True
        ) as mock_proposal:
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(is_ready=False)
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.present_proof_send_proposal(self.request)

    async def test_present_proof_send_proposal_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(
                            side_effect=test_module.StorageError()
                        ),
                        save_error_state=async_mock.CoroutineMock(),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_proposal(self.request)

    async def test_present_proof_create_request(self):
        indy_proof_req = deepcopy(INDY_PROOF_REQ)
        indy_proof_req.pop("nonce")  # exercise _add_nonce()

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "comment": "dummy",
                "presentation_request": {V20PresFormat.Format.INDY.api: indy_proof_req},
            }
        )

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresRequest", autospec=True
        ) as mock_pres_request, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                )
            )
            mock_pres_mgr_inst = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=mock_px_rec_inst
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_create_request(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_create_request_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "comment": "dummy",
                "presentation_request": {V20PresFormat.Format.INDY.api: INDY_PROOF_REQ},
            }
        )

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresRequest", autospec=True
        ) as mock_pres_request, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock()
            mock_pres_mgr_inst = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(
                            side_effect=test_module.StorageError()
                        ),
                        save_error_state=async_mock.CoroutineMock(),
                    )
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_create_request(self.request)

    async def test_present_proof_send_free_request(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "presentation_request": {V20PresFormat.Format.INDY.api: INDY_PROOF_REQ},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresRequest", autospec=True
        ) as mock_pres_request, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_pres_ex_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock()
            mock_px_rec_inst = async_mock.MagicMock(
                serialize=async_mock.MagicMock({"thread_id": "sample-thread-id"})
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=mock_px_rec_inst
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_send_free_request(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_send_free_request_not_found(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": "dummy"}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec_cls:
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_free_request(self.request)

    async def test_present_proof_send_free_request_not_ready(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": "dummy", "proof_request": {}}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", async_mock.MagicMock()
        ) as mock_conn_rec_cls:
            mock_conn_rec_inst = async_mock.MagicMock(is_ready=False)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.present_proof_send_free_request(self.request)

    async def test_present_proof_send_free_request_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "presentation_request": {V20PresFormat.Format.INDY.api: INDY_PROOF_REQ},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresRequest", autospec=True
        ) as mock_pres_request, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_conn_rec_inst = async_mock.MagicMock()
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )
            mock_px_rec_inst = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                )
            )
            mock_pres_mgr_inst = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(
                            side_effect=test_module.StorageError()
                        ),
                        save_error_state=async_mock.CoroutineMock(),
                    )
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_free_request(self.request)

    async def test_present_proof_send_bound_request(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        self.profile.context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PROPOSAL_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_inst = async_mock.MagicMock(
                is_ready=True,
            )
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )
            mock_pres_request = async_mock.MagicMock()

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_bound_request=async_mock.CoroutineMock(
                    return_value=(mock_px_rec_inst, mock_pres_request)
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_send_bound_request(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_send_bound_request_not_found(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        self.profile.context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PROPOSAL_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_bound_request(self.request)

    async def test_present_proof_send_bound_request_not_ready(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        self.profile.context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PROPOSAL_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_inst = async_mock.MagicMock(
                is_ready=False,
            )
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.present_proof_send_bound_request(self.request)

    async def test_present_proof_send_bound_request_px_rec_not_found(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError("no such record")
            )
            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.present_proof_send_bound_request(self.request)
            assert "no such record" in str(context.exception)

    async def test_present_proof_send_bound_request_bad_state(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        self.profile.context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_DONE,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_bound_request(self.request)

    async def test_present_proof_send_bound_request_x(self):
        self.request.json = async_mock.CoroutineMock(return_value={"trace": False})
        self.request.match_info = {"pres_ex_id": "dummy"}

        self.profile.context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PROPOSAL_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
                save_error_state=async_mock.CoroutineMock(),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_inst = async_mock.MagicMock(
                is_ready=True,
            )
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_bound_request=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_bound_request(self.request)

    async def test_present_proof_send_presentation(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_REQUEST_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_pres=async_mock.CoroutineMock(
                    return_value=(mock_px_rec_inst, async_mock.MagicMock())
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_send_presentation(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_send_presentation_dif(self):
        proof_req = deepcopy(DIF_PROOF_REQ)
        proof_req["issuer_id"] = "test123"
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "dif": proof_req,
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_REQUEST_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_pres=async_mock.CoroutineMock(
                    return_value=(mock_px_rec_inst, async_mock.MagicMock())
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_send_presentation(self.request)
            mock_response.assert_called_once_with(
                mock_px_rec_inst.serialize.return_value
            )

    async def test_present_proof_send_presentation_dif_error(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"dif": DIF_PROOF_REQ}
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        px_rec_instance = V20PresExRecord(
            state="request-received",
            role="prover",
            pres_proposal=None,
            pres_request={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/request-presentation",
                "@id": "6ae00c6c-87fa-495a-b546-5f5953817c92",
                "comment": "string",
                "formats": [
                    {
                        "attach_id": "dif",
                        "format": "dif/presentation-exchange/definitions@v1.0",
                    }
                ],
                "request_presentations~attach": [
                    {
                        "@id": "dif",
                        "mime-type": "application/json",
                        "data": {"json": DIF_PROOF_REQ},
                    }
                ],
                "will_confirm": True,
            },
            pres=None,
            verified=None,
            auto_present=False,
            error_msg=None,
        )
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=px_rec_instance
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_pres=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError()
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_presentation(self.request)
                mock_response.assert_called_once_with(px_rec_instance.serialize())

    async def test_present_proof_send_presentation_px_rec_not_found(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError("no such record")
            )

            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.present_proof_send_presentation(self.request)
            assert "no such record" in str(context.exception)

    async def test_present_proof_send_presentation_not_found(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_REQUEST_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_presentation(self.request)

    async def test_present_proof_send_presentation_not_ready(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_REQUEST_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(is_ready=False)
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.present_proof_send_presentation(self.request)

    async def test_present_proof_send_presentation_bad_state(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id=None,
                state=test_module.V20PresExRecord.STATE_DONE,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_send_presentation(self.request)

    async def test_present_proof_send_presentation_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "indy": {
                    "comment": "dummy",
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                }
            }
        )
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        self.profile.context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_REQUEST_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
                save_error_state=async_mock.CoroutineMock(),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                create_pres=async_mock.CoroutineMock(
                    side_effect=[
                        test_module.LedgerError(),
                        test_module.StorageError(),
                    ]
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            with self.assertRaises(test_module.web.HTTPBadRequest):  # ledger error
                await test_module.present_proof_send_presentation(self.request)
            with self.assertRaises(test_module.web.HTTPBadRequest):  # storage error
                await test_module.present_proof_send_presentation(self.request)

    async def test_present_proof_verify_presentation(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PRESENTATION_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                verify_pres=async_mock.CoroutineMock(return_value=mock_px_rec_inst)
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            await test_module.present_proof_verify_presentation(self.request)
            mock_response.assert_called_once_with({"thread_id": "sample-thread-id"})

    async def test_present_proof_verify_presentation_px_rec_not_found(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError("no such record")
            )

            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.present_proof_verify_presentation(self.request)
            assert "no such record" in str(context.exception)

    async def test_present_proof_verify_presentation_bad_state(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_DONE,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_verify_presentation(self.request)

    async def test_present_proof_verify_presentation_x(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_cls, async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec_cls, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec_inst = async_mock.MagicMock(
                connection_id="dummy",
                state=test_module.V20PresExRecord.STATE_PRESENTATION_RECEIVED,
                serialize=async_mock.MagicMock(
                    return_value={"thread_id": "sample-thread-id"}
                ),
                save_error_state=async_mock.CoroutineMock(),
            )
            mock_px_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_px_rec_inst
            )
            mock_conn_rec_inst = async_mock.MagicMock(is_ready=True)
            mock_conn_rec_cls.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_conn_rec_inst
            )

            mock_pres_mgr_inst = async_mock.MagicMock(
                verify_pres=async_mock.CoroutineMock(
                    side_effect=[
                        test_module.LedgerError(),
                        test_module.StorageError(),
                    ]
                )
            )
            mock_pres_mgr_cls.return_value = mock_pres_mgr_inst

            with self.assertRaises(test_module.web.HTTPBadRequest):  # ledger error
                await test_module.present_proof_verify_presentation(self.request)
            with self.assertRaises(test_module.web.HTTPBadRequest):  # storage error
                await test_module.present_proof_verify_presentation(self.request)

    async def test_present_proof_problem_report(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'No! Problem.'"}
        )
        self.request.match_info = {"pres_ex_id": "dummy"}
        magic_report = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "problem_report_for_record", async_mock.MagicMock()
        ) as mock_problem_report, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    save_error_state=async_mock.CoroutineMock()
                )
            )
            mock_problem_report.return_value = magic_report

            await test_module.present_proof_problem_report(self.request)

            self.request["outbound_message_router"].assert_awaited_once()
            mock_response.assert_called_once_with({})

    async def test_present_proof_problem_report_bad_pres_ex_id(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'No! Problem.'"}
        )
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.present_proof_problem_report(self.request)

    async def test_present_proof_problem_report_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'No! Problem.'"}
        )
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr_cls, async_mock.patch.object(
            test_module, "problem_report_for_record", async_mock.MagicMock()
        ) as mock_problem_report, async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_problem_report(self.request)

    async def test_present_proof_remove(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=test_module.V20PresExRecord.STATE_DONE,
                    connection_id="dummy",
                    delete_record=async_mock.CoroutineMock(),
                )
            )

            await test_module.present_proof_remove(self.request)
            mock_response.assert_called_once_with({})

    async def test_present_proof_remove_px_rec_not_found(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.present_proof_remove(self.request)

    async def test_present_proof_remove_x(self):
        self.request.match_info = {"pres_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20PresExRecord", autospec=True
        ) as mock_px_rec:
            mock_px_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=test_module.V20PresExRecord.STATE_DONE,
                    connection_id="dummy",
                    delete_record=async_mock.CoroutineMock(
                        side_effect=test_module.StorageError()
                    ),
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.present_proof_remove(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]

    def test_format_attach_dif(self):
        req_dict = {"dif": DIF_PROOF_REQ}
        pres_req_dict = test_module._formats_attach(
            by_format=req_dict,
            msg_type="present-proof/2.0/request-presentation",
            spec="request_presentations",
        )
        assert pres_req_dict.get("formats")[0].attach_id == "dif"
        assert (
            pres_req_dict.get("request_presentations_attach")[0].data.json_
            == DIF_PROOF_REQ
        )

    async def test_process_vcrecords_return_list(self):
        cred_list = [
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
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
                record_id="test1",
            ),
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
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
                record_id="test2",
            ),
        ]
        record_ids = {"test1"}
        (
            returned_cred_list,
            returned_record_ids,
        ) = await test_module.process_vcrecords_return_list(cred_list, record_ids)
        assert len(returned_cred_list) == 1
        assert len(returned_record_ids) == 2
        assert returned_cred_list[0].record_id == "test2"

    async def test_retrieve_uri_list_from_schema_filter(self):
        test_schema_filter = [
            [
                SchemaInputDescriptor(uri="test123"),
                SchemaInputDescriptor(uri="test321", required=True),
            ]
        ]
        test_one_of_uri_groups = await test_module.retrieve_uri_list_from_schema_filter(
            test_schema_filter
        )
        assert test_one_of_uri_groups == [["test123", "test321"]]

    async def test_send_presentation_no_specification(self):
        self.request.json = async_mock.CoroutineMock(return_value={"comment": "test"})
        self.request.match_info = {
            "pres_ex_id": "dummy",
        }
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.present_proof_send_presentation(self.request)

    async def test_v20presentationsendreqschema(self):
        test_input = {
            "comment": "string",
            "connection_id": "631522e9-ca17-4c88-9a4c-d1cad35e463a",
            "presentation_request": {
                "dif": {
                    "_schema": [
                        {
                            "uri": "https://www.w3.org/2018/credentials/#VerifiableCredential"
                        }
                    ],
                    "presentation_definition": {
                        "format": {"ldp_vp": {"proof_type": "BbsBlsSignature2020"}},
                        "id": "fa2c4a76-c7bd-4313-a0f8-d9f5979c1fd2",
                        "input_descriptors": [
                            {
                                "schema": [
                                    {
                                        "uri": "https://www.w3.org/2018/credentials/#VerifiableCredential"
                                    }
                                ],
                                "constraints": {
                                    "fields": [
                                        {
                                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                            "path": ["$.credentialSubject.id"],
                                        }
                                    ],
                                    "is_holder": [
                                        {
                                            "directive": "required",
                                            "field_id": [
                                                "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                                            ],
                                        }
                                    ],
                                    "limit_disclosure": "required",
                                },
                                "id": "XXXXXXX",
                                "name": "XXXXXXX",
                            }
                        ],
                    },
                }
            },
        }
        with self.assertRaises(TypeError):
            test_module.V20PresSendRequestRequestSchema.load(test_input)
