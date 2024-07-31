"""test prove.py"""

import pytest
from aries_cloudagent.anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from aries_cloudagent.anoncreds.tests.mock_objects import MOCK_W3CPRES
from aries_cloudagent.revocation.models.revocation_registry import RevocationRegistry
from aries_cloudagent.vc.ld_proofs.error import LinkedDataProofException
from aries_cloudagent.anoncreds.registry import AnonCredsRegistry
from aries_cloudagent.tests import mock
from ....core.in_memory.profile import InMemoryProfile
from ....core.profile import Profile
from ....resolver.default.key import KeyDIDResolver
from ....resolver.did_resolver import DIDResolver
from ....wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ....wallet.did_method import DIDMethods
from ...ld_proofs.document_loader import DocumentLoader

from ..prove import (
    _extract_cred_idx,
    _get_predicate_type_and_value,
    _load_w3c_credentials,
    create_rev_states,
    create_signed_anoncreds_presentation,
)
from .test_manager import VC
from anoncreds import RevocationStatusList, CredentialRevocationState


@pytest.fixture
def resolver():
    yield DIDResolver([KeyDIDResolver()])


@pytest.fixture
def profile(resolver: DIDResolver):
    profile = InMemoryProfile.test_profile(
        {},
        {
            DIDMethods: DIDMethods(),
            BaseVerificationKeyStrategy: DefaultVerificationKeyStrategy(),
            DIDResolver: resolver,
        },
    )
    profile.context.injector.bind_instance(DocumentLoader, DocumentLoader(profile))
    yield profile


