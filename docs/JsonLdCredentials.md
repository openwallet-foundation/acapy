# JSON-LD Credentials in ACA-Py <!-- omit in toc -->

By design Hyperledger Aries is credential format agnostic. This means you can use it for any credential format, as long as an RFC is defined for the specific credential format. ACA-Py currently supports two types of credentials, Indy and JSON-LD credentials. This document describes how to use the latter by making use of [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/) using [Linked Data Proofs](https://w3c-ccg.github.io/ld-proofs).

## Table of Contents <!-- omit in toc -->

- [General Concept](#general-concept)
  - [BBS+](#bbs)
- [Preparing to Issue a Credential](#preparing-to-issue-a-credential)
  - [JSON-LD Context](#json-ld-context)
    - [Writing JSON-LD Contexts](#writing-json-ld-contexts)
  - [Signature Suite](#signature-suite)
  - [Did Method](#did-method)
    - [`did:sov`](#didsov)
    - [`did:key`](#didkey)
- [Issuing Credentials](#issuing-credentials)
- [Retrieving Issued Credentials](#retrieving-issued-credentials)
- [Present Proof](#present-proof)

## General Concept

The rest of this guide assumes some basic understanding of W3C Verifiable Credentials, JSON-LD and Linked Data Proofs. If you're not familiar with some of these concepts, the following resources can help you get started:

- [Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)
- [JSON-LD Articles and Presentations](https://json-ld.org/learn.html)
- [Linked Data Proofs](https://w3c-ccg.github.io/ld-proofs)

### BBS+

BBS+ credentials offer a lot of privacy preserving features over non-ZKP credentials. Therefore we recommend to always use BBS+ credentials over non-ZKP credentials. To get started with BBS+ credentials it is recommended to at least read [RFC 0646: W3C Credential Exchange using BBS+ Signatures](https://github.com/hyperledger/aries-rfcs/blob/master/features/0646-bbs-credentials/README.md) for a general overview.

Some other resources that can help you get started with BBS+ credentials:

- [BBS+ Signatures 2020](https://w3c-ccg.github.io/ldp-bbs2020)
- [Video: BBS+ Credential Exchange in Hyperledger Aries](https://www.youtube.com/watch?v=LC0OXAir3Qw)

## Preparing to Issue a Credential

Contrary to Indy credentials, JSON-LD credentials do not need a schema or credential definition to issue credentials. Everything required to issue the credential is embedded into the credential itself using Linked Data Contexts.

### JSON-LD Context

It is required that every property key in the document can be mapped to an IRI. This means the property key must either be an IRI by default, or have the shorthand property mapped in the `@context` of the document. If you have properties that are not mapped to IRIs, the Issue Credential API will throw the following error:

> "\<x> attributes dropped. Provide definitions in context to correct. [\<missing-properties>]"

For credentials the `https://www.w3.org/2018/credentials/v1` context MUST always be the first context. In addition, when issuing BBS+ credentials the `https://w3id.org/security/bbs/v1` URL MUST be present in the context. For convenience this URL will be automatically added to the `@context` of the credential if not present.

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://other-contexts.com"
  ]
}
```

#### Writing JSON-LD Contexts

Writing JSON-LD contexts can be a daunting task and is out of scope of this guide. Generally you should try to make use of already existing vocabularies. Some examples are the vocabularies defined in the W3C Credentials Community Group:

- [Vaccination Certificate Vocabulary](https://w3c-ccg.github.io/vaccination-vocab/)
- [Citizenship Vocabulary](https://w3c-ccg.github.io/citizenship-vocab/)
- [Traceability Vocabulary](https://w3c-ccg.github.io/traceability-vocab/)

Verifiable credentials are not around that long, so there aren't that many vocabularies ready to use. If you can't use one of the existing vocabularies it is still beneficial to lean on already defined lower level contexts. http://schema.org has a large registry of definitions that can be used to build new contexts. The example vocabularies linked above all make use of types from http://schema.org

For the remainder of this guide, we will be using the example `UniversityDegreeCredential` type and `https://www.w3.org/2018/credentials/examples/v1` context from the Verifiable Credential Data Model. You should not use this for production use cases.

### Signature Suite

Before issuing a credential you must determine a signature suite to use. ACA-Py currently supports two signature suites for issuing credentials:

- [`Ed25519Signature2018`](https://w3c-ccg.github.io/lds-ed25519-2018/) - Very well supported. No zero knowledge proofs or selective disclosure.
- [`BbsBlsSignature2020`](https://w3c-ccg.github.io/ldp-bbs2020/) - Newer, but supports zero knowledge proofs and selective disclosure.

Generally you should always use `BbsBlsSignature2020` as it allows the holder to derive a new credential during the proving, meaning it doesn't have to disclose all fields and doesn't have to reveal the signature.

### Did Method

Besides the JSON-LD context, we need a did to use for issuing the credential. ACA-Py currently supports two did methods for issuing credentials:

- `did:sov` - Can only be used for `Ed25519Signature2018` signature suite.
- `did:key` - Can be used for both `Ed25519Signature2018` and `BbsBlsSignature2020` signature suites.

#### `did:sov`

When using `did:sov` you need to make sure to use a public did so other agents can resolve the did. It is also important the other agent is using the same indy ledger for resolving the did. You can get the public did using the `/wallet/did/public` endpoint. For backwards compatibility the did is returned without `did:sov` prefix. When using the did for issuance make sure this prepend this to the did. (so `DViYrCMPWfuLiY7LLs8giB` becomes `did:sov:DViYrCMPWfuLiY7LLs8giB`)

#### `did:key`

A `did:key` did is not anchored to a ledger, but embeds the key directly in the identifier part of the did. See the [did:key Method Specification](https://w3c-ccg.github.io/did-method-key/) for more information.

You can create a `did:key` using the `/wallet/did/create` endpoint with the following body. Use `ed25519` for `Ed25519Signature2018`, `bls12381g2` for `BbsBlsSignature2020`.

```jsonc
{
  "method": "key",
  "options": {
    "key_type": "bls12381g2" // or ed25519
  }
}
```

The above call will return a did that looks something like this: `did:key:zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj`

## Issuing Credentials

> Issuing JSON-LD credentials is only possible with the issue credential v2 protocol (`/issue-credential-2.0`)

The format used for exchanging JSON-LD credentials is defined in [RFC 0593: JSON-LD Credential Attachment format](https://github.com/hyperledger/aries-rfcs/tree/master/features/0593-json-ld-cred-attach/README.md). The API in ACA-Py exactly matches the formats as described in this RFC, with the most important (from the ACA-Py API perspective) being [`aries/ld-proof-vc-detail@v1.0`](https://github.com/hyperledger/aries-rfcs/blob/master/features/0593-json-ld-cred-attach/README.md#ld-proof-vc-detail-attachment-format). Read the RFC to see the exact properties required to construct a valid Linked Data Proof VC Detail.

All endpoints in API use the `aries/ld-proof-vc-detail@v1.0`. We'll use the `/issue-credential-2.0/send` as an example, but it works the same for the other endpoints. In contrary to issuing indy credentials, JSON-LD credentials do not require a credential preview. All properties should be directly embedded in the credentials.

The detail should be included under the `filter.ld_proof` property. To issue a credential call the `/issue-credential-2.0/send` endpoint, with the example body below and the `connection_id` and `issuer` keys replaced. The value of `issuer` should be the did that you created in the [Did Method](#did-method) paragraph above.

If you don't have `auto-respond-credential-offer` and `auto-store-credential` enabled in the ACA-Py config, you will need to call `/issue-credential-2.0/records/{cred_ex_id}/send-request` and `/issue-credential-2.0/records/{cred_ex_id}/store` to finalize the credential issuance.

<details>
<summary>See the example body</summary>

```jsonc
{
  "connection_id": "ddc23de9-359f-465c-b66e-f7c5a0cc9a57",
  "filter": {
    "ld_proof": {
      "credential": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": "did:key:zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "degree": {
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts"
          },
          "college": "Faber College"
        }
      },
      "options": {
        "proofType": "BbsBlsSignature2020"
      }
    }
  }
}
```

</details>

## Retrieving Issued Credentials

After issuing the credential, the credentials should be stored inside the wallet. Because the structure of JSON-LD credentials is so different from indy credentials a new endpoint is added to retrieve W3C credentials.

Call the `/credentials/w3c` endpoint to retrieve all JSON-LD credentials in your wallet. See the detail below for an example response based on the issued credential from the [Issuing Credentials](#issuing-credentials) paragraph above.

<details>

<summary>See the example response</summary>

```json
{
  "results": [
    {
      "contexts": [
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1"
      ],
      "types": ["UniversityDegreeCredential", "VerifiableCredential"],
      "schema_ids": [],
      "issuer_id": "did:key:zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj",
      "subject_ids": [],
      "proof_types": ["BbsBlsSignature2020"],
      "cred_value": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://www.w3.org/2018/credentials/examples/v1",
          "https://w3id.org/security/bbs/v1"
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": "did:key:zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "degree": {
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts"
          },
          "college": "Faber College"
        },
        "proof": {
          "type": "BbsBlsSignature2020",
          "proofPurpose": "assertionMethod",
          "verificationMethod": "did:key:zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj#zUC7FsmhhifDTuYXdwYES2UpCpWwYieJRapC6oEWqyt5KfJ3ztfLzYnbWjuXQ5drYaKaho3FjxrfDB81gtAJKjbM4yAmBuNoj3YKDXqW151KkkYarpEoEVWMMcN5zPfjCrQ8Saj",
          "created": "2021-05-03T12:31:28.561945",
          "proofValue": "iUFtRGdLLCWxKx8VD3oiFBoRMUFKhSitTzMsfImXm6OF0d8il+Z40aLz8S7m8EcXPQhRjcWWL9jkfcf1SDifD4CvxVg69NvB7hZyIIz9hwAyi3LmTm0ez4NDRCKyieBuzqKbfM2eACWn/ilhOJBm6w=="
        }
      },
      "cred_tags": {},
      "record_id": "541ddbce5760497d98e68917be8c05bd"
    }
  ]
}
```

</details>

## Present Proof

> ⚠️ TODO: https://github.com/hyperledger/aries-cloudagent-python/pull/1125
