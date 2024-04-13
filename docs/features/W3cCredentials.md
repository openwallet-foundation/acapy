## Verifiable Credential Data Integrity (VC-DI) Credentials in Aries Cloud Agent Python (ACA-Py)

This document outlines a new functionality within Aries Agent that facilitates the issuance of credentials and presentations in compliance with the W3C standard.

### Table of Contents

- [General Concept](#general-concept)
- [Prerequisites](#prerequisites)
  - [Verifiable Credentials Data Model](#verifiable-credentials-data-model)
  - [Verifiable Presentations Data Model](#verifiable-presentations-data-model)
  - [DIF Presentation Format](#dif-presentation-format)
- [Preparing to Issue a Credential](#preparing-to-issue-a-credential)
  - [VC-DI Context](#vc-di-context)
  - [Signature Suite](#signature-suite)
  - [DID Method](#did-method)
- [Issue a Credential](#issue-a-credential)

### General Concept

The introduction of VC-DI credentials in ACA-Py facilitates the issuance of credentials and presentations in adherence to the W3C standard.

### Prerequisites

Before utilizing this feature, it is essential to have the following:

#### Verifiable Credentials Data Model

A basic understanding of the Verifiable Credentials Data Model is required. Resources for reference include:

- [Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)

#### Verifiable Presentations Data Model

Familiarity with the Verifiable Presentations Data Model is necessary. Relevant resources can be found at:

- [Verifiable Presentations Data Model](https://www.w3.org/TR/vc-data-model/#presentations)

#### DIF Presentation Format

Understanding the DIF Presentation Format is recommended. Access resources at:

- [DIF Presentation Format](https://identity.foundation/presentation-exchange/)

### Preparing to Issue a Credential

To prepare for credential issuance, the following steps must be taken:

#### VC-DI Context

Ensure that every property key in the document is mappable to an IRI. This requires either the property key to be an IRI by default or to have the shorthand property mapped in the `@context` of the document.

```json
{
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/data-integrity/v2",
        {
            "@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"
        }
    ]
}
```

#### Signature Suite

Select a signature suite for use. VC-DI format currently supports EdDSA signature suites for issuing credentials.

- [`Ed25519Signature2020`](https://w3c.github.io/vc-di-eddsa/#ed25519signature2020-0)

#### DID Method

Choose a DID method for issuing the credential. VC-DI format currently supports the `did:key` method.

##### `did:key`

A `did:key` did is not anchored to a ledger, but embeds the key directly in the identifier part of the did. See the [did:key Method Specification](https://w3c-ccg.github.io/did-method-key/) for more information.

You can create a `did:key` using the `/wallet/did/create` endpoint with the following body.

```jsonc
{
  "method": "key",
  "options": {
    "key_type": "ed25519"
  }
}
```

### Issue a Credential

The issuance of W3C credentials is facilitated through the `/issue-credential-2.0/send` endpoint. This process adheres to the formats described in [RFC 0809 VC-DI](https://github.com/hyperledger/aries-rfcs/blob/main/features/0809-w3c-data-integrity-credential-attachment/README.md) and utilizes `didcomm` for communication between agents.