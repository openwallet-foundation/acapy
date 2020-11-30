import json
import pytest
import uuid

from copy import deepcopy
from datetime import datetime, timezone
from time import time
from unittest import TestCase

from ....messaging.models.base import BaseModelError
from ....wallet.indy import IndySdkWallet
from ....wallet.util import b64_to_bytes, bytes_to_b64

from ..attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
    AttachDecoratorData,
    AttachDecoratorDataSchema,
    AttachDecoratorData1JWS,
    AttachDecoratorData1JWSSchema,
    AttachDecoratorDataJWS,
    AttachDecoratorDataJWSSchema,
    AttachDecoratorDataJWSHeader,
    AttachDecoratorDataJWSHeaderSchema,
    did_key,
    raw_key,
)


KID = "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"
INDY_CRED = {
    "schema_id": "LjgpST2rjsoxYegQDRm7EL:2:icon:1.0",
    "cred_def_id": "LjgpST2rjsoxYegQDRm7EL:3:CL:19:tag",
    "rev_reg_id": None,
    "values": {
        "icon": {
            "raw": "iVBORw0KGgoAAAANSUhEUgAAACQAAAAlCAIAAAClPtxqAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAASCSURBVFhHY/hPRzAULPvx7sm5vatXT61LBYLCzvmrtxy7/uoLVBInINWyL9c31weo8rMzYAHs/KoB9Zuv47aTBMt+3FqTocsNNZib18NOtyLOdUImENlWeKp5iMEcwK2bsebWD6gmFECsZS8OV5mATeOSUa3MCd82MX03BtrW7FNvI8gFUsWunrvrBVQrAhBl2Y+LnWCbWCx8vdb3oduBilLX5xlYsIHtK9r7DmoAFBBh2Y+9uaIgm9wighEe6otamOWyoDYJyRoE2lZl4QayTzR2A4r3CFr243iVMlAfl7ndGmQTq5wnhOn1ZwQjRFDRxkxNaaA2wdgNSL4jYNmPi636QD1sMg11aMalrK8NX9uLKtgRMjfDZWFDKpgb32PLAtRqPeUu1CwClr3YlasOiisDb/MZGU4zgSjLc2FF+LouiHHoaFuZfX+Y3uSCaAh3R4EeyHPK9WegxuG07Mv1ldB0ziEp0Rim14eCDCYm+6zGklJSNrfGb0WIB5bJAw0w6bsBNRSLZT8ebyuC5idWAyudznjnBWVBK5ri1tYGLS72nJlkOiEcaJ/1gja4oTjRZFeQKbEboCajW4acn+qLorZgTei9iRs6U9AFMVGHV487KNfBvYZiGSn5iSBKWJyi32EEsky/8wrEfCTL3m1NxsxPRKJG3+lxlrOr4NkuYUm6ETB2K7RACTJ8DbTwglsGy0+2ThvhRuBCvYkb0RJkhSNSOoTa1BemnSwLNFK26jjUDphl75YHAgOQTbG9CaI/an6SyZTc8J1w4xAoel68Xl+4xTxofoKg1K3tidtBDLhNen3Bsk5Au9hjN8BKZahlj2Y4AsWlvb13QDR3BUwP1+tP8t0ANQsZJS3JABsX47YCPV6RbArTqwdHmGDmLngNALHsx5pwoLhQWTlC586uRKQcg4r6oubFGwCNm5QbgSSOYlNfoKwTKL6QsjTMsout2kAJxfYWuE5CqNFzMtDEKJflUBFUm0LUYiWZgCaKJm9FLvghlm2IBcowaE8mIbmnri5xmVMWA45UdJuS5UFlPoNo7l7UOhTZMqWu5BAsKaIreFYcrsQCRLhsQqteQABi2d5cQaA8f02Y4YyyeHRDuwJnROhNyAjegiYOQjhtWvMYS8MAYhkkMbIE+gD1GE0rjAAnYkKoL2ZhCgk2AQHEsv9XOkHVlrKuGlgnsFD3XN6GvR4Bo9SN1Z7TokEJknibgABqGdQ2LsG8YJj+MINJSS7zqyKRylxgzo1eUeY5I94QWF6QahMQwCyDFiEMGroq3cgGEURE2wQEcMuAnusDF/lsXnba6CbiQqTYBARIlv3/f3euG6jSZGH3sdEi7L9g1URSbAICFMsQNRoDs56GbB0i/tCQbquThIMAqIwg3iYgQLMMCH7cWhwuDbaQgYXFUFEs0Um12U+rM0SvK1Cz2Vsl31TURogZLM3AbVV/GLPdixtgWgYCPx4f6AxQhLXrsQB2fuOMlXi6ENgBdssg4Me7y3uBnSI/C3kEsPAr7Fx17D6p1kAAPsuoDoarZf//AwC50IEBL0kXDwAAAABJRU5ErkJggg==",
            "encoded": "85929378851528373462476134086349191156716977518236347190837906992705833250356",
        },
        "ident": {
            "raw": "user123",
            "encoded": "104044126701819941567620027928245728115259050067486134943085783087059317769286",
        },
    },
    "signature": {
        "p_credential": {
            "m_2": "12793445067895681333541008404571656028744585880834393854282654815765098811607",
            "a": "30493624771714999750664947149063864872079726486304859824509159719759248766426548567539655789005288566000489820378097416694445381019755606098802624521713332571600287785890474406419058201142498228331300355404538550735219342791097107362126769781128125755404026599399730121648476429643149538796075297983214423300027588074098346224513724675704148358327736921325673600912295803649158768049845935118037495053339327327533820158671062805750278076695260570350391958980965153038578544580957728820106541165420828487047454961560740761654675166441774288281847970069949920492238486277883006304771381038193384773719457764945515908368",
            "e": "259344723055062059907025491480697571938277889515152306249728583105665800713306759149981690559193987143012367913206299323899696942213235956742930100751413905307180889170188706654741",
            "v": "6247149074830522384788781911791166096867562977126702235555529750862341622033207615327169506527018798536233961888739830461168596209733404946795826735416009289933106166561198715296924950280893556506591309585160693784229778411319917776517204038858075779447948330858837161319709931892301128667177202264913661309853029183642587801009603083957409145961948944958437245291001980779116127530157410314979802615155598243284808105566273192284732599123486654030966074849566391173338491795177870375162340169290935462125235201421524320732912778881314448632315503015076999555275869439763279727091979358499185388799511243995496976938508241028254626867651484285100409649210465719854836127032022955810102860503121199898835939401404866521131232768406693306463735020670759562986485035176817787673102574110285427945257661758072224541984814214",
        },
        "r_credential": None,
    },
    "signature_correctness_proof": {
        "se": "6383089159718843691877794688971071220275030905560874137911054099064431761021716671063690767696909894018000007068324574982548945575643565092654792066807059157974212977897429400573299144869092663312438701239293658152030628758710350771443402172420620477902317751878418567571879922412069114719475275409179789374322679251290260653588700903847832410719254794914112181998691802227715011822416019754999717264096433742321496782490043812383111660515513781181876524111123591221558091490318198825057135876793820697480807021940549243121302007076687442523144630103557703781605167977619019171151120253897738429294520066881760984151",
        "c": "71776975021845391646647388738454608801245704188788685888117225842593781468763",
    },
    "rev_reg": None,
    "witness": None,
}
IDENT = str(uuid.uuid4())
DESCRIPTION = 'To one trained by "Bob," Truth can be found in a potato'
FILENAME = "potato.png"
MIME_TYPE = "image/png"
LASTMOD_TIME = datetime.now().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
BYTE_COUNT = 123456
DATA_B64 = AttachDecoratorData(base64_=bytes_to_b64(b"sample image with padding"))
DATA_JSON = AttachDecoratorData(
    json_=json.dumps({"preference": "hasselback", "variety": "russet"})
)
DATA_LINKS = AttachDecoratorData(
    links_="https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png",
    sha256_="3eb10792d1f0c7e07e7248273540f1952d9a5a2996f4b5df70ab026cd9f05517",
)


