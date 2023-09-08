import importlib
import json

from os.path import join
from typing import Any, Mapping, Type

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....core.in_memory import InMemoryProfile, InMemoryProfileSession
from ....core.profile import Profile, ProfileSession
from ....config.injection_context import InjectionContext
from ....indy.issuer import IndyIssuer, IndyIssuerError
from ....indy.models.revocation import IndyRevRegDef
from ....indy.util import indy_client_dir
from ....ledger.base import BaseLedger
from ....tails.base import BaseTailsServer

from ...error import RevocationError

from .. import issuer_rev_reg_record as test_module
from ..issuer_rev_reg_record import IssuerRevRegRecord
from ..revocation_registry import RevocationRegistry

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"
TAILS_HASH = "3MLjUFQz9x9n5u9rFu8Ba9C5bo4HNFjkPNc54jZPSNaZ"
TAILS_URI = "http://tails.ca/3MLj"

REV_REG_DEF = {
    "ver": "1.0",
    "id": REV_REG_ID,
    "revocDefType": "CL_ACCUM",
    "tag": "default",
    "credDefId": CRED_DEF_ID,
    "value": {
        "issuanceType": "ISSUANCE_ON_DEMAND",
        "maxCredNum": 5,
        "publicKeys": {
            "accumKey": {
                "z": "1 120F522F81E6B71556D4CAE43ED6DB3EEE154ABBD4443108E0F41A989682B6E9 1 20FA951E9B7714EAB189BD9AA2BE6F165D86327C01BEB39B2F13737EC8FEC7AC 1 209F1257F3A54ABE76140DDF6740E54BB132A682521359A32AF7B194E55E22E1 1 09F7A59005C49398548E2CF68F03E95F2724BB12432E51A351FC22208EC9B96B 1 1FAD806F8BAA3BD98B32DD9237399C35AB207E7D39C3F240789A3196394B3357 1 0C0DB1C207DAC540DA70556486BEC1671C0B8649CA0685810AFC2C0A2A29A2F1 1 08DF0DF68F7B662130DE9E756695E6DAD8EE7E7FE0CE140FB6E4C8669C51C431 1 1FB49B2822014FC18BDDC7E1FE42561897BEF809B1ED5FDCF4AD3B46975469A0 1 1EDA5FF53A25269912A7646FBE7E9110C443D695C96E70DC41441DB62CA35ADF 1 217FEA48FB4FBFC850A62C621C00F2CCF1E2DBBA118302A2B976E337B74F3F8F 1 0DD4DD3F9350D4026AF31B33213C9CCE27F1771C082676CCC0DB870C46343BC1 1 04C490B80545D203B743579054F8198D7515190649679D0AB8830DFFC3640D0A"
            }
        },
        "tailsHash": TAILS_HASH,
        "tailsLocation": TAILS_URI,
    },
}
REV_REG_ENTRY = {
    "ver": "1.0",
    "value": {
        "accum": "21 11792B036AED0AAA12A46CF39347EB35C865DAC99F767B286F6E37FF0FF4F1CBE 21 12571556D2A1B4475E81295FC8A4F0B66D00FB78EE8C7E15C29C2CA862D0217D4 6 92166D2C2A3BC621AD615136B7229AF051AB026704BF8874F9F0B0106122BF4F 4 2C47BCBBC32904161E2A2926F120AD8F40D94C09D1D97DA735191D27370A68F8 6 8CC19FDA63AB16BEA45050D72478115BC1CCB8E47A854339D2DD5E112976FFF7 4 298B2571FFC63A737B79C131AC7048A1BD474BF907AF13BC42E533C79FB502C7"
    },
}


