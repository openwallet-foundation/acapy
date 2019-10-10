from datetime import datetime, timezone
from unittest import TestCase

import base64
import json
import uuid

from ..attach_decorator import AttachDecorator, AttachDecoratorData


class TestAttachDecorator(TestCase):
    ident = str(uuid.uuid4())
    description = 'To one trained by "Bob," Truth can be found in a potato'
    filename = 'potato.png'
    mime_type = 'image/png'
    lastmod_time = datetime.now().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
    byte_count = 123456
    data_b64 = AttachDecoratorData(
        base64_=base64.b64encode('sample image with padding'.encode()).decode()
    )
    data_json = AttachDecoratorData(
        json_=json.dumps({'preference': 'hasselback', 'variety': 'russet'})
    )
    data_links = AttachDecoratorData(
        links_='https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png',
        sha256_='3eb10792d1f0c7e07e7248273540f1952d9a5a2996f4b5df70ab026cd9f05517'
    )
    indy_cred = {
        "schema_id": "LjgpST2rjsoxYegQDRm7EL:2:icon:1.0",
        "cred_def_id": "LjgpST2rjsoxYegQDRm7EL:3:CL:19:tag",
        "rev_reg_id": None,
        "values": {
            "icon": {
                "raw": "iVBORw0KGgoAAAANSUhEUgAAACQAAAAlCAIAAAClPtxqAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAASCSURBVFhHY/hPRzAULPvx7sm5vatXT61LBYLCzvmrtxy7/uoLVBInINWyL9c31weo8rMzYAHs/KoB9Zuv47aTBMt+3FqTocsNNZib18NOtyLOdUImENlWeKp5iMEcwK2bsebWD6gmFECsZS8OV5mATeOSUa3MCd82MX03BtrW7FNvI8gFUsWunrvrBVQrAhBl2Y+LnWCbWCx8vdb3oduBilLX5xlYsIHtK9r7DmoAFBBh2Y+9uaIgm9wighEe6otamOWyoDYJyRoE2lZl4QayTzR2A4r3CFr243iVMlAfl7ndGmQTq5wnhOn1ZwQjRFDRxkxNaaA2wdgNSL4jYNmPi636QD1sMg11aMalrK8NX9uLKtgRMjfDZWFDKpgb32PLAtRqPeUu1CwClr3YlasOiisDb/MZGU4zgSjLc2FF+LouiHHoaFuZfX+Y3uSCaAh3R4EeyHPK9WegxuG07Mv1ldB0ziEp0Rim14eCDCYm+6zGklJSNrfGb0WIB5bJAw0w6bsBNRSLZT8ebyuC5idWAyudznjnBWVBK5ri1tYGLS72nJlkOiEcaJ/1gja4oTjRZFeQKbEboCajW4acn+qLorZgTei9iRs6U9AFMVGHV487KNfBvYZiGSn5iSBKWJyi32EEsky/8wrEfCTL3m1NxsxPRKJG3+lxlrOr4NkuYUm6ETB2K7RACTJ8DbTwglsGy0+2ThvhRuBCvYkb0RJkhSNSOoTa1BemnSwLNFK26jjUDphl75YHAgOQTbG9CaI/an6SyZTc8J1w4xAoel68Xl+4xTxofoKg1K3tidtBDLhNen3Bsk5Au9hjN8BKZahlj2Y4AsWlvb13QDR3BUwP1+tP8t0ANQsZJS3JABsX47YCPV6RbArTqwdHmGDmLngNALHsx5pwoLhQWTlC586uRKQcg4r6oubFGwCNm5QbgSSOYlNfoKwTKL6QsjTMsout2kAJxfYWuE5CqNFzMtDEKJflUBFUm0LUYiWZgCaKJm9FLvghlm2IBcowaE8mIbmnri5xmVMWA45UdJuS5UFlPoNo7l7UOhTZMqWu5BAsKaIreFYcrsQCRLhsQqteQABi2d5cQaA8f02Y4YyyeHRDuwJnROhNyAjegiYOQjhtWvMYS8MAYhkkMbIE+gD1GE0rjAAnYkKoL2ZhCgk2AQHEsv9XOkHVlrKuGlgnsFD3XN6GvR4Bo9SN1Z7TokEJknibgABqGdQ2LsG8YJj+MINJSS7zqyKRylxgzo1eUeY5I94QWF6QahMQwCyDFiEMGroq3cgGEURE2wQEcMuAnusDF/lsXnba6CbiQqTYBARIlv3/f3euG6jSZGH3sdEi7L9g1URSbAICFMsQNRoDs56GbB0i/tCQbquThIMAqIwg3iYgQLMMCH7cWhwuDbaQgYXFUFEs0Um12U+rM0SvK1Cz2Vsl31TURogZLM3AbVV/GLPdixtgWgYCPx4f6AxQhLXrsQB2fuOMlXi6ENgBdssg4Me7y3uBnSI/C3kEsPAr7Fx17D6p1kAAPsuoDoarZf//AwC50IEBL0kXDwAAAABJRU5ErkJggg==",
                "encoded": "85929378851528373462476134086349191156716977518236347190837906992705833250356"
            },
            "ident": {
                "raw": "user123",
                "encoded": "104044126701819941567620027928245728115259050067486134943085783087059317769286"
            }
        },
        "signature": {
            "p_credential": {
                "m_2": "12793445067895681333541008404571656028744585880834393854282654815765098811607",
                "a": "30493624771714999750664947149063864872079726486304859824509159719759248766426548567539655789005288566000489820378097416694445381019755606098802624521713332571600287785890474406419058201142498228331300355404538550735219342791097107362126769781128125755404026599399730121648476429643149538796075297983214423300027588074098346224513724675704148358327736921325673600912295803649158768049845935118037495053339327327533820158671062805750278076695260570350391958980965153038578544580957728820106541165420828487047454961560740761654675166441774288281847970069949920492238486277883006304771381038193384773719457764945515908368",
                "e": "259344723055062059907025491480697571938277889515152306249728583105665800713306759149981690559193987143012367913206299323899696942213235956742930100751413905307180889170188706654741",
                "v": "6247149074830522384788781911791166096867562977126702235555529750862341622033207615327169506527018798536233961888739830461168596209733404946795826735416009289933106166561198715296924950280893556506591309585160693784229778411319917776517204038858075779447948330858837161319709931892301128667177202264913661309853029183642587801009603083957409145961948944958437245291001980779116127530157410314979802615155598243284808105566273192284732599123486654030966074849566391173338491795177870375162340169290935462125235201421524320732912778881314448632315503015076999555275869439763279727091979358499185388799511243995496976938508241028254626867651484285100409649210465719854836127032022955810102860503121199898835939401404866521131232768406693306463735020670759562986485035176817787673102574110285427945257661758072224541984814214"
            },
            "r_credential": None
        },
        "signature_correctness_proof": {
            "se": "6383089159718843691877794688971071220275030905560874137911054099064431761021716671063690767696909894018000007068324574982548945575643565092654792066807059157974212977897429400573299144869092663312438701239293658152030628758710350771443402172420620477902317751878418567571879922412069114719475275409179789374322679251290260653588700903847832410719254794914112181998691802227715011822416019754999717264096433742321496782490043812383111660515513781181876524111123591221558091490318198825057135876793820697480807021940549243121302007076687442523144630103557703781605167977619019171151120253897738429294520066881760984151",
            "c": "71776975021845391646647388738454608801245704188788685888117225842593781468763"
        },
        "rev_reg": None,
        "witness": None
    }

    def test_init_embedded_b64(self):
        decorator = AttachDecorator(
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_b64

    def test_serialize_load_embedded_b64(self):
        decorator = AttachDecorator(
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_b64

    def test_init_appended_b64(self):
        decorator = AttachDecorator(
            ident=self.ident,
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )

        assert decorator.ident == self.ident
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_b64

    def test_serialize_load_appended_b64(self):
        decorator = AttachDecorator(
            ident=self.ident,
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.ident == self.ident
        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_b64

    def test_init_appended_links(self):
        decorator = AttachDecorator(
            ident=self.ident,
            mime_type=self.mime_type,
            filename=self.filename,
            byte_count=self.byte_count,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_links
        )
        assert decorator.ident == self.ident
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.byte_count == self.byte_count
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_links

    def test_serialize_load_appended_links(self):
        decorator = AttachDecorator(
            ident=self.ident,
            mime_type=self.mime_type,
            filename=self.filename,
            byte_count=self.byte_count,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_links
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.ident == self.ident
        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.byte_count == self.byte_count
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_links

    def test_indy_dict(self):
        deco_indy = AttachDecorator.from_indy_dict(
            indy_dict=self.indy_cred,
            ident=self.ident,
            description=self.description,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            byte_count=self.byte_count
        )
        assert deco_indy.mime_type == 'application/json'
        assert hasattr(deco_indy.data, 'base64_')
        assert deco_indy.indy_dict == self.indy_cred
        assert deco_indy.ident == self.ident
        assert deco_indy.description == self.description
        assert deco_indy.filename == self.filename
        assert deco_indy.lastmod_time == self.lastmod_time
        assert deco_indy.byte_count == self.byte_count

        deco_indy_auto_id = AttachDecorator.from_indy_dict(indy_dict=self.indy_cred)
        assert deco_indy_auto_id.ident
