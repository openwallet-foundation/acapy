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
- [Verify a Credential](#verify-a-credential)
- [Present Proof](#present-proof)
  - [Requesting Proof](#requesting-proof)
  - [Presenting Proof](#presenting-proof)
  - [Verifying Proof](#verifying-proof)
- [Appendix](#appendix)
  - [Glossary of Terms](#glossary-of-terms)
  - [References and Resources](#references-and-resources)

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

To issue a W3C credential, follow these steps:

1. **Prepare the Credential Data:**
Ensure the credential data conforms to the VC-DI context.

<details>
<summary>JSON example</summary>

```jsonc
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://w3id.org/security/data-integrity/v2",
    {
      "@vocab": "https://www.w3.org/ns/credentials/issuer-dependent#"
    }
  ],
  "type": ["VerifiableCredential"],
  "issuer": "did:key:z6MkqG......",
  "issuanceDate": "2023-01-01T00:00:00Z",
  "credentialSubject": {
    "id": "did:key:z6Mkh......",
    "name": "John Doe"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "created": "2023-01-01T00:00:00Z",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
    "proofValue": "eyJhbGciOiJFZERTQSJ9..."
  }
}
```
</details>

2. **Select Credential type**
The ability to choose the credential type (indy, vc_di) to be issued. The credential type is used to determine the schema for the credential data.

The format to change credential can be seen in the ["Demo Instruction"](../demo/README.md)

3. **Send the Credential:**
Use the `/issue-credential-2.0/send` endpoint to issue the credential.

<details>
<summary>JSON example</summary>

```jsonc
{
  "auto_issue": true,
  "auto_remove": false,
  "comment": "Issuing a test credential",
  "credential_preview": {
    "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
    "attributes": [
      {"name": "name", "value": "John Doe"}
    ]
  },
  "filter": {
    "format": {
      "cred_def_id": "FMB5MqzuhR..."
    }
  },
  "trace": false
}
```
</details>

4. **Verify the Response:**
The response should confirm the credential issuance.

<details>
<summary>JSON example</summary>

```jsonc
{
  "state": "credential_issued",
  "credential_id": "12345",
  "thread_id": "abcde",
  "role": "issuer"
}
```
</details>

### Verify a Credential

To verify a credential, follow these steps:

1. **Prepare the Verification Request:**
Ensure the request conforms to the verification context.

<details>
<summary>JSON example</summary>

```jsonc
{
  "verifiableCredential": [
    {
      "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/data-integrity/v2"
      ],
      "type": ["VerifiableCredential"],
      "issuer": "did:key:z6MkqG......",
      "issuanceDate": "2023-01-01T00:00:00Z",
      "credentialSubject": {
        "id": "did:key:z6Mkh......",
        "name": "John Doe"
      },
      "proof": {
        "type": "Ed25519Signature2020",
        "created": "2023-01-01T00:00:00Z",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
        "proofValue": "eyJhbGciOiJFZERTQSJ9..."
      }
    }
  ]
}
```
</details>

2. **Send the Verification Request:**
Use the `/present-proof/send-request` endpoint.

<details>
<summary>JSON example</summary>

```jsonc
{
  "presentation": {
    "verifiableCredential": [
      {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://w3id.org/security/data-integrity/v2"
        ],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:z6MkqG......",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
          "id": "did:key:z6Mkh......",
          "name": "John Doe"
        },
        "proof": {
          "type": "Ed25519Signature2020",
          "created": "2023-01-01T00:00:00Z",
          "proofPurpose": "assertionMethod",
          "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
          "proofValue": "eyJhbGciOiJFZERTQSJ9..."
        }
      }
    ]
  }
}
```
</details>

3. **Verify the Response:**
The response should confirm the credential verification.

<details>
<summary>JSON example</summary>

```jsonc
{
  "verified": true,
  "presentation": {
    "type": "VerifiablePresentation",
    "verifiableCredential": [
      {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://w3id.org/security/data-integrity/v2"
        ],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:z6MkqG......",
        "issuanceDate": "2023-01-01T00:00:00Z",
        "credentialSubject": {
          "id": "did:key:z6Mkh......",
          "name": "John Doe"
        },
        "proof": {
          "type": "Ed25519Signature2020",
          "created": "2023-01-01T00:00:00Z",
          "proofPurpose": "assertionMethod",
          "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
          "proofValue": "eyJhbGciOiJFZERTQSJ9..."
        }
      }
    ],
    "proof": {
      "type": "Ed25519Signature2020",
      "created": "2023-01-01T00:00:00Z",
      "proofPurpose": "authentication",
      "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
      "proofValue": "eyJhbGciOiJFZERTQSJ9..."
    }
  }
}
```
</details>

### Present Proof

#### Requesting Proof

To request proof, follow these steps:

1. **Prepare the Proof Request:**
   Ensure the request aligns with the DIF Presentation Format.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "presentation_definition": {
       "id": "example-presentation-definition",
       "input_descriptors": [
         {
           "id": "example-input-descriptor",
           "schema": [
             {
               "uri": "https://www.w3.org/2018/credentials/v1"
             }
           ],
           "constraints": {
             "fields": [
               {
                 "path": ["$.credentialSubject.name"],
                 "filter": {
                   "type": "string",
                   "pattern": "John Doe"
                 }
               }
             ]
           }
         }
       ]
     }
   }
   ```
   </details>

2. **Send the Proof Request:**
   Use the `/present-proof-2.0/send-request` endpoint.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "comment": "Requesting proof of name",
     "presentation_request": {
       "presentation_definition": {
         "id": "example-presentation-definition",
         "input_descriptors": [
           {
             "id": "example-input-descriptor",
             "schema": [
               {
                 "uri": "https://www.w3.org/2018/credentials/v1"
               }
             ],
             "constraints": {
               "fields": [
                 {
                   "path": ["$.credentialSubject.name"],
                   "filter": {
                     "type": "string",
                     "pattern": "John Doe"
                   }
                 }
               ]
             }
           }
         ]
       }
     }
   }
   ```
  </details>

3. **Verify the Response:**
   The response should confirm the proof request.

<details>
<summary>JSON example</summary>

   ```jsonc
   {
     "state": "presentation_received",
     "thread_id": "abcde",
     "role": "verifier"
   }
   ```
   </details>

#### Presenting Proof

To present proof, follow these steps:

1. **Prepare the Presentation Data:**
   Ensure the presentation data conforms to the VC-DI context.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "@context": [
       "https://www.w3.org/2018/credentials/v1",
       "https://w3id.org/security/data-integrity/v2"
     ],
     "type": ["VerifiablePresentation"],
     "verifiableCredential": [
       {
         "@context": [
           "https://www.w3.org/2018/credentials/v1",
           "https://w3id.org/security/data-integrity/v2"
         ],
         "type": ["VerifiableCredential"],
         "issuer": "did:key:z6MkqG......",
         "issuanceDate": "2023-01-01T00:00:00Z",
         "credentialSubject": {
           "id": "did:key:z6Mkh......",
           "name": "John Doe"
         },
         "proof": {
           "type": "Ed25519Signature2020",
           "created": "2023-01-01T00:00:00Z",
           "proofPurpose": "assertionMethod",
           "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
           "proofValue": "eyJhbGciOiJFZERTQSJ9..."
         }
       }
     ]
   }
   ```
   </details>

2. **Send the Presentation:**
   Use the `/present-proof-2.0/send-request` endpoint.

   <details>
   <summary>JSON example</summary>

   ```jsonc
   {
     "presentation": {
       "@context": [
         "https://www.w3.org/2018/credentials/v1",
         "https://w3id.org/security/data-integrity/v2"
       ],
       "type": ["VerifiablePresentation"],
       "verifiableCredential": [
         {
           "@context": [
             "https://www.w3.org/2018/credentials/v1",
             "https://w3id.org/security/data-integrity/v2"
           ],
           "type": ["VerifiableCredential"],
           "issuer": "did:key:z6MkqG......",
           "issuanceDate": "2023-01-01T00:00:00Z",
           "credentialSubject": {
             "id": "did:key:z6Mkh......",
             "name": "John Doe"
           },
           "proof": {
             "type": "Ed25519Signature2020",
             "created": "2023-01-01T00:00:00Z",
             "proofPurpose": "assertionMethod",
             "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
             "proofValue": "eyJhbGciOiJFZERTQSJ9..."
           }
         }
       ]
     },
     "comment": "Presenting proof of name"
   }
   ```
   </details>

3. **Verify the Response:**
   The response should confirm the presentation.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "state": "presentation_sent",
     "thread_id": "abcde",
     "role": "prover"
   }
   ```
   </details>

#### Verifying Proof

To verify presented proof, follow these steps:

1. **Prepare the Verification Data:**
   Ensure the verification data aligns with the VC-DI context.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "@context": [
       "https://www.w3.org/2018/credentials/v1",
       "https://w3id.org/security/data-integrity/v2"
     ],
     "type": ["VerifiablePresentation"],
     "verifiableCredential": [
       {
         "@context": [
           "https://www.w3.org/2018/credentials/v1",
           "https://w3id.org/security/data-integrity/v2"
         ],
         "type": ["VerifiableCredential"],
         "issuer": "did:key:z6MkqG......",
         "issuanceDate": "2023-01-01T00:00:00Z",
         "credentialSubject": {
           "id": "did:key:z6Mkh......",
           "name": "John Doe"
         },
         "proof": {
           "type": "Ed25519Signature2020",
           "created": "2023-01-01T00:00:00Z",
           "proofPurpose": "assertionMethod",
           "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
           "proofValue": "eyJhbGciOiJFZERTQSJ9..."
         }
       }
     ]
   }
   ```
   </details>

2. **Send the Verification Request:**
   Use the `/present-proof-2.0/send-request` endpoint.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "presentation": {
       "@context": [
         "https://www.w3.org/2018/credentials/v1",
         "https://w3id.org/security/data-integrity/v2"
       ],
       "type": ["VerifiablePresentation"],
       "verifiableCredential": [
         {
           "@context": [
             "https://www.w3.org/2018/credentials/v1",
             "https://w3id.org/security/data-integrity/v2"
           ],
           "type": ["VerifiableCredential"],
           "issuer": "did:key:z6MkqG......",
           "issuanceDate": "2023-01-01T00:00:00Z",
           "credentialSubject": {
             "id": "did:key:z6Mkh......",
             "name": "John Doe"
           },
           "proof": {
             "type": "Ed25519Signature2020",
             "created": "2023-01-01T00:00:00Z",
             "proofPurpose": "assertionMethod",
             "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
             "proofValue": "eyJhbGciOiJFZERTQSJ9..."
           }
         }
       ]
     }
   }
   ```
   </details>

3. **Verify the Response:**
   The response should confirm the proof verification.

  <details>
  <summary>JSON example</summary>

   ```jsonc
   {
     "verified": true,
     "presentation": {
       "type": "VerifiablePresentation",
       "verifiableCredential": [
         {
           "@context": [
             "https://www.w3.org/2018/credentials/v1",
             "https://w3id.org/security/data-integrity/v2"
           ],
           "type": ["VerifiableCredential"],
           "issuer": "did:key:z6MkqG......",
           "issuanceDate": "2023-01-01T00:00:00Z",
           "credentialSubject": {
             "id": "did:key:z6Mkh......",
             "name": "John Doe"
           },
           "proof": {
             "type": "Ed25519Signature2020",
             "created": "2023-01-01T00:00:00Z",
             "proofPurpose": "assertionMethod",
             "verificationMethod": "did:key:z6MkqG......#z6MkqG......",
             "proofValue": "eyJhbGciOiJFZERTQSJ9..."
           }
         }
       ]
     }
   }
   ```
   </details>

### Appendix

#### Glossary of Terms

- **VC-DI:** Verifiable Credential Data Integrity
- **W3C:** World Wide Web Consortium
- **DID:** Decentralized Identifier
- **EdDSA:** Edwards-curve Digital Signature Algorithm
- **DIF:** Decentralized Identity Foundation

#### References and Resources

- [Aries Cloud Agent Python Documentation](https://github.com/hyperledger/aries-cloudagent-python)
- [Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)
- [Verifiable Presentations Data Model](https://www.w3.org/TR/vc-data-model/#presentations)
- [DIF Presentation Format](https://identity.foundation/presentation-exchange/)
- [did:key Method Specification](https://w3c-ccg.github.io/did-method-key/)
- ["Aries Cloud Agent Python (ACA-Py) Demos"](https://github.com/sarthakvijayvergiya/aries-cloudagent-python/blob/whatscookin/feat/vc-di-proof/docs/demo/README.md)