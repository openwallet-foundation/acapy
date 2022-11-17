from asynctest import TestCase as AsyncTestCase

from aries_cloudagent.protocols.issue_credential.v3_0.messages.cred_body import (
    V30CredBody,
)

from ......messaging.decorators.attach_decorator_didcomm_v2_cred import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, CRED_30_REQUEST

from ..cred_format import V30CredFormat
from ..cred_request import V30CredRequest


class TestV30CredRequest(AsyncTestCase):
    """Credential request tests"""

    indy_cred_req = {
        "nonce": "1017762706737386703693758",
        "prover_did": "GMm4vMw8LLrLJjp81kRRLp",
        "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        "blinded_ms": {
            "u": "83907504917598709544715660183444547664806528194879236493704185267249518487609477830252206438464922282419526404954032744426656836343614241707982523911337758117991524606767981934822739259321023980818911648706424625657217291525111737996606024710795596961607334766957629765398381678917329471919374676824400143394472619220909211861028497009707890651887260349590274729523062264675018736459760546731362496666872299645586181905130659944070279943157241097916683504866583173110187429797028853314290183583689656212022982000994142291014801654456172923356395840313420880588404326139944888917762604275764474396403919497783080752861",
            "ur": "1 2422A7A25A9AB730F3399C77C28E1F6E02BB94A2C07D245B28DC4EE33E33DE49 1 1EF3FBD36FBA7510BDA79386508C0A84A33DF4171107C22895ACAE4FA4499F02 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
            "hidden_attributes": ["master_secret"],
            "committed_attributes": {},
        },
        "blinded_ms_correctness_proof": {
            "c": "77782990462020711078900471139684606615516190979556618670020830699801678914552",
            "v_dash_cap": "1966215015532422356590954855080129096516569112935438312989092847889400013191094311374123910677667707922694722167856889267996544544770134106600289624974901761453909338477897555013062690166110508298265469948048257876547569520215226798025984795668101468265482570744011744194025718081101032551943108999422057478928838218205736972438022128376728526831967897105301274481454020377656694232901381674223529320224276009919370080174601226836784570762698964476355045131401700464714725647784278935633253472872446202741297992383148244277451017022036452203286302631768247417186601621329239603862883753434562838622266122331169627284313213964584034951472090601638790603966977114416216909593408778336960753110805965734708636782885161632",
            "m_caps": {
                "master_secret": "1932933391026030434402535597188163725022560167138754201841873794167337347489231254032687761158191503499965986291267527620598858412377279828812688105949083285487853357240244045442"
            },
            "r_caps": {},
        },
    }

    ld_proof_cred_req = {
        "credential": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "credentialSubject": {"test": "key"},
            "issuanceDate": "2021-04-12",
            "issuer": "did:sov:something",
        },
        "options": {"proofType": "Ed25519Signature2018"},
    }

    CRED_REQUEST = V30CredRequest(
        _body=V30CredBody(comment="Test"),
        attachments=[
            AttachDecorator.data_base64(
                ident="indy",
                mapping=indy_cred_req,
                format=V30CredFormat(
                    format_=ATTACHMENT_FORMAT[CRED_30_REQUEST][
                        V30CredFormat.Format.INDY.api
                    ],
                ),
            )
        ],
    )

    async def test_init_type(self):
        """Test initializer and type."""
        assert (
            TestV30CredRequest.CRED_REQUEST.attachments[0].content
            == TestV30CredRequest.indy_cred_req
        )

        assert TestV30CredRequest.CRED_REQUEST._type == DIDCommPrefix.qualify_current(
            CRED_30_REQUEST
        )

    async def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_cred_req = V30CredRequest(
            _body=V30CredBody(comment="Test"),
            attachments=[
                AttachDecorator.data_base64(
                    ident="not_indy",
                    mapping=TestV30CredRequest.indy_cred_req,
                    format=V30CredFormat(attach_id="not_indy", format_="not_indy"),
                )
            ],
        )
        assert x_cred_req.attachment() is None

    async def test_serde(self):
        """Test de/serialization."""
        obj = TestV30CredRequest.CRED_REQUEST.serialize()

        cred_request = V30CredRequest.deserialize(obj)
        assert type(cred_request) == V30CredRequest

        obj["attachments"][0]["data"]["base64"] = "eyJub3QiOiAiaW5keSJ9"
        with self.assertRaises(BaseModelError):
            V30CredRequest.deserialize(obj)

        obj["attachments"][0]["id"] = "xxx"
        with self.assertRaises(BaseModelError):
            V30CredRequest.deserialize(obj)

        obj["attachments"].append(  # more attachments than formats
            {
                "id": "def",
                "media-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                "format": "",
            }
        )
        with self.assertRaises(BaseModelError):
            V30CredRequest.deserialize(obj)

        obj = cred_request.serialize()
        obj["attachments"].append(
            {
                "id": "not_indy",
                "media-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                "format": "<V30CredFormat(format_='not_indy')>",
            }
        )
        V30CredRequest.deserialize(obj)


class TestV30CredRequestSchema(AsyncTestCase):
    """Test credential request schema"""

    async def test_make_model(self):
        """Test making model."""
        cred_request = V30CredRequest(
            _body=V30CredBody(comment="Test"),
            attachments=[
                AttachDecorator.data_base64(
                    ident="indy",
                    mapping=TestV30CredRequest.indy_cred_req,
                    format=V30CredFormat(
                        attach_id="indy",
                        format_=ATTACHMENT_FORMAT[CRED_30_REQUEST][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                ),
                AttachDecorator.data_json(
                    ident="ld-proof-json",
                    mapping=TestV30CredRequest.ld_proof_cred_req,
                    format=V30CredFormat(
                        attach_id="ld-proof-json",
                        format_=ATTACHMENT_FORMAT[CRED_30_REQUEST][
                            V30CredFormat.Format.LD_PROOF.api
                        ],
                    ),
                ),
            ],
        )

        assert (
            cred_request.attachment(V30CredFormat.Format.INDY)
            == TestV30CredRequest.indy_cred_req
        )
        assert (
            cred_request.attachment(V30CredFormat.Format.LD_PROOF)
            == TestV30CredRequest.ld_proof_cred_req
        )
        data = cred_request.serialize()
        model_instance = V30CredRequest.deserialize(data)
        assert isinstance(model_instance, V30CredRequest)

        cred_request = V30CredRequest(
            _body=V30CredBody(comment="Test"),
            attachments=[
                AttachDecorator.data_base64(
                    ident="indy",
                    mapping=TestV30CredRequest.indy_cred_req,
                    format=V30CredFormat(
                        attach_id="indy",
                        format_=ATTACHMENT_FORMAT[CRED_30_REQUEST][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                ),
                AttachDecorator.data_links(
                    ident="ld-proof-links",
                    links="http://10.20.30.40/cred-req.json",
                    sha256="00000000000000000000000000000000",
                    format=V30CredFormat(
                        attach_id="ld-proof-links",
                        format_=ATTACHMENT_FORMAT[CRED_30_REQUEST][
                            V30CredFormat.Format.LD_PROOF.api
                        ],
                    ),
                ),
            ],
        )
        assert cred_request.attachment(V30CredFormat.Format.LD_PROOF) == (
            ["http://10.20.30.40/cred-req.json"],
            "00000000000000000000000000000000",
        )
