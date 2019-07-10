import json
from unittest import mock

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.holder.indy import IndyHolder
from aries_cloudagent.storage.error import StorageError
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.wallet.indy import IndyWallet

from ...messaging.issue_credential.v1_0.messages.inner.credential_preview import (
    AttributePreview,
    CredentialPreview
)

class TestIndyHolder(AsyncTestCase):
    def test_init(self):
        holder = IndyHolder("wallet")
        assert holder.wallet == "wallet"

    @async_mock.patch("indy.anoncreds.prover_create_credential_req")
    async def test_create_credential_request(self, mock_create_credential_req):
        mock_create_credential_req.return_value = ("{}", "{}")
        mock_wallet = async_mock.MagicMock()

        holder = IndyHolder(mock_wallet)
        cred_req = await holder.create_credential_request(
            "credential_offer", "credential_definition", "did"
        )

        mock_create_credential_req.assert_called_once_with(
            mock_wallet.handle,
            "did",
            json.dumps("credential_offer"),
            json.dumps("credential_definition"),
            mock_wallet.master_secret_id,
        )

        assert cred_req == ({}, {})

    @async_mock.patch("indy.anoncreds.prover_store_credential")
    async def test_store_credential(self, mock_store_cred):
        mock_store_cred.return_value = "cred_id"
        mock_wallet = async_mock.MagicMock()

        holder = IndyHolder(mock_wallet)

        cred_id = await holder.store_credential(
            "credential_definition", "credential_data", "credential_request_metadata"
        )

        mock_store_cred.assert_called_once_with(
            mock_wallet.handle,
            None,
            json.dumps("credential_request_metadata"),
            json.dumps("credential_data"),
            json.dumps("credential_definition"),
            None,
        )

        assert cred_id == "cred_id"

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        mock_search_credentials.return_value = ("search_handle", "record_count")
        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials(0, 0, {})

        mock_search_credentials.assert_called_once_with(
            mock_wallet.handle, json.dumps({})
        )

        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_fetch_credentials.assert_called_once_with("search_handle", 0)
        mock_close_cred_search.assert_called_once_with("search_handle")

        assert credentials == json.loads("[1,2,3]")

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials_seek(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        mock_search_credentials.return_value = ("search_handle", "record_count")
        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials(2, 3, {})

        assert mock_fetch_credentials.call_args_list == [
            (("search_handle", 2),),
            (("search_handle", 3),),
        ]

    @async_mock.patch("indy.anoncreds.prover_search_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search_for_proof_req")
    async def test_get_credentials_for_presentation_request_by_referent(
        self,
        mock_prover_close_credentials_search_for_proof_req,
        mock_prover_fetch_credentials_for_proof_req,
        mock_prover_search_credentials_for_proof_req,
    ):
        mock_prover_search_credentials_for_proof_req.return_value = "search_handle"
        mock_prover_fetch_credentials_for_proof_req.return_value = '{"x": "y"}'

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            {"p": "r"}, "asdb", 2, 3, {"e": "q"}
        )

        mock_prover_search_credentials_for_proof_req.assert_called_once_with(
            mock_wallet.handle, json.dumps({"p": "r"}), json.dumps({"e": "q"})
        )

        assert mock_prover_fetch_credentials_for_proof_req.call_args_list == [
            (("search_handle", "asdb", 2),),
            (("search_handle", "asdb", 3),),
        ]

        mock_prover_close_credentials_search_for_proof_req.assert_called_once_with(
            "search_handle"
        )

        assert credentials == json.loads('{"x": "y"}')

    @async_mock.patch("indy.anoncreds.prover_get_credential")
    async def test_get_credential(self, mock_get_cred):
        mock_get_cred.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credential = await holder.get_credential("credential_id")

        mock_get_cred.assert_called_once_with(mock_wallet.handle, "credential_id")

        assert credential == json.loads("{}")

    @async_mock.patch("indy.anoncreds.prover_delete_credential")
    async def test_get_credential(self, mock_del_cred):
        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credential = await holder.delete_credential("credential_id")

        mock_del_cred.assert_called_once_with(mock_wallet.handle, "credential_id")

    try:
        import pytest
        from indy.libindy import _cdll
        _cdll()
    except ImportError:
        pytest.skip(
            "skipping Indy-specific tests: python module not installed",
            allow_module_level=True,
        )
    except OSError:
        pytest.skip(
            "skipping Indy-specific tests: shared library not loaded",
            allow_module_level=True,
        )
    async def test_metadata(self):
        cred_def_id = "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"

        indy_cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "12",
            "type": "CL",
            "tag": "tag",
            "value": {
                "primary": {
                    "n": "96095839200538879972844944289561855564182557530546183562621225694567807710704044134724653493348884456939079674288553367727413055272801551538574902897752864116216315921216486939472498359712293176576636599185413393866897891687980045979432674044063005750088248165399411874595072107172759056778084660962100712085135985932211848019163716141287876520356340776611414946996765304615806981481071341315457297109275322095843143931654733203945642219468713529471651809223075018314368125993197444550920206819706577018452179274632808939363825481000151643215338489671868837647632535108380048880683434721126642559397240183444829247549",
                    "s": "50672811666118644039874456151645281913747581817097103080049409772039902823676143088437626508167825358633298198639111709343098490217342836765268521601031175419926878244538040576285127845710681125939325603083679721542304628997813446333206091026593647184333099055553444282513576273749800512098953522401112315384666579446380395610469030587744300018885538712627254195519361453073335979311767950630436759445320300436238648336288985667163702277372102662179316469329924335146201099448548323177233785266293182372318479454554611600864826511342200610870824870134519666636851962430825674916508524848662323502940577194540818176366",
                    "r": {
                        "master_secret": "20841662401250363372618671627131027481299871240963536008687629269668824334116191046736567801366382445841953404299433797904519078245004242703089014825111347915825947561238975724078591915298586325446308628124634343103332089084975989370691032434273543795068038833679462552947733602830816869437034251886944301722666466985551431092555320817930879709081669312706859011433732796295549153649400066259759315678550934941675941903404223965315663335436538894257013036647087170579834801860575581364456071536069525106201564130079154684766604781681925098353473791098797970183924921991762910552543654013288697981726405401218843483579",
                        "ident": "55343401360338181373155453364756535494128577317441275586731993262673483765368055239733916784264917181673189099191767865262510146309010995797707511272049509453563835425568275189376408059239444551537106418612510697902394132825853496825789422550294050496221010303388152418412350299076153459187036332487490259453794661894325649422007602245928623671618993976052076065402295046080680584573396460917292278424394366974593614573669115687560973420441606252515829718317619626036797900619074654431768694217817681535216074575092797400084627340110305507392994722929341280479438289812705285491633746427162103382714596374776506665018",
                        "icon": "30332515374696238018620213243126417965647199581966134706369640814272674260878240366929573622818762017770663213465524708203696020927666543510479596628637210049867134352821836504673369138816270996718070184911042332398877228916570740439445427538070895000231213952197072163866548842470010931774204670616912106068703085190140108258439537459039349395292222795098262110346000406360747376801024543499588549399899296446030408911447356917635623123646634895538183034828991791791557862112595335643855259004458536929600557959729341452814783194547439801483360315351507418215502268784694151080200695240206735027007419840246739671083"
                    },
                    "rctxt": "74959436321483254664132841263659455118488983657619109522379567332866514833488034707744286975716638848360902975038002065554341310565672188032709520624820934369406863520757141952154745058648106352346933538055886623287093258325488208187125404486470517719620396697227322777815736334859430239788335184526227727491746985872992397467696173844365657808238520423155019346028554035137806642350991626546122810968807307471898026123516884924793713760476644095277335388157372146194897377373139263332481437319309938306813169336420961658885074751113378059683746088270928903031898354104418830450782493268913299867162122194255933284144",
                    "z": "13540423120606819658331611771086791196141435754696171943955735507652160399651093745109093939216907894582202600253274524547660050733717779207589053937413674665713411940790156528227150750386304241183011497139258419487386088069631424739995145878214071724137187569594733187540754027679920766811237587175050736681755052378770920964790453383726291677065585180287056641022184256043947256825788960272162393871746392199277063337143648776756081375889645579683871624016701518063129183992410782555359067103983838741274459484632343295576907054246373707029253896345427278200434115150665267568353897524676436043140820096639354266871"
                },
                "revocation": {
                    "g": "1 1F14F7ECB578F742572DAE9DE045C101D8D780720B61D77CB7C1204EF68F945C 1 09A43346660328D67CC502DF60A671D635F367209349CEDD6E1E4DA0848B8408 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "g_dash": "1 1D647164CDC00C55AF2A1D1171B7FF7D9FC0524C015B3B73E5D5CF781E5B7FB7 1 0C781960FA66E3D3FE004FC573A1CF6FBAAE653DAECF72958D82CCF5A558EBE5 1 0F9717C5A7F3A9A54EE34D7DAF288EFDBA7734A95B999169EAF2F4CE80372E10 1 22263BEA51077ABD54B63A516B9B3E30CD4C1BF2AF1D0C3BDE00FF895731F9AB 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "h": "1 16675DAE54BFAE8C3FBA7907892498CB1FDD44C443D52D1B0E9DE5E4B8FDA0A6 1 1CE1A85646BE8D3B7A339CCEAE3478057D2C8309FB90A68E5401326B06E84648 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h0": "1 21E5EF9476EAF1F7F06E8D23521ED948AE28A10EDA1183B7870EAF7E7619B192 1 133922BB0D9BED59144F8530C32B2ED90B80EBBA347828B6D084213FC14FAB3B 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h1": "1 236D1D99236090E2770243C2A66B86EBDD45A1CA6E63EB8E540236BBA00A4B21 1 1D0CDD6B08F1022815BF30377A5577F8FA0A1E4EF59CF853408C5E39A9A60B9A 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h2": "1 1C3AE8D1F1E2694D693029360B129835A10E2D4A2FA2393BED6C39A3418BC663 1 0DF1173D49E73DE035A92C62ECD443E7D7FC46EEACF6B8797412E998E5727FF5 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "htilde": "1 1D8549E8C0F8B4B2DD86C8AAD759C95AC8775DBB1718C3BDBD6DAE112C47EA01 1 1ED49BB219FD9FFFA3FCBB22719BE35150CC9AEDA11AC4F6F5B15038C293900D 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h_cap": "1 1B2A32CF31673608C68AA299E7C9F1E06687B7BF8A4350CC1FF12D7B7D2F3EC2 1 2490FEBF6EE553CF5131C0C5B124AEC95FFF53FAA7E373A90E1B45DAEBC01FA8 1 205A57E00813CA43C7BC28758AB9BF3D5A1AC9FF84D6FA46B7A8D5DA08C19F19 1 1775AF29AF2D4009A03D8A899F20B93C5752CAC6B28E8FEFFC7F1F56C9D326B8 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "u": "1 0C43011B2B4710C6E0794CBCF663B00A959E82D6B36A1D36650F918C95BCA385 1 0EA9529E5353D322C960841E81BB9363D8E40033F1DBCDA5F8DF5EDBBF0FE4F8 1 1CB3A0932EE7E3C1CC06820511D4DEF06F7C3E143F04FEB97EEE415ACE76E0CF 1 0FA670BC512BBD9D06E7B92D757AE6C7C36CDAF9E573876519A495D6D65D4344 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "pk": "1 142CD5E5A7DC49E2E3BBA5A348141AAC055121482BA3F63AEBDB555094F1809F 1 1AD3E0C192BB060D6DD874D2217490FA5307832F70C6A17CAEB39673FB7B45A3 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "y": "1 153885BD90331274628399107A9EE4177A61ED6DB86CEB1A3854A8E0C74E1BEA 1 0D7791FE3B379B7898C2B0D89B1A384547CBA9F81E7BF3DFE07335D868F9BFD4 1 0B9DF98FBC923375920FB84B8D92581BFCA8EBFAF9B85214571218089F9412D0 1 00150AF596651BDFEC152078C363D712B8F4E9555D26DA5DB3BF7D759BC3A027 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000"
                }
            }
        }
        cred_preview = CredentialPreview(
            attributes=(
                AttributePreview.list_plain({'ident': 'user123'}) +
                [
                    AttributePreview(
                        name='icon',
                        encoding='base64',
                        mime_type='image/png',
                        value='iVBORw0KGgoAAAANSUhEUgAAACQAAAAlCAIAAAClPtxqAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAASCSURBVFhHY/hPRzAULPvx7sm5vatXT61LBYLCzvmrtxy7/uoLVBInINWyL9c31weo8rMzYAHs/KoB9Zuv47aTBMt+3FqTocsNNZib18NOtyLOdUImENlWeKp5iMEcwK2bsebWD6gmFECsZS8OV5mATeOSUa3MCd82MX03BtrW7FNvI8gFUsWunrvrBVQrAhBl2Y+LnWCbWCx8vdb3oduBilLX5xlYsIHtK9r7DmoAFBBh2Y+9uaIgm9wighEe6otamOWyoDYJyRoE2lZl4QayTzR2A4r3CFr243iVMlAfl7ndGmQTq5wnhOn1ZwQjRFDRxkxNaaA2wdgNSL4jYNmPi636QD1sMg11aMalrK8NX9uLKtgRMjfDZWFDKpgb32PLAtRqPeUu1CwClr3YlasOiisDb/MZGU4zgSjLc2FF+LouiHHoaFuZfX+Y3uSCaAh3R4EeyHPK9WegxuG07Mv1ldB0ziEp0Rim14eCDCYm+6zGklJSNrfGb0WIB5bJAw0w6bsBNRSLZT8ebyuC5idWAyudznjnBWVBK5ri1tYGLS72nJlkOiEcaJ/1gja4oTjRZFeQKbEboCajW4acn+qLorZgTei9iRs6U9AFMVGHV487KNfBvYZiGSn5iSBKWJyi32EEsky/8wrEfCTL3m1NxsxPRKJG3+lxlrOr4NkuYUm6ETB2K7RACTJ8DbTwglsGy0+2ThvhRuBCvYkb0RJkhSNSOoTa1BemnSwLNFK26jjUDphl75YHAgOQTbG9CaI/an6SyZTc8J1w4xAoel68Xl+4xTxofoKg1K3tidtBDLhNen3Bsk5Au9hjN8BKZahlj2Y4AsWlvb13QDR3BUwP1+tP8t0ANQsZJS3JABsX47YCPV6RbArTqwdHmGDmLngNALHsx5pwoLhQWTlC586uRKQcg4r6oubFGwCNm5QbgSSOYlNfoKwTKL6QsjTMsout2kAJxfYWuE5CqNFzMtDEKJflUBFUm0LUYiWZgCaKJm9FLvghlm2IBcowaE8mIbmnri5xmVMWA45UdJuS5UFlPoNo7l7UOhTZMqWu5BAsKaIreFYcrsQCRLhsQqteQABi2d5cQaA8f02Y4YyyeHRDuwJnROhNyAjegiYOQjhtWvMYS8MAYhkkMbIE+gD1GE0rjAAnYkKoL2ZhCgk2AQHEsv9XOkHVlrKuGlgnsFD3XN6GvR4Bo9SN1Z7TokEJknibgABqGdQ2LsG8YJj+MINJSS7zqyKRylxgzo1eUeY5I94QWF6QahMQwCyDFiEMGroq3cgGEURE2wQEcMuAnusDF/lsXnba6CbiQqTYBARIlv3/f3euG6jSZGH3sdEi7L9g1URSbAICFMsQNRoDs56GbB0i/tCQbquThIMAqIwg3iYgQLMMCH7cWhwuDbaQgYXFUFEs0Um12U+rM0SvK1Cz2Vsl31TURogZLM3AbVV/GLPdixtgWgYCPx4f6AxQhLXrsQB2fuOMlXi6ENgBdssg4Me7y3uBnSI/C3kEsPAr7Fx17D6p1kAAPsuoDoarZf//AwC50IEBL0kXDwAAAABJRU5ErkJggg=='
                    )
                ]
            )
        )
        assert indy_cred_def["id"] == cred_def_id

        wallet = IndyWallet({
            "auto_create": False,
            "auto_remove": False,
            "name": "indy_meta",
        })
        await wallet.create()
        await wallet.open()

        holder = IndyHolder(wallet)

        await holder.store_metadata(indy_cred_def, cred_preview.metadata())
        try:
            await holder.get_metadata(cred_def_id, "no-such-attr")
            assert False
        except StorageError as x_stor:
            assert "has no tag" in str(x_stor)

        assert await holder.get_metadata(cred_def_id, "ident") == {
            "mime-type": "text/plain"
        }

        assert await holder.get_metadata(cred_def_id, "icon") == {
            "mime-type": "image/png",
            "encoding": "base64"
        }

        assert await holder.get_metadata(cred_def_id) == {
            "ident": {
                "mime-type": "text/plain"
            },
            "icon": {
                "mime-type": "image/png",
                "encoding": "base64"
            }
        }

        await wallet.close()
        await wallet.remove()

    @async_mock.patch("indy.anoncreds.prover_create_proof")
    async def test_create_presentation(self, mock_create_proof):
        mock_create_proof.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        presentation = await holder.create_presentation(
            "presentation_request",
            "requested_credentials",
            "schemas",
            "credential_definitions",
        )

        mock_create_proof.assert_called_once_with(
            mock_wallet.handle,
            json.dumps("presentation_request"),
            json.dumps("requested_credentials"),
            mock_wallet.master_secret_id,
            json.dumps("schemas"),
            json.dumps("credential_definitions"),
            json.dumps({}),
        )

        assert presentation == json.loads("{}")