@pytest.fixture()
def seed():
    return [f"TestWalletSignVerifyAttachDeco0{i}" for i in [0, 1]]


@pytest.fixture()
async def wallet():
    wallet = IndySdkWallet(
        {
            "auto_create": True,
            "auto_remove": True,
            "key": await IndySdkWallet.generate_wallet_key(),
            "key_derivation_method": "RAW",
            "name": "test-wallet-sign-verify-attach-deco",
        }
    )
    await wallet.open()
    yield wallet
    await wallet.close()


class TestAttachDecorator(TestCase):
    def test_jws_header(self):
        jws_header = AttachDecoratorDataJWSHeader(kid=KID)
        assert jws_header.kid == KID

        dumped = jws_header.serialize()
        loaded = AttachDecoratorDataJWSHeader.deserialize(dumped)
        assert loaded.kid == jws_header.kid

        bad_kid = {"kid": "a suffusion of yellow"}
        with pytest.raises(BaseModelError):
            AttachDecoratorDataJWSHeader.deserialize(bad_kid)

    def test_1jws(self):
        jws_header = AttachDecoratorDataJWSHeader(kid=KID)
        PROTECTED = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"
        SIGNATURE = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"

        one_jws = AttachDecoratorData1JWS(
            header=jws_header, protected=PROTECTED, signature=SIGNATURE
        )
        assert one_jws.header == jws_header
        assert one_jws.protected == PROTECTED
        assert one_jws.signature == SIGNATURE

        dumped = one_jws.serialize()
        loaded = AttachDecoratorData1JWS.deserialize(dumped)
        assert loaded.header == one_jws.header
        assert loaded.protected == one_jws.protected
        assert loaded.signature == one_jws.signature

        badness = [
            {
                "header": jws_header.serialize(),
                "protected": "a suffusion of yellow",
                "signature": SIGNATURE,
            },
            {"header": "incorrect", "protected": PROTECTED, "signature": SIGNATURE},
        ]
        for bad in badness:
            with pytest.raises(BaseModelError):
                AttachDecoratorData1JWS.deserialize(bad)

    def test_jws1(self):
        jws_header = AttachDecoratorDataJWSHeader(kid=KID)
        PROTECTED = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"
        SIGNATURE = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"
        jws1 = AttachDecoratorDataJWS(
            header=jws_header, protected=PROTECTED, signature=SIGNATURE
        )
        assert jws1.header == jws_header
        assert jws1.protected == PROTECTED
        assert jws1.signature == SIGNATURE

        dumped = jws1.serialize()
        loaded = AttachDecoratorDataJWS.deserialize(dumped)
        assert loaded.header == jws1.header
        assert loaded.protected == jws1.protected
        assert loaded.signature == jws1.signature

        badness = [
            {"header": jws_header.serialize()},
            {"header": "incorrect", "protected": PROTECTED, "signature": SIGNATURE},
            {"protected": PROTECTED, "signature": SIGNATURE},
        ]
        for bad in badness:
            with pytest.raises(BaseModelError):
                AttachDecoratorData1JWS.deserialize(bad)

    def test_jws2(self):
        jws_header = AttachDecoratorDataJWSHeader(kid=KID)
        PROTECTED = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"
        SIGNATURE = "YmFzZTY0dXJsOyBubyBwYWRkaW5n"
        one_jws = AttachDecoratorData1JWS(
            header=jws_header, protected=PROTECTED, signature=SIGNATURE
        )
        jws2 = AttachDecoratorDataJWS(signatures=[one_jws, one_jws])
        assert jws2.header is None
        assert jws2.protected is None
        assert jws2.signature is None
        assert len(jws2.signatures) == 2

        dumped = jws2.serialize()
        loaded = AttachDecoratorDataJWS.deserialize(dumped)
        assert loaded.header == jws2.header
        assert loaded.protected == jws2.protected
        assert loaded.signature == jws2.signature
        assert loaded.signatures == jws2.signatures

        badness = [
            {
                "header": jws_header.serialize(),
                "protected": PROTECTED,
                "signature": SIGNATURE,
                "signatures": [one_jws.serialize(), one_jws.serialize()],
            },
            {
                "signature": SIGNATURE,
                "signatures": [one_jws.serialize(), one_jws.serialize()],
            },
            {
                "protected": PROTECTED,
                "signature": SIGNATURE,
            },
        ]
        for bad in badness:
            with pytest.raises(BaseModelError) as excinfo:
                AttachDecoratorDataJWS.deserialize(bad)

    def test_embedded_b64(self):
        decorator = AttachDecorator(
            mime_type=MIME_TYPE,
            filename=FILENAME,
            lastmod_time=LASTMOD_TIME,
            description=DESCRIPTION,
            data=DATA_B64,
        )

        assert decorator.mime_type == MIME_TYPE
        assert decorator.filename == FILENAME
        assert decorator.lastmod_time == LASTMOD_TIME
        assert decorator.description == DESCRIPTION
        assert decorator.data == DATA_B64

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.mime_type == decorator.mime_type
        assert loaded.filename == decorator.filename
        assert loaded.lastmod_time == decorator.lastmod_time
        assert loaded.description == decorator.description
        assert loaded.data == decorator.data

    def test_init_appended_b64(self):
        decorator = AttachDecorator(
            ident=IDENT,
            mime_type=MIME_TYPE,
            filename=FILENAME,
            lastmod_time=LASTMOD_TIME,
            description=DESCRIPTION,
            data=DATA_B64,
        )

        assert decorator.ident == IDENT
        assert decorator.mime_type == MIME_TYPE
        assert decorator.filename == FILENAME
        assert decorator.lastmod_time == LASTMOD_TIME
        assert decorator.description == DESCRIPTION
        assert decorator.data == DATA_B64

    def test_serialize_load_appended_b64(self):
        decorator = AttachDecorator(
            ident=IDENT,
            mime_type=MIME_TYPE,
            filename=FILENAME,
            lastmod_time=LASTMOD_TIME,
            description=DESCRIPTION,
            data=DATA_B64,
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert decorator.ident == IDENT
        assert decorator.mime_type == MIME_TYPE
        assert decorator.filename == FILENAME
        assert decorator.lastmod_time == LASTMOD_TIME
        assert decorator.description == DESCRIPTION
        assert decorator.data == DATA_B64

    def test_init_appended_links(self):
        decorator = AttachDecorator(
            ident=IDENT,
            mime_type=MIME_TYPE,
            filename=FILENAME,
            byte_count=BYTE_COUNT,
            lastmod_time=LASTMOD_TIME,
            description=DESCRIPTION,
            data=DATA_LINKS,
        )

        assert decorator.ident == IDENT
        assert decorator.mime_type == MIME_TYPE
        assert decorator.filename == FILENAME
        assert decorator.byte_count == BYTE_COUNT
        assert decorator.lastmod_time == LASTMOD_TIME
        assert decorator.description == DESCRIPTION
        assert decorator.data == DATA_LINKS

    def test_serialize_load_appended_links(self):
        decorator = AttachDecorator(
            ident=IDENT,
            mime_type=MIME_TYPE,
            filename=FILENAME,
            byte_count=BYTE_COUNT,
            lastmod_time=LASTMOD_TIME,
            description=DESCRIPTION,
            data=DATA_LINKS,
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert decorator.ident == IDENT
        assert decorator.mime_type == MIME_TYPE
        assert decorator.filename == FILENAME
        assert decorator.byte_count == BYTE_COUNT
        assert decorator.lastmod_time == LASTMOD_TIME
        assert decorator.description == DESCRIPTION
        assert decorator.data == DATA_LINKS

    def test_indy_dict(self):
        deco_indy = AttachDecorator.from_indy_dict(
            indy_dict=INDY_CRED,
            ident=IDENT,
            description=DESCRIPTION,
        )
        assert deco_indy.mime_type == "application/json"
        assert hasattr(deco_indy.data, "base64_")
        assert deco_indy.data.base64 is not None
        assert deco_indy.data.json is None
        assert deco_indy.data.links is None
        assert deco_indy.data.sha256 is None
        assert deco_indy.indy_dict == INDY_CRED
        assert deco_indy.ident == IDENT
        assert deco_indy.description == DESCRIPTION

        deco_indy_auto_id = AttachDecorator.from_indy_dict(indy_dict=INDY_CRED)
        assert deco_indy_auto_id.ident

        # cover AttachDecoratorData equality operator
        plain_json = AttachDecoratorData(json_=json.dumps({"sample": "data"}))
        assert deco_indy.data != plain_json

        lynx_str = AttachDecoratorData(links_="https://en.wikipedia.org/wiki/Lynx")
        lynx_list = AttachDecoratorData(links_=["https://en.wikipedia.org/wiki/Lynx"])
        links = AttachDecoratorData(links_="https://en.wikipedia.org/wiki/Chain")

        assert lynx_str == lynx_list
        assert lynx_str != links
        assert links != DATA_LINKS  # has sha256

    def test_from_aries_msg(self):
        deco_aries = AttachDecorator.from_aries_msg(
            message=INDY_CRED,
            ident=IDENT,
            description=DESCRIPTION,
        )
        assert deco_aries.mime_type == "application/json"
        assert hasattr(deco_aries.data, "json_")
        assert deco_aries.data.base64 is None
        assert deco_aries.data.json is not None
        assert deco_aries.data.links is None
        assert deco_aries.data.sha256 is None
        assert deco_aries.data.json == INDY_CRED
        assert deco_aries.ident == IDENT
        assert deco_aries.description == DESCRIPTION

        deco_aries_auto_id = AttachDecorator.from_aries_msg(message=INDY_CRED)
        assert deco_aries_auto_id.ident


@pytest.mark.indy
class TestAttachDecoratorSignature:
    @pytest.mark.asyncio
    async def test_did_raw_key(self, wallet, seed):
        did_info = await wallet.create_local_did(seed[0])
        did_key0 = did_key(did_info.verkey)
        raw_key0 = raw_key(did_key0)
        assert raw_key0 != did_key0
        assert did_key0.startswith("did:key:z")
        assert raw_key0 == did_info.verkey

        assert did_key(did_key0) == did_key0
        assert raw_key(raw_key0) == raw_key0

    @pytest.mark.asyncio
    async def test_indy_sign(self, wallet, seed):
        deco_indy = AttachDecorator.from_indy_dict(
            indy_dict=INDY_CRED,
            ident=IDENT,
            description=DESCRIPTION,
            filename=FILENAME,
            lastmod_time=LASTMOD_TIME,
            byte_count=BYTE_COUNT,
        )
        deco_indy_master = deepcopy(deco_indy)
        did_info = [await wallet.create_local_did(seed[i]) for i in [0, 1]]
        assert deco_indy.data.signatures == 0
        assert deco_indy.data.header_map() is None
        await deco_indy.data.sign(did_info[0].verkey, wallet)
        assert deco_indy.data.jws is not None
        assert deco_indy.data.signatures == 1
        assert deco_indy.data.jws.signature
        assert not deco_indy.data.jws.signatures
        assert deco_indy.data.header_map(0) is not None
        assert deco_indy.data.header_map() is not None
        assert "kid" in deco_indy.data.header_map()
        assert "jwk" in deco_indy.data.header_map()
        assert "kid" in deco_indy.data.header_map()["jwk"]
        assert deco_indy.data.header_map()["kid"] == did_key(did_info[0].verkey)
        assert deco_indy.data.header_map()["jwk"]["kid"] == did_key(did_info[0].verkey)
        assert await deco_indy.data.verify(wallet)

        indy_cred = json.loads(deco_indy.data.signed.decode())
        assert indy_cred == INDY_CRED

        # Test tamper evidence
        jws_parts = deco_indy.data.jws.signature.split(".")
        tampered = bytearray(b64_to_bytes(deco_indy.data.jws.signature, urlsafe=True))
        tampered[0] = (tampered[0] + 1) % 256
        deco_indy.data.jws.signature = bytes_to_b64(
            bytes(tampered), urlsafe=True, pad=False
        )
        assert not await deco_indy.data.verify(wallet)

        # Degenerate case: sign with list of 1 verkey (expect flattened JSON)
        deco_indy = deepcopy(deco_indy_master)
        assert deco_indy.data.signed is None
        assert deco_indy.data.signatures == 0
        assert deco_indy.data.header_map() is None
        await deco_indy.data.sign([did_info[0].verkey], wallet)
        assert deco_indy.data.jws is not None
        assert deco_indy.data.signatures == 1
        assert deco_indy.data.jws.signature
        assert not deco_indy.data.jws.signatures
        assert deco_indy.data.header_map(0) is not None
        assert deco_indy.data.header_map() is not None
        assert "kid" in deco_indy.data.header_map()
        assert "jwk" in deco_indy.data.header_map()
        assert "kid" in deco_indy.data.header_map()["jwk"]
        assert deco_indy.data.header_map()["kid"] == did_key(did_info[0].verkey)
        assert deco_indy.data.header_map()["jwk"]["kid"] == did_key(did_info[0].verkey)
        assert await deco_indy.data.verify(wallet)

        indy_cred = json.loads(deco_indy.data.signed.decode())
        assert indy_cred == INDY_CRED

        # Multi-signature
        deco_indy = deepcopy(deco_indy_master)
        assert deco_indy.data.signed is None
        assert deco_indy.data.signatures == 0
        assert deco_indy.data.header_map() is None
        await deco_indy.data.sign(
            [did_info[i].verkey for i in range(len(did_info))], wallet
        )
        assert deco_indy.data.jws is not None
        assert deco_indy.data.signatures == 2
        assert not deco_indy.data.jws.signature
        assert deco_indy.data.jws.signatures
        for i in range(len(did_info)):
            assert deco_indy.data.header_map(i) is not None
            assert "kid" in deco_indy.data.header_map(i, jose=False)
            assert "kid" in deco_indy.data.header_map(i, jose=True)
            assert "jwk" in deco_indy.data.header_map(i)
            assert "kid" in deco_indy.data.header_map(i)["jwk"]
            assert deco_indy.data.header_map(i)["kid"] == did_key(did_info[i].verkey)
            assert deco_indy.data.header_map(i)["jwk"]["kid"] == did_key(
                did_info[i].verkey
            )
        assert deco_indy.data.signed is not None
        assert await deco_indy.data.verify(wallet)

        indy_cred = json.loads(deco_indy.data.signed.decode())
        assert indy_cred == INDY_CRED

        # De/serialize to exercise initializer with JWS
        deco_dict = deco_indy.serialize()
        deco = AttachDecorator.deserialize(deco_dict)
        deco_dict["data"]["links"] = "https://en.wikipedia.org/wiki/Potato"
        with pytest.raises(BaseModelError):
            AttachDecorator.deserialize(deco_dict)  # now has base64 and links