@pytest.mark.asyncio
async def test_create_signed_anoncreds_presentation(profile: Profile):
    profile.context.injector.bind_instance(
        AnonCredsRegistry,
        mock.MagicMock(
            get_schema=mock.CoroutineMock(
                return_value=mock.MagicMock(
                    schema=mock.MagicMock(
                        serialize=mock.MagicMock(
                            return_value={
                                "issuerId": "TNuyNH2pAW2G6z3BW8ZYLf",
                                "attrNames": [
                                    "degree",
                                    "name",
                                    "date",
                                    "birthdate_dateint",
                                    "timestamp",
                                ],
                                "name": "degree schema",
                                "version": "68.37.38",
                            }
                        )
                    )
                ),
            ),
            get_credential_definition=mock.CoroutineMock(
                return_value=mock.MagicMock(
                    credential_definition=mock.MagicMock(
                        serialize=mock.MagicMock(
                            return_value={
                                "issuerId": "TNuyNH2pAW2G6z3BW8ZYLf",
                                "schemaId": "1242274",
                                "type": "CL",
                                "tag": "faber.agent.degree_schema",
                                "value": {
                                    "primary": {
                                        "n": "110191895107383177944225186787127045472400456419044508847920073749118325816882879555888693590503408107531218246551508200778858813446764597252042460295740219285296989541107769089502181778576777417930436325553990675031577262316859960188786027427415918907113489291521324039356114616863101480866513302357191568489145237650236954578848085540776058357840327446186761324850043360872510240168860114128657413033422322367730714244593033343815255367880227269514752281182456165390304117532268729405376542376337985308310279351286237047011259755660096523481882637528390140070572293678914392133356847907443964699396666368223294158061",
                                        "s": "9415812539608195450966883098870652296916491635505203853080983952632805384302967432306788150605939803147875077062094749099736966082292346688785945337831356656890556951983186155154365222554857316130536164238857088110797546973073757951768643832909466949503368156244645826883930998004092294090171380523954224832439522626754713977466892117127635439861663437421962242296372559287964629293301712321588335521469805244310171886131183734977508209622245349508899886419257943124600270414702700150921447687226557458680951807835253145114264110732291146813141269571018474399690170085303553149912953395770110046436238930438812780147",
                                        "r": {
                                            "birthdate_dateint": "39968681640304788380009477273748351837529664198759676077165379337792646675901616432152370797900826515094147804138445249213613945496792933661400605498715980120831712924000357777147499418810050923414071460841739245157420435453468918475700941287524373324079549579873246517784186882218530939272891114746579591872034727864365855842228114509998007945460010480245507010064392110362136591952150320820422225826544285688677068642300714078641169340591902569248592823824054227933825730852985690007682552923384746004484874059862968040467406436797474876079422807683482900156405231629390843729772887675489043282470807407031205186969",
                                            "date": "1189483679228280739072650972354053068606455987118485184085207434597201188158334235777355692068087062063721870127753534657818335769737924323208415920434077874887496282538032440486476302782516445945959644735720202525994434469144049628428271543868582987595621454107048590112351992445017094207270819619996701213546548131486236291413202271720647291688756231888188593794699964380031588638888843772851461391755221206371940247603348559507718057920345380550594583486893575953718560696958190724499821774481967602504818394556262808918356126374081669920344874855870303258253201308390418654588788321421245107716899898452672677669",
                                            "degree": "7930507600973622255761968698285828306846788291380201483787889093576185243433070380250482080700646211095178134232253270069460369492303935894012408118127081015494559256719242506733590055152439637360319677447051969350390638377492011800932771226273035358153040455317319159092480932337395314046192165987582330687751669998427678060271101315462477794016231639142468258481489055468781240927905148904953855558036223028111290216890655943559980456204339868018478633494472724669957163721224817260017913056937034080193667933454564153001308165996679854735603451224195324968916426779531862123459043377650779177644556309703126058569",
                                            "master_secret": "276481248076029901397915904197571939766835573218052607192738620704710670905748562925445909482694999303080385244124333488797597869947177554955868568791587429441803954589662661470453559603193697529455695636193068394109938416082954992003652270737665467573503772195889460315616035410445104017129549757818399000451038212677658874397388131875030264607848961441095008175483303770912033940379028110558590125358672540783519319152844457014577027814244423449014637405165845051430105495276716743166413876676529214061455612429316323214502293979149015655581759299623912651153921930483011898615547608936905586870150072549489722497",
                                            "name": "82868656041023829484169603686526910742809130312561664067502441442293881789487387499604367473067725155834966664040618821809499511114213661657225202206321891616189181748382445256076664775972124872336589185892368887947537027000430124719570575062210504764164198906984696516109885071145245277063304337918433238788453702459065343194907264612324316538889460640366702448456177503504044952464912882387589287029922982523474901886018581567364020613890822736197654463892632953961461903659266302672901927472391491520220790086494421629530104134487848960992291400448418880719301301643211538480715261724678645854026893882662935786454",
                                            "timestamp": "7031267523384255931724229734709668852236981666398664500628609312084184839422714066646111517571504367881906999946906142205880431579116282139457459430490628368074988968893818537384306625760198775803846638688715282693724689063695143781851672316171826804538178049496230705683899355140338093894078404749873276975725352612375324676593660719462779985715395422238940426215008469041353116398836478202492841783866649731302994305254257899941902815383605743664381990123198126148381917220067404201702094151978496034163563512821780561363033330132250212505439974465744473015256287665802141980858496388564369684473390614913213492963",
                                        },
                                        "rctxt": "57595457065224964384532723809214070177221283698619189163273994795484340422910421565194502650047793930986106754378617657953634148479003200343596849944404829819454759272470409952906484645890312928698071525795674306099322535554040769358088959541527217412947857624113771388855906636033132647358149811523979540215755447957501980890442007680654813076936017670559128454293737368578572852087014890823425797572658699153814350307873126659084777516770578065919757432552875676249519945052600028967301682399735687262474002867432540942797659023173846671235714105519229325988649284822140546012838121486756140885474564667338033508925",
                                        "z": "92392248633579159734489059262157658066602172492655376458258465743015720279931884516580613066265472490833888951133646441506435308647071645829490880133890938400531213056849488446865347760761739826520600426315831962473284037732716361460703303047650224879262380737182724193613502180709449361207809530289742931388401783902150303407116160750968583373664158158828048355594343560019377499225431222258609781090866038688202681876195069528239050879910722452167883110680950451692711483330249956590291961929310759534360045884090140017202751268354570741889324005873479145636960045391944928193003593085006050343477314073342608326752",
                                    }
                                },
                            }
                        )
                    )
                )
            ),
        ),
    )

    with mock.patch.object(
        AnonCredsHolder, "create_presentation_w3c", return_value=MOCK_W3CPRES
    ) as mock_create_pres:
        await create_signed_anoncreds_presentation(
            profile=profile,
            pres_definition={
                "id": "5591656f-5b5d-40f8-ab5c-9041c8e3a6a0",
                "name": "Age Verification",
                "purpose": "We need to verify your age before entering a bar",
                "format": {
                    "di_vc": {
                        "proof_type": ["DataIntegrityProof"],
                        "cryptosuite": ["anoncreds-2023", "eddsa-rdfc-2022"],
                    }
                },
                "input_descriptors": [
                    {
                        "id": "age-verification",
                        "name": "A specific type of VC + Issuer",
                        "purpose": "We want a VC of this type generated by this issuer",
                        "constraints": {
                            "limit_disclosure": "required",
                            "fields": [
                                {
                                    "path": ["$.issuer"],
                                    "filter": {
                                        "type": "string",
                                        "const": "7yDP6qARVAp1Rims8Fj43k",
                                    },
                                },
                                {"path": ["$.credentialSubject.name"]},
                                {"path": ["$.credentialSubject.degree"]},
                                {
                                    "path": ["$.credentialSubject.birthdate_dateint"],
                                    "predicate": "preferred",
                                    "filter": {"type": "number", "maximum": 20060711},
                                },
                            ],
                            "statuses": {
                                "active": {"directive": "disallowed"},
                                "suspended": {"directive": None},
                                "revoked": {"directive": None},
                            },
                        },
                        "schema": {
                            "uri_groups": [
                                [
                                    {
                                        "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                                    }
                                ]
                            ],
                            "oneof_filter": False,
                        },
                    }
                ],
            },
            presentation={
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "verifiableCredential": [
                    {
                        "@context": [
                            "https://www.w3.org/2018/credentials/v1",
                            "https://w3id.org/security/data-integrity/v2",
                            {
                                "@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"
                            },
                        ],
                        "type": ["VerifiableCredential"],
                        "issuer": "7yDP6qARVAp1Rims8Fj43k",
                        "issuanceDate": "2024-07-11T18:33:24.564345117Z",
                        "credentialSubject": {
                            "name": "Alice Smith",
                            "date": "2018-05-28",
                            "timestamp": 1720722800,
                            "degree": "Maths",
                            "birthdate_dateint": 20000711,
                        },
                        "proof": {
                            "type": "DataIntegrityProof",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "7yDP6qARVAp1Rims8Fj43k:3:CL:1255455:faber.agent.degree_schema",
                            "proofValue": "ukgGEqXNjaGVtYV9pZNkvN3lEUDZxQVJWQXAxUmltczhGajQzazoyOmRlZ3JlZSBzY2hlbWE6NDYuMzkuNzmrY3JlZF9kZWZfaWTZPTd5RFA2cUFSVkFwMVJpbXM4Rmo0M2s6MzpDTDoxMjU1NDU1OmZhYmVyLmFnZW50LmRlZ3JlZV9zY2hlbWGpc2lnbmF0dXJlgqxwX2NyZWRlbnRpYWyEo21fMtwAIFHM9cyPzOMsEls6E3zMtC0BaMzTGsyazNzMnsz2zL9lzJHMj8zHaczATsyUYi7Mv6Fh3AEBAsy8zMrMwFHM5MzHzPTMxQc-zPjM68ywV8ypXszEzJLMv8yaNczYDhvMqR7M9CzMv8yweszIccyqCWHMiwbMrGrMyRU0zOTM2sypBczfzII7VksbBMzXTRzMyhjM2idFNsyCBszDOMzVzLDM3cy8IVDMy0YETSfM_VFwzPfM-gdaAcyUNBJ8zPxgeszLO8zwzNjM98zPNFgKBRXM_mZ4zIXMnszOzOjMscyNJQTMmszjD3drzMXMgSBAzJ_M8MzkawYXzP7MrszKzLJPzPXMjEd8HsyzEczBzNEmzJ7Mkl_Mmcz0csziGk9eVD9ezMEfchjMzsyFJsyhQj_MrczyzLDMtWYczIorzMULzPbM0mUSzP1aR8zvzJQRQcyuzP1czK8TDQxSK8zjzOZ8zKIFUcyXzPZpdk9PzLpLNczzHyTM7SU5zJQFRcyaWAdcWczodSfMkszKAmLM7igjeMz_zN3Ms8zAT0TM2cyYJmEqzODM20rM8klTzPChZdwASxAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMozMsWzN3M8MzSDg3MhsyTzLRLzIwzoXbcAVUMzM3MlCDMhMyMH1LMigd7JEUHIMzuW8yQJT8iAm7Mpw5nAsyTzKbMtsyUzPUzzK9FzLLMkFLMzynMu8yEzN5nO8z3FjvMiszIzJbM3cywWMzTEszQzPzMx8yNBcycexcle8yIzJfMycyTQszUMBTMg8zGzNPMisz3zLhnEszDdcyozLXM1TYFzPRCO8zfcSQLNGPMoszyf8yfCwtVzNbM18zJzNDMscyzzJbM3l3Mh8zPzKYhCcyXzIrM98ykzODMiczSzJPMgRXMgnDMhkLMhCLMkwRkzKotF8yDzPbMmGzMoC4LRMyZzJ3M8w7MvczHLcyzzMTMmCdJzILMwUHM98zMzPpSDyLM5X7M2kXMg8yQXHvM8MyqV0nMmAgQzKx9LTM2V8zlzLLMv8z8zPJqTMzjR8zLFlU2KFRHc8zXzOfMrMzSdArM7CDMksykzM3MjMznLGo-zLzM7QVqzPXM6Bl9aMzgzIsSzLlpNMyYa8z5zId1BnNyzPUxZczyX8zSzNYKfMzIzJPM2QvM_MzIzLvMvRw4ZgwgzLkvGszAKszmMMzfzLbM4czQRGfM21Z5PzsxzIRlzJETzNszMMydzOdAzObMuczJzJUZzKgXzJ_MlG0PDcz4QCXMpwDMyszXzPMVzOFrzKjM3hc6zP_M-sz3XMyfS1vMvF_Mlsz7MMzozKzMk8y0rHJfY3JlZGVudGlhbMC7c2lnbmF0dXJlX2NvcnJlY3RuZXNzX3Byb29mgqJzZdwBAMy0zO7MyszkzN7MxcyVQMy3zNEdzKBvzMfMq2Q5agJwG8yazPjMpMyQzJ1JV8z_zOrMkMzWzKPMjcybPMyHX8yVzMDM-WBwBcz6zN0yHRbMnSDMoMyXHMynzOfMlMyiCnfM-Mylb8zKzPBHzMrMm1TM2l7Mp8zCQMyyzIYHzMBXzPJFf04lzPpYzKLM7sykKMzHzJgJzNoTJEVtzP5KzJ7Mz8yAXUPM-13M18yQWhpOXszRFczqzI3MqszDJ8yjE2V-zLxUzPpDUknMrh_Mu0sVzJBAzMgqfX1ZF8zRzLzMr8zIzKtdeRbM4szqCFnMqczXdsyIPMzXzK_MhQTM5sypzOrM5MziHlXMxxrMpMzTzPjMjXbMzEZxNsykzJRKFjXM-XtYzIcEzJzMgMynzITMyWxpEix9zOvM1cy5ZcyacMzJLMzxzN9OzM3MuV7M28z7zKQRHsyXzPDMvczhB8zgzNrMmxwhJMydEhPMhUkvzIHM3cytzL8CIiLMtczJzOLMlMyZOMzOzLcizOwAoWPcACAvzI_MrkTMvDvMmMy2zIvMizDM0ihSzMd_VGDMvMzEWn3MrczcbMykzKNqzLgzzKvMzw",
                            "cryptosuite": "anoncreds-2023",
                        },
                    }
                ],
                "presentation_submission": {
                    "id": "700e4ed4-bb73-403f-a73c-e456556cbdf0",
                    "definition_id": "5591656f-5b5d-40f8-ab5c-9041c8e3a6a0",
                    "descriptor_map": [
                        {
                            "id": "age-verification",
                            "format": "ldp_vc",
                            "path": "$.verifiableCredential[0]",
                        }
                    ],
                },
            },
            challenge="3fa85f64-5717-4562-b3fc-2c963f66afa7",
            domain="domain",
            credentials=[
                {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/security/data-integrity/v2",
                        {
                            "@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"
                        },
                    ],
                    "type": ["VerifiableCredential"],
                    "issuer": "7yDP6qARVAp1Rims8Fj43k",
                    "issuanceDate": "2024-07-11T18:33:24.564345117Z",
                    "credentialSubject": {
                        "name": "Alice Smith",
                        "date": "2018-05-28",
                        "timestamp": 1720722800,
                        "degree": "Maths",
                        "birthdate_dateint": 20000711,
                    },
                    "proof": {
                        "type": "DataIntegrityProof",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": "7yDP6qARVAp1Rims8Fj43k:3:CL:1255455:faber.agent.degree_schema",
                        "proofValue": "ukgGEqXNjaGVtYV9pZNkvN3lEUDZxQVJWQXAxUmltczhGajQzazoyOmRlZ3JlZSBzY2hlbWE6NDYuMzkuNzmrY3JlZF9kZWZfaWTZPTd5RFA2cUFSVkFwMVJpbXM4Rmo0M2s6MzpDTDoxMjU1NDU1OmZhYmVyLmFnZW50LmRlZ3JlZV9zY2hlbWGpc2lnbmF0dXJlgqxwX2NyZWRlbnRpYWyEo21fMtwAIFHM9cyPzOMsEls6E3zMtC0BaMzTGsyazNzMnsz2zL9lzJHMj8zHaczATsyUYi7Mv6Fh3AEBAsy8zMrMwFHM5MzHzPTMxQc-zPjM68ywV8ypXszEzJLMv8yaNczYDhvMqR7M9CzMv8yweszIccyqCWHMiwbMrGrMyRU0zOTM2sypBczfzII7VksbBMzXTRzMyhjM2idFNsyCBszDOMzVzLDM3cy8IVDMy0YETSfM_VFwzPfM-gdaAcyUNBJ8zPxgeszLO8zwzNjM98zPNFgKBRXM_mZ4zIXMnszOzOjMscyNJQTMmszjD3drzMXMgSBAzJ_M8MzkawYXzP7MrszKzLJPzPXMjEd8HsyzEczBzNEmzJ7Mkl_Mmcz0csziGk9eVD9ezMEfchjMzsyFJsyhQj_MrczyzLDMtWYczIorzMULzPbM0mUSzP1aR8zvzJQRQcyuzP1czK8TDQxSK8zjzOZ8zKIFUcyXzPZpdk9PzLpLNczzHyTM7SU5zJQFRcyaWAdcWczodSfMkszKAmLM7igjeMz_zN3Ms8zAT0TM2cyYJmEqzODM20rM8klTzPChZdwASxAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMozMsWzN3M8MzSDg3MhsyTzLRLzIwzoXbcAVUMzM3MlCDMhMyMH1LMigd7JEUHIMzuW8yQJT8iAm7Mpw5nAsyTzKbMtsyUzPUzzK9FzLLMkFLMzynMu8yEzN5nO8z3FjvMiszIzJbM3cywWMzTEszQzPzMx8yNBcycexcle8yIzJfMycyTQszUMBTMg8zGzNPMisz3zLhnEszDdcyozLXM1TYFzPRCO8zfcSQLNGPMoszyf8yfCwtVzNbM18zJzNDMscyzzJbM3l3Mh8zPzKYhCcyXzIrM98ykzODMiczSzJPMgRXMgnDMhkLMhCLMkwRkzKotF8yDzPbMmGzMoC4LRMyZzJ3M8w7MvczHLcyzzMTMmCdJzILMwUHM98zMzPpSDyLM5X7M2kXMg8yQXHvM8MyqV0nMmAgQzKx9LTM2V8zlzLLMv8z8zPJqTMzjR8zLFlU2KFRHc8zXzOfMrMzSdArM7CDMksykzM3MjMznLGo-zLzM7QVqzPXM6Bl9aMzgzIsSzLlpNMyYa8z5zId1BnNyzPUxZczyX8zSzNYKfMzIzJPM2QvM_MzIzLvMvRw4ZgwgzLkvGszAKszmMMzfzLbM4czQRGfM21Z5PzsxzIRlzJETzNszMMydzOdAzObMuczJzJUZzKgXzJ_MlG0PDcz4QCXMpwDMyszXzPMVzOFrzKjM3hc6zP_M-sz3XMyfS1vMvF_Mlsz7MMzozKzMk8y0rHJfY3JlZGVudGlhbMC7c2lnbmF0dXJlX2NvcnJlY3RuZXNzX3Byb29mgqJzZdwBAMy0zO7MyszkzN7MxcyVQMy3zNEdzKBvzMfMq2Q5agJwG8yazPjMpMyQzJ1JV8z_zOrMkMzWzKPMjcybPMyHX8yVzMDM-WBwBcz6zN0yHRbMnSDMoMyXHMynzOfMlMyiCnfM-Mylb8zKzPBHzMrMm1TM2l7Mp8zCQMyyzIYHzMBXzPJFf04lzPpYzKLM7sykKMzHzJgJzNoTJEVtzP5KzJ7Mz8yAXUPM-13M18yQWhpOXszRFczqzI3MqszDJ8yjE2V-zLxUzPpDUknMrh_Mu0sVzJBAzMgqfX1ZF8zRzLzMr8zIzKtdeRbM4szqCFnMqczXdsyIPMzXzK_MhQTM5sypzOrM5MziHlXMxxrMpMzTzPjMjXbMzEZxNsykzJRKFjXM-XtYzIcEzJzMgMynzITMyWxpEix9zOvM1cy5ZcyacMzJLMzxzN9OzM3MuV7M28z7zKQRHsyXzPDMvczhB8zgzNrMmxwhJMydEhPMhUkvzIHM3cytzL8CIiLMtczJzOLMlMyZOMzOzLcizOwAoWPcACAvzI_MrkTMvDvMmMy2zIvMizDM0ihSzMd_VGDMvMzEWn3MrczcbMykzKNqzLgzzKvMzw",
                        "cryptosuite": "anoncreds-2023",
                    },
                }
            ],
            purpose="assertionMethod",
        )

        mock_create_pres.assert_called_once()


