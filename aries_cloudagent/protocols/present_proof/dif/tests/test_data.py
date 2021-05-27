"""Data for DIFPresExchHandler."""
import json
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from .....storage.vc_holder.vc_record import VCRecord

from ..pres_exch import PresentationDefinition


def create_vcrecord(cred_dict: dict):
    given_id = cred_dict.get("id")
    contexts = [ctx for ctx in cred_dict.get("@context") if type(ctx) is str]

    # issuer
    issuer = cred_dict.get("issuer")
    if type(issuer) is dict:
        issuer = issuer.get("id")

    # subjects
    subjects = cred_dict.get("credentialSubject")
    if type(subjects) is dict:
        subjects = [subjects]
    subject_ids = [subject.get("id") for subject in subjects if subject.get("id")]

    # Schemas
    schemas = cred_dict.get("credentialSchema", [])
    if type(schemas) is dict:
        schemas = [schemas]
    schema_ids = [schema.get("id") for schema in schemas]

    # Proofs (this can be done easier if we use the expanded version)
    proofs = cred_dict.get("proof") or []
    proof_types = None
    if type(proofs) is dict:
        proofs = [proofs]
    if proofs:
        proof_types = [proof.get("type") for proof in proofs]

    # Saving expanded type as a cred_tag
    expanded = jsonld.expand(cred_dict)
    types = JsonLdProcessor.get_values(
        expanded[0],
        "@type",
    )
    return VCRecord(
        contexts=contexts,
        expanded_types=types,
        issuer_id=issuer,
        subject_ids=subject_ids,
        proof_types=proof_types,
        given_id=given_id,
        cred_value=cred_dict,
        schema_ids=schema_ids,
    )


bbs_bls_number_filter_creds = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
                "test": 2,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:23:56.045014",
                "proofPurpose": "assertionMethod",
                "proofValue": "rhD+4HOhPfLywBuhLYMi1i0kWa/L2Qipt+sqTRiebjoo4OF3ESoGnm+L4Movz128Mjns60H0Bz7W+aqN1dPP9uhU/FGBKW/LEIGJX1rrrYgn17CkWp46z/hwQy+8c9ulOCn0Yq3BDqB37euoBTZbOQ==",
            },
        }
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627466",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Theodor",
                "familyName": "Major",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2017-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1968-07-17",
                "test": 2,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:33:05.798834",
                "proofPurpose": "assertionMethod",
                "proofValue": "jp8ahSYYFhRAk+1ahfG8qu7iEjQnEXp3P3fWgTrc4khxmw9/9mGACq67YW9r917/aKYTQcVyojelN3cBHrjBvaOzb7bZ6Ps0Wf6WFq1gc0QFUrdiN0mJRl5YAz8R16sLxrPsoS/8ji1MoabjqmlnWQ==",
            },
        }
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627467",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Cai",
                "familyName": "Leblanc",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-9989",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1975-07-17",
                "test": 3,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:40:44.835154",
                "proofPurpose": "assertionMethod",
                "proofValue": "t8+TPbYqF/dGlEn+qNnEFL1L0QeUjgXlYfJ7AelzOhb7cr2CjP/MIcG5bAQ5l6F2OZKNyE8RsPY14xedrkxpyv1oyWPmXzOwr0gt6ElLJm9jAUwFoZ7xAYHSedcR3Lh4FFuqmxfBHYF3A6VgSlMSfA==",
            },
        }
    ),
]

edd_jsonld_creds = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:47:13.090322",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..HHEpbiQp781YtXdxmYr3xO9a8OtHSePjySbgwGaSqiHGjd9hO0AnhkFxlBlrGukp5rkiJccr4p9KV3uKDzkqDA",
            },
        }
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627466",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Theodor",
                "familyName": "Major",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2017-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1968-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:48:49.702706",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..r88-rSvqp_JLr2fnGr8nKEU--Hu6UhzjXOmdWpt082Wc6ojWpOANvv2wbgKrs5kXF5ATb8-AZ01VPpHdv4m9CQ",
            },
        }
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627467",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Cai",
                "familyName": "Leblanc",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-9989",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1975-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        }
    ),
]