class TestIssuerRevRegRecord(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"tails_server_base_url": "http://1.2.3.4:8088"},
        )
        self.context = self.profile.context

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.send_revoc_reg_def = async_mock.CoroutineMock()
        self.ledger.send_revoc_reg_entry = async_mock.CoroutineMock()
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)

        TailsServer = async_mock.MagicMock(BaseTailsServer, autospec=True)
        self.tails_server = TailsServer()
        self.tails_server.upload_tails_file = async_mock.CoroutineMock(
            return_value=(True, "http://1.2.3.4:8088/rev-reg-id")
        )
        self.profile.context.injector.bind_instance(BaseTailsServer, self.tails_server)

        self.session = await self.profile.session()

    async def test_order(self):
        async with self.profile.session() as session:
            rec0 = IssuerRevRegRecord()
            await rec0.save(session, reason="a record")
            rec1 = IssuerRevRegRecord()
            await rec1.save(session, reason="another record")
            assert rec0 < rec1

    async def test_fix_ledger_entry(self):
        mock_cred_def = {
            "ver": "1.0",
            "id": "55GkHamhTU1ZbTbV2ab9DE:3:CL:15:tag",
            "schemaId": "15",
            "type": "CL",
            "tag": "tag",
            "value": {
                "primary": {
                    "n": "97755077532337293488745809101840506138839796255951676757957095601046950252131007247574478925999370347259264200571203215922043340992124710162716447600735862203372184211636922189157817784130889637892277882125570534881418101997106854432924131454003284028861730869486619833238782461572414320131411215654018054873708704239239964147885524705957168226001184349267512368273047027640698617139590254809517853853130886625330234652284599369944951191468504513070325577275942459149020744004320427886430812173881305323670033871442431456536710164496981741573947141839358296893048748871620778358547174947418982842584086910766377426381",
                    "s": "93857461424756524831309204327541325286955427618197438652468158979904850495412765053870776608842922458588066684799662534588058064651312983375745531372709501399468055860133002734655992193122962210761579825894255323571233899698407599997585154150003119067126768230932260880730480485869205348502571475803409653237711195597513501909794351191631697504002513031303493339100149587811674358458553310268294288630892274988762794340699542957746255964836213015732087927295229891638172796974267746722775815971385993320758281434138548295910631509522670548769524207136946079991721576359187532370389806940124963337347442220291195381379",
                    "r": {
                        "attr": "47851812221002419738510348434589719299005636707459946297826216114810122000929029718256700990932773158900801032759636000731156275563407397654401429007893443548977293352519606768993036568324588287173469229957113813985349265315838049185336810444812307980611094706266979152047930521019494220669875858786312470775883694491178666122652050631237335108908878703921025524371908258656719798575775820756662770857250313841640739199537587617643616110506607528089021428997787577846819067855712454919148492951257992078447468260961148762693304228013316282905649275245604958548728173709772269908692834231109401462806738322298320014588",
                        "master_secret": "1456034034452917866826058280183727425788793902981406386175016190082488912409448091384258390876182506491481376203626852147024966574074505159095019883608712317385148607657338114099655296899988391276120507283428334300992065352980582993987058928311851237491145495605817715962285966152190021168736714801270287839185496030660074232737687865821410617700173791873244132463428232777257496952831001540198725563550215668732380420651897876237788070219793125826917973396212392661183288071986411608233468079014270033759863563636650489933951357555474357165922955337708555697826065745245669404874498188819137127409608428703992429087",
                    },
                    "rctxt": "3181166664902801317779556377385630436151550717862204865421515198259158965590304479081007449054293128232193810709014084698474265818919401580417293157753663769438333622403413264724381527519123803324371803790394771682351074853790156764071298806108016312946683322202825645967662223488370365263607749486727675784672879635222504232881959377264213229748333060407839919218390751977625946072140500297691925789411870206929445018192788803161174534714033652405735420578422669164795825360682590769380466620583112381320768898271838621002245390378640966896034356391997262998321678222800285339726066703530463747958328257763842981029",
                    "z": "88882571993858813307170085778645601203164536169839951148860666045278872319305671063809074514017614163768224290285339562133145800179699201796197881847784025241295744277627025401945924707873790519590490294771194748427422972923806879605569348426345486261878031328212177481424474160598821738627280954513834712377303213119700398636139443890766009925681362795514758039170870017744796137650484010207378636277505131056606153648732287440383301414486959605962454376715897921966027018433464774363787319454306102402364604589381426633687528444586300536019182461458586285601075166524298872635741326726895166696312685388693673327358",
                },
                "revocation": {
                    "g": "1 1ACDF1F880164FAE240C033DD2CC7E80130264E1A3BC81A3B2BD28E65827E1DA 1 0A4DD8DBB73B2A26CD2A576ECC0C5AB609346EDC923FFF20685EBE3B618A841A 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "g_dash": "1 206CF4DECDE37A09315EE453D08E64CE6EFF4B89D6FCADFB456396AD1C57C442 1 14E36B42881BD9CA04608002810B4C9923BCC52D379A8F216FA57C6392A3BE83 1 138F620C8EEBFEAF9D1EF90152A11B9C0BDF3AED384324767E2293A4FC12F784 1 073227CD0CC0A6D5101A3CE03BDF6D29E6BACB33A090A4AE95F688F45BD54316 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "h": "1 0B608579F0A9A830862E45AC4E97F5CB30FD118379A1C408363D92970DBE989C 1 1671922BCECA4E69B693851EA3C78CB3B2714CACAAB64DD5B5CF3C5A187A572A 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h0": "1 1BCE3325E76EF9FA7566732BD17B5B82B1D0E9559B393D368A0BD09761AE2A39 1 10A1DA70F60369FBD69742B1564E98C85188312CFCCDD8AD5D11978F3FA1376D 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h1": "1 145B2DB05BFAAB9AF90401897E318B73BCEE7178D2857A551561DE0893098137 1 17A23E4161EF4392A56F13B2B0F40E0FA1DD28CDBD3FF33FDD67C5D998A10B6D 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h2": "1 14E18A1496B043246A4A860159EFCF49621606AF3E46A9854B8949E9F8C0FD97 1 1EFE5D486448A8F7A44BE358B674C0CF6FF09AAFDDDA416462943311CCA1A291 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "htilde": "1 152FBD85CD4C81796599582D2CFE37407760B348A7816ADE2C9B76077C62440D 1 23DDDD15C99111413585FD282E05095FC27803EA8DCF94570B3FD2A53658AE00 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "h_cap": "1 06333FED8C082FE894D02CC04A53B78D801ABC9CE09D0C5B731FEDF82A1BBB5F 1 06FD92996796D6B81F7803C3CEA3891741552B452E3F6C735F5BFE096234442A 1 23C5C9462697381BDF16658D133E5B0888C909E0EA01F041FEDC8E3A4F84BBF6 1 0511A0E8510AAF8454EB78446C563A8719622DADFF4AE86DF07E2969D2E4E48F 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "u": "1 1566C7AC1F99896C4E0CD7BD1B77C241614CE03337201FC6BB886650D78AC20D 1 1C73D8607361E539355F39297C3D8073B6CCA2DBF8A7AC50A50BF2FF20CAD7E9 1 1BF4F8AAE80EFAE308FF9ED399F24546306623EE8BECF6A2B39D939B1FCE94DA 1 0646620C014AD0A78BF83748F165211EFF811B526859F71AD184DA462A0C9303 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                    "pk": "1 16373692E1B40E44D2010B1CC7023E89E96DD9F45DB3F837D532A1299E80DB23 1 0A0DA35D2830848D4C04FADBB3E726525ADE9DC5F3364AB6286F642E904BB913 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8",
                    "y": "1 1C132346B6D6999F872132568ACB6F722FF4F93E08F0F6A1433E25F0937FBCB8 1 093034020F4F2087FDAA63D2EBD9BC02A7FF88F914F5971F285CD21BC200F9BD 1 04FB2599E6FA39E12F7F4A9B1C152E753E6584755843D7B6F746904A78396650 1 2291AC4F56DC5E0FEA5C580ACC2521714A3A8F3C79D78D475AEC473FB631E131 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000",
                },
            },
        }
        mock_reg_rev_def_private = {
            "value": {
                "gamma": "11D1EF7D29B67A898E8BFDECEF24AD3B23A4984636F31AA84E1958A724A3579A"
            }
        }

        class TestProfile(InMemoryProfile):
            def session(self, context: InjectionContext = None) -> "ProfileSession":
                return TestProfileSession(self, context=context)

            @classmethod
            def test_profile(
                cls, settings: Mapping[str, Any] = None, bind: Mapping[Type, Any] = None
            ) -> "TestProfile":
                profile = TestProfile(
                    context=InjectionContext(enforce_typing=False, settings=settings),
                    name=InMemoryProfile.TEST_PROFILE_NAME,
                )
                if bind:
                    for k, v in bind.items():
                        if v:
                            profile.context.injector.bind_instance(k, v)
                        else:
                            profile.context.injector.clear_binding(k)
                return profile

            @classmethod
            def test_session(
                cls, settings: Mapping[str, Any] = None, bind: Mapping[Type, Any] = None
            ) -> "TestProfileSession":
                session = TestProfileSession(cls.test_profile(), settings=settings)
                session._active = True
                session._init_context()
                if bind:
                    for k, v in bind.items():
                        if v:
                            session.context.injector.bind_instance(k, v)
                        else:
                            session.context.injector.clear_binding(k)
                return session

        class TestProfileSession(InMemoryProfileSession):
            def __init__(
                self,
                profile: Profile,
                *,
                context: InjectionContext = None,
                settings: Mapping[str, Any] = None,
            ):
                super().__init__(profile=profile, context=context, settings=settings)
                self.handle_counter = 0

            @property
            def handle(self):
                if self.handle_counter == 0:
                    self.handle_counter = self.handle_counter + 1
                    return async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=async_mock.MagicMock(
                                value_json=json.dumps(mock_cred_def)
                            )
                        )
                    )
                else:
                    return async_mock.MagicMock(
                        fetch=async_mock.CoroutineMock(
                            return_value=async_mock.MagicMock(
                                value_json=json.dumps(mock_reg_rev_def_private),
                            ),
                        )
                    )

        credx_module = importlib.import_module("indy_credx")
        rev_reg_delta = credx_module.RevocationRegistryDelta.load(
            json.dumps(
                {
                    "ver": "1.0",
                    "value": {
                        "accum": "1 0792BD1C8C1A529173FDF54A5B30AC90C2472956622E9F04971D36A9BF77C2C5 1 13B18B6B68AD62605C74FD61088814338EDEEB41C2195F96EC0E83B2B3D0258F 1 102ED0DDE96F6367199CE1C0B138F172BC913B65E37250581606974034F4CA20 1 1C53786D2C15190B57167CDDD2A046CAD63970B5DE43F4D492D4F46B8EEE6FF1 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000"
                    },
                }
            )
        )

        TEST_GENESIS_TXN = "test_genesis_txn"
        rec = IssuerRevRegRecord(
            issuer_did=TEST_DID,
            revoc_reg_id=REV_REG_ID,
            revoc_reg_def=REV_REG_DEF,
            revoc_def_type="CL_ACCUM",
            revoc_reg_entry=REV_REG_ENTRY,
            cred_def_id=CRED_DEF_ID,
            tails_public_uri=TAILS_URI,
        )
        _test_rev_reg_delta = {
            "ver": "1.0",
            "value": {"accum": "ACCUM", "issued": [1, 2], "revoked": [3, 4]},
        }
        self.ledger.get_revoc_reg_delta = async_mock.CoroutineMock(
            return_value=(
                _test_rev_reg_delta,
                1234567890,
            )
        )
        self.ledger.send_revoc_reg_entry = async_mock.CoroutineMock(
            return_value={
                "result": {"...": "..."},
            },
        )
        _test_session = TestProfile.test_session(
            settings={"tails_server_base_url": "http://1.2.3.4:8088"},
        )
        _test_profile = _test_session.profile
        _test_profile.context.injector.bind_instance(BaseLedger, self.ledger)
        with async_mock.patch.object(
            test_module.IssuerCredRevRecord,
            "query_by_ids",
            async_mock.CoroutineMock(
                return_value=[
                    test_module.IssuerCredRevRecord(
                        record_id=test_module.UUID4_EXAMPLE,
                        state=test_module.IssuerCredRevRecord.STATE_REVOKED,
                        cred_ex_id=test_module.UUID4_EXAMPLE,
                        rev_reg_id=REV_REG_ID,
                        cred_rev_id="1",
                    )
                ]
            ),
        ), async_mock.patch.object(
            test_module.IssuerRevRegRecord,
            "retrieve_by_revoc_reg_id",
            async_mock.CoroutineMock(return_value=rec),
        ), async_mock.patch.object(
            test_module,
            "generate_ledger_rrrecovery_txn",
            async_mock.CoroutineMock(return_value=rev_reg_delta),
        ):
            assert (
                _test_rev_reg_delta,
                {
                    "ver": "1.0",
                    "value": {
                        "accum": "1 0792BD1C8C1A529173FDF54A5B30AC90C2472956622E9F04971D36A9BF77C2C5 1 13B18B6B68AD62605C74FD61088814338EDEEB41C2195F96EC0E83B2B3D0258F 1 102ED0DDE96F6367199CE1C0B138F172BC913B65E37250581606974034F4CA20 1 1C53786D2C15190B57167CDDD2A046CAD63970B5DE43F4D492D4F46B8EEE6FF1 2 095E45DDF417D05FB10933FFC63D474548B7FFFF7888802F07FFFFFF7D07A8A8 1 0000000000000000000000000000000000000000000000000000000000000000"
                    },
                },
                {"...": "..."},
            ) == await rec.fix_ledger_entry(
                profile=_test_profile,
                apply_ledger_update=True,
                genesis_transactions=json.dumps(TEST_GENESIS_TXN),
            )

    async def test_generate_registry_etc(self):
        rec = IssuerRevRegRecord(
            issuer_did=TEST_DID,
            cred_def_id=CRED_DEF_ID,
            revoc_reg_id=REV_REG_ID,
        )
        issuer = async_mock.MagicMock(IndyIssuer)
        self.profile.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            issuer, "create_and_store_revocation_registry", async_mock.CoroutineMock()
        ) as mock_create_store_rr:
            mock_create_store_rr.side_effect = IndyIssuerError("Not this time")

            with self.assertRaises(RevocationError):
                await rec.generate_registry(self.profile)

        issuer.create_and_store_revocation_registry.return_value = (
            REV_REG_ID,
            json.dumps(REV_REG_DEF),
            json.dumps(REV_REG_ENTRY),
        )

        with async_mock.patch.object(
            test_module, "move", async_mock.MagicMock()
        ) as mock_move:
            await rec.generate_registry(self.profile)

        assert rec.revoc_reg_id == REV_REG_ID
        assert rec.state == IssuerRevRegRecord.STATE_GENERATED
        assert rec.tails_hash == TAILS_HASH
        assert rec.tails_local_path == join(
            indy_client_dir(join("tails", REV_REG_ID)), rec.tails_hash
        )
        with self.assertRaises(RevocationError):
            await rec.set_tails_file_public_uri(self.profile, "dummy")

        await rec.set_tails_file_public_uri(self.profile, TAILS_URI)
        assert rec.tails_public_uri == TAILS_URI
        assert rec.revoc_reg_def.value.tails_location == TAILS_URI

        await rec.send_def(self.profile)
        assert rec.state == IssuerRevRegRecord.STATE_POSTED
        self.ledger.send_revoc_reg_def.assert_called_once()

        with async_mock.patch.object(test_module.Path, "is_file", lambda _: True):
            await rec.upload_tails_file(self.profile)
        assert (
            rec.tails_public_uri
            and rec.revoc_reg_def.value.tails_location == rec.tails_public_uri
        )
        self.tails_server.upload_tails_file.assert_called_once()

        await rec.send_entry(self.profile)
        assert rec.state == IssuerRevRegRecord.STATE_ACTIVE
        self.ledger.send_revoc_reg_entry.assert_called_once()

        rev_reg = rec.get_registry()
        assert type(rev_reg) == RevocationRegistry

        async with self.profile.session() as session:
            queried = await IssuerRevRegRecord.query_by_cred_def_id(
                session=session,
                cred_def_id=CRED_DEF_ID,
                state=IssuerRevRegRecord.STATE_ACTIVE,
            )
            assert len(queried) == 1

            retrieved = await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                session=session, revoc_reg_id=rec.revoc_reg_id
            )
            assert retrieved.revoc_reg_id == rec.revoc_reg_id

            await rec.set_state(session)
            assert rec.state == IssuerRevRegRecord.STATE_FULL

        data = rec.serialize()
        model_instance = IssuerRevRegRecord.deserialize(data)
        assert isinstance(model_instance, IssuerRevRegRecord)
        assert model_instance == rec

    async def test_operate_on_full_record(self):
        rec_full = IssuerRevRegRecord(
            issuer_did=TEST_DID,
            revoc_reg_id=REV_REG_ID,
            revoc_reg_def=REV_REG_DEF,
            revoc_def_type="CL_ACCUM",
            revoc_reg_entry=REV_REG_ENTRY,
            cred_def_id=CRED_DEF_ID,
            state=IssuerRevRegRecord.STATE_FULL,
            tails_public_uri=TAILS_URI,
        )

        with self.assertRaises(RevocationError) as x_state:
            await rec_full.generate_registry(self.profile)

        with self.assertRaises(RevocationError) as x_state:
            await rec_full.send_def(self.profile)

        rec_full.state = IssuerRevRegRecord.STATE_INIT
        with self.assertRaises(RevocationError) as x_state:
            await rec_full.send_entry(self.profile)

    async def test_pending(self):
        async with self.profile.session() as session:
            rec = IssuerRevRegRecord()
            await rec.mark_pending(session, "1")
            await rec.mark_pending(session, "2")
            await rec.mark_pending(session, "3")
            await rec.mark_pending(session, "4")

            found = await IssuerRevRegRecord.query_by_pending(session)
            assert len(found) == 1 and found[0] == rec

            await rec.clear_pending(session, ["1", "2"])
            assert rec.pending_pub == ["3", "4"]
            found = await IssuerRevRegRecord.query_by_pending(session)
            assert found

            await rec.clear_pending(session, [])
            assert rec.pending_pub == []
            found = await IssuerRevRegRecord.query_by_pending(session)
            assert not found

            await rec.mark_pending(session, "5")
            await rec.mark_pending(session, "6")

            await rec.clear_pending(session, [])
            assert rec.pending_pub == []
            found = await IssuerRevRegRecord.query_by_pending(session)
            assert not found

    async def test_set_tails_file_public_uri_rev_reg_undef(self):
        rec = IssuerRevRegRecord()
        with self.assertRaises(RevocationError):
            await rec.set_tails_file_public_uri(self.profile, "dummy")

    async def test_send_rev_reg_undef(self):
        rec = IssuerRevRegRecord()
        with self.assertRaises(RevocationError):
            await rec.send_def(self.profile)

        with self.assertRaises(RevocationError):
            await rec.send_entry(self.profile)
