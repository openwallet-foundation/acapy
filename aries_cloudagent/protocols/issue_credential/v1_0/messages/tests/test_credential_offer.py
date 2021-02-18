from unittest import mock, TestCase

from ......messaging.decorators.attach_decorator import AttachDecorator

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACH_DECO_IDS, CREDENTIAL_OFFER, PROTOCOL_PACKAGE
from ..credential_offer import CredentialOffer
from ..inner.credential_preview import CredAttrSpec, CredentialPreview


class TestCredentialOffer(TestCase):
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
    preview = CredentialPreview(
        attributes=CredAttrSpec.list_plain(
            {"member": "James Bond", "favourite": "martini"}
        )
    )
    offer = CredentialOffer(
        comment="shaken, not stirred",
        credential_preview=preview,
        offers_attach=[
            AttachDecorator.data_base64(
                mapping=indy_offer,
                ident=ATTACH_DECO_IDS[CREDENTIAL_OFFER],
            )
        ],
    )

    def test_init(self):
        """Test initializer"""
        credential_offer = CredentialOffer(
            comment="shaken, not stirred",
            credential_preview=self.preview,
            offers_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_offer,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_OFFER],
                )
            ],
        )
        assert credential_offer.credential_preview == self.preview
        assert credential_offer.offers_attach[0].content == self.indy_offer
        assert credential_offer.indy_offer(0) == self.indy_offer

    def test_type(self):
        """Test type"""
        credential_offer = CredentialOffer(
            comment="shaken, not stirred",
            credential_preview=self.preview,
            offers_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_offer,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_OFFER],
                )
            ],
        )

        assert credential_offer._type == DIDCommPrefix.qualify_current(CREDENTIAL_OFFER)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOfferSchema.load"
    )
    def test_deserialize(self, mock_credential_offer_schema_load):
        """
        Test deserialize
        """
        obj = self.indy_offer

        credential_offer = CredentialOffer.deserialize(obj)
        mock_credential_offer_schema_load.assert_called_once_with(obj)

        assert credential_offer is mock_credential_offer_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOfferSchema.dump"
    )
    def test_serialize(self, mock_credential_offer_schema_dump):
        """
        Test serialization.
        """
        credential_offer = CredentialOffer(
            comment="shaken, not stirred",
            credential_preview=self.preview,
            offers_attach=[
                AttachDecorator.data_base64(
                    mapping=self.indy_offer,
                    ident=ATTACH_DECO_IDS[CREDENTIAL_OFFER],
                )
            ],
        )

        credential_offer_dict = credential_offer.serialize()
        mock_credential_offer_schema_dump.assert_called_once_with(credential_offer)

        assert credential_offer_dict is mock_credential_offer_schema_dump.return_value


class TestCredentialOfferSchema(TestCase):
    """Test credential cred offer schema"""

    credential_offer = CredentialOffer(
        comment="shaken, not stirred",
        credential_preview=TestCredentialOffer.preview,
        offers_attach=[AttachDecorator.data_base64(TestCredentialOffer.indy_offer)],
    )

    def test_make_model(self):
        """Test making model."""
        data = self.credential_offer.serialize()
        model_instance = CredentialOffer.deserialize(data)
        assert isinstance(model_instance, CredentialOffer)
