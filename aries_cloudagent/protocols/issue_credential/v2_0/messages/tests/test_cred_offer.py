from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, CRED_20_OFFER

from .. import cred_offer as test_module
from ..cred_format import V20CredFormat
from ..cred_offer import V20CredOffer
from ..inner.cred_preview import V20CredAttrSpec, V20CredPreview


class TestV20CredOffer(AsyncTestCase):
    """Credential offer tests"""

    indy_offer = {
        "nonce": "614100168443907415054289",
        "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:drinks:1.0",
        "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        "key_correctness_proof": {
            "c": "56585275561905717161839952743647026395542989876162452893531670700564212393854",
            "xz_cap": "287165348340975789727971384349378142287959058342225940074538845935436773874329328991029519089234724427434486533815831859470220965864684738156552672305499237703498538513271159520247291220966466227432832227063850459130839372368207180055849729905609985998538537568736869293407524473496064816314603497171002962615258076622463931743189286900496109205216280607630768503576692684508445827948798897460776289403908388023698817549732288585499518794247355928287227786391839285875542402023633857234040392852972008208415080178060364227401609053629562410235736217349229809414782038441992275607388974250885028366550369268002576993725278650846144639865881671599246472739142902676861561148712912969364530598265",
            "xr_cap": [
                [
                    "member",
                    "247173988424242283128308731284354519593625104582055668969315003963838548670841899501658349312938942946846730152870858369236571789232183841781453957957720697180067746500659257059976519795874971348181945469064991738990738845965440847535223580150468375375443512237424530837415294161162638683584221123453778375487245671372772618360172541002473454666729113558205280977594339672398197686260680189972481473789054636358472310216645491588945137379027958712059669609528877404178425925715596671339305959202588832885973524555444251963470084399490131160758976923444260763440975941005911948597957705824445435191054260665559130246488082450660079956928491647323363710347167509227696874201965902602039122291827",
                ],
                [
                    "favourite",
                    "1335045667644070498565118732156146549025899560440568943935771536511299164006020730238478605099548137764051990321413418863325926730012675851687537953795507658228985382833693223549386078823801188511091609027561372137859781602606173745112393410558404328055415428275164533367998547196095783458226529569321865083846885509205360165413682408429660871664533434140200342530874654054024409641491095797032894595844264175356021739370667850887453108137634226023771337973520900908849320630756049969052968900455735023806005098461831167599998292029791540116613937132049776519811961709679592741659868352478832873910002910063294074562896887581629929595271513565238416621119418443383796085468376565042025935483490",
                ],
                [
                    "master_secret",
                    "1033992860010367458372180504097559955661066772142722707045156268794833109485917658718054000138242001598760494274716663669095123169580783916372365989852993328621834238281615788751278692675115165487417933883883618299385468584923910731758768022514670608541825229491053331942365151645754250522222493603795702384546708563091580112967031435038732735155283423684631622768416201085577137158105343396606143962017453945220908112975903537378485103755718950361047334234687103399968712220979025991673471498636490232494897885460464490635716242509247751966176791851396526210422140145723375747195416033531994076204650208879292521201294795264925045126704368284107432921974127792914580116411247536542717749670349",
                ],
            ],
        },
    }

    preview = V20CredPreview(
        attributes=V20CredAttrSpec.list_plain(
            {"member": "James Bond", "favourite": "martini"}
        )
    )

    CRED_OFFER = V20CredOffer(
        comment="shaken, not stirred",
        credential_preview=preview,
        formats=[
            V20CredFormat(
                attach_id="indy",
                format_=ATTACHMENT_FORMAT[CRED_20_OFFER][V20CredFormat.Format.INDY.api],
            )
        ],
        offers_attach=[
            AttachDecorator.data_base64(
                mapping=indy_offer,
                ident="indy",
            )
        ],
    )

    async def test_init_type(self):
        """Test initializer and type."""
        assert (
            TestV20CredOffer.CRED_OFFER.credential_preview == TestV20CredOffer.preview
        )
        assert (
            TestV20CredOffer.CRED_OFFER.offers_attach[0].content
            == TestV20CredOffer.indy_offer
        )
        assert TestV20CredOffer.CRED_OFFER.attachment() == TestV20CredOffer.indy_offer
        assert TestV20CredOffer.CRED_OFFER._type == DIDCommPrefix.qualify_current(
            CRED_20_OFFER
        )

    async def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_cred_offer = V20CredOffer(
            comment="Test",
            formats=[V20CredFormat(attach_id="not_indy", format_="not_indy")],
            offers_attach=[
                AttachDecorator.data_base64(
                    ident="not_indy", mapping=TestV20CredOffer.CRED_OFFER.serialize()
                )
            ],
        )
        assert x_cred_offer.attachment() is None

    async def test_serde(self):
        """Test de/serialization."""
        obj = TestV20CredOffer.CRED_OFFER.serialize()

        cred_offer = V20CredOffer.deserialize(obj)
        assert type(cred_offer) == V20CredOffer

        obj["offers~attach"][0]["data"]["base64"] = "eyJub3QiOiAiaW5keSJ9"
        with self.assertRaises(BaseModelError):
            V20CredOffer.deserialize(obj)

        obj["offers~attach"][0]["@id"] = "xxx"
        with self.assertRaises(BaseModelError):
            V20CredOffer.deserialize(obj)

        obj["offers~attach"].append(  # more attachments than formats
            {
                "@id": "not_indy",
                "mime-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
            }
        )
        with self.assertRaises(BaseModelError):
            V20CredOffer.deserialize(obj)

        cred_offer.formats.append(  # unknown format: no validation
            V20CredFormat(
                attach_id="not_indy",
                format_="not_indy",
            )
        )
        obj = cred_offer.serialize()
        obj["offers~attach"].append(
            {
                "@id": "not_indy",
                "mime-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
            }
        )
        V20CredOffer.deserialize(obj)


class TestV20CredOfferSchema(AsyncTestCase):
    """Test credential cred offer schema"""

    async def test_make_model(self):
        """Test making model."""
        cred_offer = V20CredOffer(
            comment="shaken, not stirred",
            credential_preview=TestV20CredOffer.preview,
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            offers_attach=[
                AttachDecorator.data_base64(
                    mapping=TestV20CredOffer.indy_offer,
                    ident="indy",
                )
            ],
        )

        data = cred_offer.serialize()
        model_instance = V20CredOffer.deserialize(data)
        assert isinstance(model_instance, V20CredOffer)
