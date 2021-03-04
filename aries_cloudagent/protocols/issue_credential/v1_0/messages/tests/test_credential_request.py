from unittest import mock, TestCase

from ......messaging.decorators.attach_decorator import AttachDecorator

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACH_DECO_IDS, CREDENTIAL_REQUEST, PROTOCOL_PACKAGE

from ..credential_request import CredentialRequest


class TestCredentialRequest(TestCase):
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

    cred_req = CredentialRequest(
        comment="Test",
        requests_attach=[
            AttachDecorator.data_base64(
                mapping=indy_cred_req,
                ident=ATTACH_DECO_IDS[CREDENTIAL_REQUEST],
            )
        ],
    )

    def test_init(self):
        """Test initializer"""
        credential_request = CredentialRequest(
            comment="Test",
            requests_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_cred_req,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_REQUEST],
                )
            ],
        )
        assert credential_request.requests_attach[0].content == self.indy_cred_req
        assert credential_request.indy_cred_req(0) == self.indy_cred_req

    def test_type(self):
        """Test type"""
        credential_request = CredentialRequest(
            comment="Test",
            requests_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_cred_req,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_REQUEST],
                )
            ],
        )

        assert credential_request._type == DIDCommPrefix.qualify_current(
            CREDENTIAL_REQUEST
        )

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "credential_request.CredentialRequestSchema.load"
    )
    def test_deserialize(self, mock_credential_request_schema_load):
        """
        Test deserialize
        """
        obj = self.indy_cred_req

        credential_request = CredentialRequest.deserialize(obj)
        mock_credential_request_schema_load.assert_called_once_with(obj)

        assert credential_request is mock_credential_request_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages."
        "credential_request.CredentialRequestSchema.dump"
    )
    def test_serialize(self, mock_credential_request_schema_dump):
        """
        Test serialization.
        """
        credential_request = CredentialRequest(
            comment="Test",
            requests_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_cred_req,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_REQUEST],
                )
            ],
        )

        credential_request_dict = credential_request.serialize()
        mock_credential_request_schema_dump.assert_called_once_with(credential_request)

        assert (
            credential_request_dict is mock_credential_request_schema_dump.return_value
        )


class TestCredentialRequestSchema(TestCase):
    """Test credential cred request schema"""

    credential_request = CredentialRequest(
        comment="Test",
        requests_attach=[
            AttachDecorator.data_base64(TestCredentialRequest.indy_cred_req)
        ],
    )

    def test_make_model(self):
        """Test making model."""
        data = self.credential_request.serialize()
        model_instance = CredentialRequest.deserialize(data)
        assert isinstance(model_instance, CredentialRequest)