cred_list = [
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "identifier": "83627465",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "JOHN",
            "familyName": "SMITH",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2015-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-999",
            "commuterClassification": "C1",
            "birthCountry": "Bahamas",
            "birthDate": "1958-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:28:37.647315",
            "proofPurpose": "assertionMethod",
            "proofValue": "re8gFWszv8pNA0yAzzR34QGKMUiw+EO/slTqR0L4IJAHWbI4sc5EKCKQamllwAuAAvQ3gVVUbUwrPO5BnyMS+jsenHGTY56uJLFwndZx9X8HZKfKZZAYOdgEl4Ts3GDC3GXidtvR+r+TywI7Qp804Q==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "identifier": "83627466",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Theodor",
            "familyName": "Major",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2017-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-999",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1968-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:12:24.052700",
            "proofPurpose": "assertionMethod",
            "proofValue": "sql6nyas1aGxCLIKwTCO4Ny7758vhcoLSkQ/3/YbNLn4p4yF86dCswkFGn6IhkcrPO4yVhYCkWEaRuk8afaAbLZNoXEPFV/co2l9+dvwLplECaLnoQnl8GCeYfmtHBYW3G9stq/q02nHSejO//3OcQ==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627467",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Cai",
            "familyName": "Leblanc",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2015-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-9989",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1975-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:09:57.710637",
            "proofPurpose": "assertionMethod",
            "proofValue": "hCvSng48xE7k19ShyCbaN+dO82ggwGRVRstr74+zeW1WKtX5xg6n0uS0A+h3QcBwQit6tputniZnUklmgoWPyxwQTaFBTD2nT8EthvKZRhBgxpha1KyZfCIZwvQCZtxfQI7jhen3lzXTeqZRvca80Q==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627468",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:example:489398593",
        "identifier": "83627468",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Jamel",
            "familyName": "Huber",
            "gender": "Female",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2012-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-000",
            "commuterClassification": "C1",
            "birthCountry": "United States",
            "birthDate": "1959-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:35:00.285059",
            "proofPurpose": "assertionMethod",
            "proofValue": "s4kVzMqvC7neR2wsgfgdqxCVejotdsh8Y+0qUfcjPDd3wjU0cVaQExjgz7N8LjQhVZ4iOScUTcLT1u32t4Fpd1H5Xj6h5+OE8TlessDy2hQlsxd0O0vrBn/CmihWagJAWfgYbU1D+eNjj2mbbHWRiQ==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627469",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627469",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Vivek",
            "familyName": "Easton",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2019-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-888",
            "commuterClassification": "C1",
            "birthCountry": "India",
            "birthDate": "1990-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:36:41.396448",
            "proofPurpose": "assertionMethod",
            "proofValue": "iYXNfJTcVP1Z/UC7LSSVN3R1UhKIC2Yjh+X8xLjYvkbeGslPL9JeyXQOI6TpgMS/Tai51ImUouKhtZcuA9l4IOZ4Cslp1UJn5h7nJOMGTXxR7wq9+aPV+Nv9X4aR830Pcy2GiAVOlPWRSc3rE9clKg==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627470",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627470",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Ralphie",
            "familyName": "Jennings",
            "gender": "Female",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2010-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-777",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1980-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2021-05-07T08:38:35.919533",
            "proofPurpose": "assertionMethod",
            "proofValue": "qvnii1PSorn/FEMnhvhDwehtgWdPPU6F8xQ1b4WtdnBYRoCLe3Lqni9An6+zKHGENlCYn8XdU16ah8nDNETDhXYpN9i9TJuMjAl2Xjh3EX9jysLAWCYThObcFtiPGrYubGfboHeKasfq4x+ETzj7vA==",
        },
    },
]

