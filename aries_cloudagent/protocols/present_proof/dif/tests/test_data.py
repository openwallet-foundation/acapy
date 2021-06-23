"""Data for DIFPresExchHandler."""
import json
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from .....storage.vc_holder.vc_record import VCRecord

from ..pres_exch import PresentationDefinition


def create_vcrecord(cred_dict: dict, expanded_types: list):
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

    return VCRecord(
        contexts=contexts,
        expanded_types=expanded_types,
        issuer_id=issuer,
        subject_ids=subject_ids,
        proof_types=proof_types,
        given_id=given_id,
        cred_value=cred_dict,
        schema_ids=schema_ids,
    )


creds_with_no_id = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "type": ["PermanentResident", "Person"],
                "givenName": "TEST",
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "mMEjznbr4lN5xQT0OuLJ94pKSSBEwBxKNHBPxfjwhRq2NnDaTH/mb+PdPnmfUgKvA8h5hI9Ho3qfY8TWmJtLsYSmJFZoG/FARQuwJJbTW/tVZoA2FVVKZGEsGt2MHsr1z/W30cXnmRyQzgqh4lnhQg==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "type": ["PermanentResident", "Person"],
                "givenName": "TEST",
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "rf5LlOFiB5oAl/hSEeaN/H3vx+3AXVpL4O4abtLmYb1aUF+WBOX3HBx5SrTkcwUgJBAPNoFX9l2PVDjTGy/eCjDerDG0DN5ZR+YwjebcZeclzE3Yv2hsnan1M/OTAc9GTNWE3p9lXbRxHNvwTXX6ug==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
]

bbs_signed_cred_no_credsubjectid = [
    create_vcrecord(
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
            "issuanceDate": "2019-12-03T12:19:52Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "hG9cNGyjjAgPkDmtNv/+28ciBZFUVcAG2gfvLBlTWeFyYJu6DARo16RwQAoSnrgVRQn3n7KCSdnSrPb3op1+vSTu2vo+LF3GfSfqlei44bwA+c2FBIRk7S3FKY6Lm5mqOtC2Q4LStC9HtaOj8vQhgA==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "credentialSubject": {
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
                "familyName": "SMITH",
                "gender": "Female",
                "givenName": "ALICE",
                "type": ["PermanentResident", "Person"],
            },
            "issuanceDate": "2020-01-01T12:00:00Z",
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "haUMgpZE4hPiIEvzdEWyGsvXh1enQvhsOq2cMf3q80u29ybRDi74zU0O+fug1bWiMxeFOboxsfuEKXGC4Ldw0sCsIs+90Jn4EuTqhY4ml8YWsKY9Kjpxvtpc0e24SOl++oo48EICfUxb24HYlQ35pw==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                    "degreeType": "Underwater Basket Weaving",
                },
                "college": "Contoso University",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "iRArJRSvmIwx5YH2HXg5OJD+0v5sD1HoqhBsiJiw59t3Eb6nSntyOnENEnqnpzQwCjtbvOsU18eBlVi2/ign1u1ysz0iOLxSRHvIKtDDpr1dTDwQCbuZo2gUnY+8Dy+xEst8MDtcXwzNQW8Y3l1XzA==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://example.org/examples#UniversityDegreeCredential",
        ],
    ),
]

bbs_signed_cred_credsubjectid = [
    create_vcrecord(
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
            "issuanceDate": "2019-12-03T12:19:52Z",
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "s++A89p+SvIHvY9pnIKIPsLjrLGGk2cs+LfpTWCsE0S1Y5Rg1h9OA5c84Vzqlc3kGfM3zdYpHrO9v0/vBFLQ3HV9wH7xgmD9MPVN+klsaQJdobRpJMjlBni7/QA2/+0szT2P1FJ537lGjyuRboVWng==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                    "degreeType": "Underwater Basket Weaving",
                },
                "college": "Contoso University",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "iGAQ4bOxuqkoCbX3RoxTqFkJsoqPcEeRN2vqIzd/zWLS+VHCwYkQHu/TeMOrit4eb6eugbJFUBaoenZyy2VU/7Rsj614sNzumJFuJ6ZaDTlv0k70CkO9GheQTc+Gwv749Y3JzPJ0dwYGUzzcyytFCQ==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://example.org/examples#UniversityDegreeCredential",
        ],
    ),
]

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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
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
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
]

CRED_LIST = [
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "ssut7SPH6KiY44z5w9N/dD+L8KxS7pXF5irVyty0IlafX7hn5AZNd1rb7fhzVz6wZo9nK/nu/bYs9zhuJggTbuQNPWyOWiFmd3uSxr+CrTYUZ/u31s7gaqEYv4pUBoKgMx6WKkOApELtOI4e0PFddA==",
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "tnRgimJXy8mP7Amk8dPiJnJc+WhAFiYPF8hpRlqOPsSom4cF1VAxaiAN2o3io1kYajUtmXAJLxNNLOZkXDBblcqZAu5mHKEPWc/nctu3vNs4gs5f7tWZX7lm6JK71pLJq8lWbyIufIm/BnCjeIll5g==",
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "l1sdjvIhlkAPb+Y1vUYgIVH9YhiWSFjJFOL1ntzN9jXvOqv7/RMFhoAxg0BTYU1ITHK5l/6Q5lwmtkKxJMt/Z+QPZ8yWDIwqX8kVXFxKo9st8T45ChYiizc75E+Rd7Z5qIidmuulyPvpHlpgHYLZsQ==",
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "rtG10rBsv8zXHBGWqHTeGyH9Y3oMa6xHjBvsJ5YHeocUBxOCge2WEs1tr60hjI4SEpi3JHSJOfd1wJEvfvMg/x6YnTZoA2UXiHBu/6vANx43EfTgbq4YDrrf1aTtQgpZDp/J4GaKoeUshuPXyf8LyA==",
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "pvo7gqDgu9mMjcZafvS8gRz0mIRfFnRCNmp39cZ/92R3UDG5bmxPhh4nG2k1kjaza8wFfaqjaBxsonV+FkQUMzUWbZkn2vstEcGCJllDHFBQiDcf8MVCiCcbGBLpU9MXjnyzhwA5AteG9a2YcvRh/w==",
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
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "pVuvbBfGnVbwwht1s4qZSCoLlZ8nwqvsmNKR+1VTesA+7tXPriJCdlnNFDL0Gkh5TV5E0NOS8WNttE5Uhhqakmjcs7L4hIr4PoVtCLFAF1tce8n4Z/5PKD7IuGIdCDbn77fjQffu2Cs+JDBVVcQRBA==",
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
    for cred in CRED_LIST:
        vc_record_list.append(
            create_vcrecord(
                cred,
                [
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://w3id.org/citizenship#PermanentResidentCard",
                ],
            )
        )
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