def test__extract_cred_idx():
    item_path = "$.verifiableCredential[0]"
    assert _extract_cred_idx(item_path) == 0

    item_path = "$.verifiableCredential[42]"
    assert _extract_cred_idx(item_path) == 42


def test__get_predicate_type_and_value():
    pred_filter: dict[str, int] = {"exclusiveMinimum": 10}
    assert _get_predicate_type_and_value(pred_filter) == (">", 10)

    pred_filter = {"exclusiveMaximum": 20}
    assert _get_predicate_type_and_value(pred_filter) == ("<", 20)

    pred_filter = {"minimum": 5}
    assert _get_predicate_type_and_value(pred_filter) == (">=", 5)

    pred_filter = {"maximum": 15}
    assert _get_predicate_type_and_value(pred_filter) == ("<=", 15)


@pytest.mark.asyncio
async def test__load_w3c_credentials():
    credentials = [VC]

    w3c_creds = await _load_w3c_credentials(credentials)

    assert len(w3c_creds) == len(credentials)

    with pytest.raises(LinkedDataProofException) as context:
        credentials = [{"schema": "invalid"}]
        await _load_w3c_credentials(credentials)
    assert "Error loading credential as W3C credential"


@pytest.mark.asyncio
async def test_create_rev_states():
    w3c_creds_metadata = [
        {"rev_reg_id": "rev_reg_id_1", "rev_reg_index": 0, "timestamp": 1234567890},
        {"rev_reg_id": "rev_reg_id_2", "rev_reg_index": 1, "timestamp": 1234567890},
    ]
    rev_reg_defs = {
        "rev_reg_id_1": {"id": "rev_reg_id_1", "definition": "rev_reg_def_1"},
        "rev_reg_id_2": {"id": "rev_reg_id_2", "definition": "rev_reg_def_2"},
    }
    rev_reg_entries = {
        "rev_reg_id_1": {1234567890: "rev_reg_entry_1"},
        "rev_reg_id_2": {1234567890: "rev_reg_entry_2"},
    }

    with mock.patch.object(
        RevocationRegistry,
        "from_definition",
        return_value=mock.CoroutineMock(
            get_or_fetch_local_tails_path=mock.CoroutineMock(return_value="tails_path")
        ),
    ):
        with mock.patch.object(
            RevocationStatusList, "load", return_value=mock.MagicMock()
        ):
            with pytest.raises(AnonCredsHolderError):
                await create_rev_states(
                    w3c_creds_metadata, rev_reg_defs, rev_reg_entries
                )
            with mock.patch.object(
                CredentialRevocationState, "create", return_value=mock.MagicMock()
            ) as mock_create:

                result = await create_rev_states(
                    w3c_creds_metadata, rev_reg_defs, rev_reg_entries
                )

                assert len(result) == 2
                assert mock_create.call_count == 2