# [Nested_From] Either or case
# Exclusive Disjunction
# -----------------------
# |_x_|_y_|_output_|
# | T | T |   F    |
# | T | F |   T    |
# | F | T |   T    |
# | F | F |   F    |
# -----------------------
pres_exch_nested_srs_a = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "pick",
      "count": 1,
      "from_nested": [
        {
          "name": "United States Citizenship Proofs",
          "purpose": "We need you to prove you are a US citizen.",
          "rule": "all",
          "from": "A"
        },
        {
          "name": "European Union Citizenship Proofs",
          "purpose": "We need you to prove you are a citizen of a EU country.",
          "rule": "all",
          "from": "B"
        }
      ]
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuer.id",
              "$.issuer",
              "$.vc.issuer.id"
            ],
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_2",
      "name":"US Passport",
      "group":[
        "B"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "maximum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_nested_srs_b = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "pick",
      "count": 1,
      "from_nested": [
        {
          "name": "United States Citizenship Proofs",
          "purpose": "We need you to prove you are a US citizen.",
          "rule": "all",
          "from": "A"
        },
        {
          "name": "European Union Citizenship Proofs",
          "purpose": "We need you to prove you are a citizen of a EU country.",
          "rule": "all",
          "from": "B"
        }
      ]
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuer.id",
              "$.issuer",
              "$.vc.issuer.id"
            ],
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593"]
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_2",
      "name":"US Passport",
      "group":[
        "B"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "maximum":"2012-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_nested_srs_c = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "pick",
      "count": 1,
      "from_nested": [
        {
          "name": "United States Citizenship Proofs",
          "purpose": "We need you to prove you are a US citizen.",
          "rule": "all",
          "from": "A"
        },
        {
          "name": "European Union Citizenship Proofs",
          "purpose": "We need you to prove you are a citizen of a EU country.",
          "rule": "all",
          "from": "B"
        }
      ]
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuer.id",
              "$.issuer",
              "$.vc.issuer.id"
            ],
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_2",
      "name":"US Passport",
      "group":[
        "B"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_multiple_srs_not_met = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "pick",
      "count": 2,
      "from": "A"
    },
    {
      "name": "European Union Citizenship Proofs",
      "purpose": "We need you to prove you are a citizen of a EU country.",
      "rule": "all",
      "from": "B"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuer.id",
              "$.vc.issuer.id",
              "$.issuer"
            ],
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_2",
      "name":"US Passport",
      "group":[
        "B"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "exclusiveMinimum":"2009-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_multiple_srs_met = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "all",
      "from": "A"
    },
    {
      "name": "European Union Citizenship Proofs",
      "rule": "all",
      "from": "B"
    },
    {
      "name": "Date Test",
      "rule": "all",
      "from": "C"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
           "path":[
              "$.issuer.id",
              "$.vc.issuer.id",
              "$.issuer"
            ],
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_2",
      "name":"US Passport",
      "group":[
        "B"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.credentialSubject.gender"
            ],
            "filter":{
              "const":"Male"
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_3",
      "name":"US Passport",
      "group":[
        "C"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_datetime_minimum_met = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "European Union Citizenship Proofs",
      "rule": "all",
      "from": "A"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_datetime_maximum_met = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "European Union Citizenship Proofs",
      "rule": "all",
      "from": "A"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate",
              "$.vc.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "maximum":"2014-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""


def get_test_data():
    vc_record_list = []
    for cred in cred_list:
        vc_record_list.append(create_vcrecord(cred))
    pd_json_list = [
        (pres_exch_multiple_srs_not_met, 0),
        (pres_exch_multiple_srs_met, 4),
        (pres_exch_datetime_minimum_met, 6),
        (pres_exch_datetime_maximum_met, 6),
        (pres_exch_nested_srs_a, 4),
        (pres_exch_nested_srs_b, 5),
        (pres_exch_nested_srs_c, 2),
    ]

    pd_list = []
    for pd in pd_json_list:
        pd_list.append(
            (
                PresentationDefinition.deserialize(json.loads(pd[0])),
                pd[1],
            )
        )
    return (vc_record_list, pd_list)
