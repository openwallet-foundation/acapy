from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.decorators.attach_decorator import AttachDecorator

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_20_REQUEST

from .. import cred_request as test_module
from ..cred_format import V20CredFormat
from ..cred_request import V20CredRequest


class TestV20CredRequest(AsyncTestCase):
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

    dif_cred_req = {
        "credential-manifest": {
            "issuer": "did:example:123",
            "credential": {
                "name": "Banana sticker",
                "schema": "...",
            },
        }
    }

    async def test_init_type(self):
        """Test initializer and type."""
        cred_request = V20CredRequest(
            comment="Test",
            formats=[
                V20CredFormat(
                    attach_id="abc",
                    format_=V20CredFormat.Format.INDY,
                )
            ],
            requests_attach=[
                AttachDecorator.data_base64(
                    mapping=TestV20CredRequest.indy_cred_req,
                    ident="abc",
                )
            ],
        )
        assert (
            cred_request.requests_attach[0].content == TestV20CredRequest.indy_cred_req
        )
        assert cred_request.cred_request() == TestV20CredRequest.indy_cred_req
        assert cred_request._type == DIDCommPrefix.qualify_current(CRED_20_REQUEST)

    async def test_deserialize(self):
        """Test deserialization."""
        obj = TestV20CredRequest.indy_cred_req

        with async_mock.patch.object(
            test_module.V20CredRequestSchema, "load", async_mock.MagicMock()
        ) as mock_load:
            cred_request = V20CredRequest.deserialize(obj)
            mock_load.assert_called_once_with(obj)

            assert cred_request is mock_load.return_value

    async def test_serialize(self):
        """Test serialization."""
        cred_request = V20CredRequest(
            comment="Test",
            formats=[
                V20CredFormat(
                    attach_id="abc",
                    format_=V20CredFormat.Format.INDY,
                )
            ],
            requests_attach=[
                AttachDecorator.data_base64(
                    ident="abc",
                    mapping=TestV20CredRequest.indy_cred_req,
                )
            ],
        )

        with async_mock.patch.object(
            test_module.V20CredRequestSchema, "dump", async_mock.MagicMock()
        ) as mock_dump:
            cred_request_dict = cred_request.serialize()
            mock_dump.assert_called_once_with(cred_request)

            assert cred_request_dict is mock_dump.return_value


class TestV20CredRequestSchema(AsyncTestCase):
    """Test credential request schema"""

    async def test_make_model(self):
        """Test making model."""
        cred_request = V20CredRequest(
            comment="Test",
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=V20CredFormat.Format.INDY,
                ),
                V20CredFormat(
                    attach_id="dif-json",
                    format_=V20CredFormat.Format.DIF,
                ),
            ],
            requests_attach=[
                AttachDecorator.data_base64(
                    ident="indy", mapping=TestV20CredRequest.indy_cred_req
                ),
                AttachDecorator.data_json(
                    ident="dif-json", mapping=TestV20CredRequest.dif_cred_req
                ),
            ],
        )

        assert (
            cred_request.cred_request(V20CredFormat.Format.INDY)
            == TestV20CredRequest.indy_cred_req
        )
        assert (
            cred_request.cred_request(V20CredFormat.Format.DIF)
            == TestV20CredRequest.dif_cred_req
        )
        data = cred_request.serialize()
        model_instance = V20CredRequest.deserialize(data)
        assert isinstance(model_instance, V20CredRequest)

        cred_request = V20CredRequest(
            comment="Test",
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=V20CredFormat.Format.INDY,
                ),
                V20CredFormat(
                    attach_id="dif-links",
                    format_=V20CredFormat.Format.DIF,
                ),
            ],
            requests_attach=[
                AttachDecorator.data_base64(
                    ident="indy", mapping=TestV20CredRequest.indy_cred_req
                ),
                AttachDecorator.data_links(
                    ident="dif-links",
                    links="http://10.20.30.40/cred-req.json",
                ),
            ],
        )
        assert cred_request.cred_request(V20CredFormat.Format.DIF) == [
            "http://10.20.30.40/cred-req.json"
        ]
