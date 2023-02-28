
# How to Issue JSON-LD Credentials using Aca-py

Aca-py has the capability to issue and verify both Indy and JSON-LD (W3C compliant) credentials.

The JSON-LD support is documented [here](../JsonLdCredentials.md) - this document will provide some additional detail in how to use the demo and admin api to issue and prove JSON-LD credentials.


## Setup Agents to Issue JDON-LD Credentials

Clone this repository to a directory on your local:

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python.git
cd aries-cloudagent-python/demo
```

Open up a second shell (so you have 2 shells open in the `demo` directory) and in one shell:

```bash
./run_demo faber --did-exchange --aip 20 --cred-type json-ld
```

... and in the other:

```bash
./run_demo alice
```

Note that you start the `faber` agent with AIP2.0 options.  (When you specify `--cred-type json-ld` faber will set aip to `20` automatically, so the `--aip` option is not strictly required.)

Also note that the above will only work with the `/issue-credential-2.0/create-offer` endpoint.  If you want to use the `/issue-credential-2.0/send` endpoint - which automates each step of the credential exchange - you will need to include the `--no-auto` option when starting each of the alice and faber agents (since the alice and faber controllers *also* automatically respond to each step in the credential exchange).

(Alternately you can run run Alice and Faber agents locally, see the `./faber-local.sh` and `./alice-local.sh` scripts in the `demo` directory.)

Copy the "invitation" json text from the Faber shell and paste into the Alice shell to establish a connection between the two agents.

(If you are running with `--no-auto` you will also need to call the `/connections/{conn_id}/accept-invitation` endpoint in alice's admin api swagger page.)

Now open up two browser windows to the [Faber](http://localhost:8021/api/doc) and [Alice](http://localhost:8031/api/doc) admin api swagger pages.

Using the Faber admin api, you have to create a DID with the appropriate:

- DID method ("key" or "sov")
- key type "ed25519" or "bls12381g2" (corresponding to signature types "Ed25519Signature2018" or "BbsBlsSignature2020")
- if you use DID method "sov" you must use key type "ed25519"

Note that "did:sov" must be a public DID (i.e. registered on the ledger) but "did:key" is not.

For example, in Faber's swagger page call the `/wallet/did/create` endpoint with the following payload:

```
{
  "method": "key",
  "options": {
    "key_type": "bls12381g2" // or ed25519
  }
}
```

This will return something like:

```
{
  "result": {
    "did": "did:key:zUC71KdwBhq1FioWh53VXmyFiGpewNcg8Ld42WrSChpMzzskRWwHZfG9TJ7hPj8wzmKNrek3rW4ZkXNiHAjVchSmTr9aNUQaArK3KSkTySzjEM73FuDV62bjdAHF7EMnZ27poCE",
    "verkey": "mV6482Amu6wJH8NeMqH3QyTjh6JU6N58A8GcirMZG7Wx1uyerzrzerA2EjnhUTmjiSLAp6CkNdpkLJ1NTS73dtcra8WUDDBZ3o455EMrkPyAtzst16RdTMsGe3ctyTxxJav",
    "posture": "wallet_only",
    "key_type": "bls12381g2",
    "method": "key"
  }
}
```

You do *not* create a schema or cred def for a JSON-LD credential (these are only required for "indy" credentials).

You will need to create a DID as above for Alice as well (`/wallet/did/create` etc ...).

Congradulations, you are now ready to start issuing JSON-LD credentials!

- You have two agents with a connection established between the agents - you will need to copy Faber's `connection_id` into the examples below.
- You have created a (non-public) DID for Faber to use to sign/issue the credentials - you will need to copy the DID that you created above into the examples below (as `issuer`).
- You have created a (non-public) DID for Alice to use as her `credentialSubject.id` - this is required for Alice to sign the proof (the `credentialSubject.id` is not required, but then the provided presentation can't be verified).

To issue a credential, use the `/issue-credential-2.0/send-offer` endpoint. (You can also use the `/issue-credential-2.0/send`) endpoint, if, as mentioned above, you have included the `--no-auto` when starting both of the agents.)

You can test with this example payload (just replace the "connection_id", "issuer" key, "credentialSubject.id" and "proofType" with appropriate values:

```
{
  "connection_id": "4fba2ce5-b411-4ecf-aa1b-ec66f3f6c903",
  "filter": {
    "ld_proof": {
      "credential": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": "did:key:zUC71KdwBhq1FioWh53VXmyFiGpewNcg8Ld42WrSChpMzzskRWwHZfG9TJ7hPj8wzmKNrek3rW4ZkXNiHAjVchSmTr9aNUQaArK3KSkTySzjEM73FuDV62bjdAHF7EMnZ27poCE",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
          "givenName": "Sally",
          "familyName": "Student",
          "degree": {
            "type": "BachelorDegree",
            "degreeType": "Undergraduate",
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

Note that if you have the "auto" settings on, this is all you need to do.  Otherwise you need to call the `/send-request`, `/store`, etc endpoints to complete the protocol.

To see the issued credential, call the `/credentials/w3c` endpoint on Alice's admin api - this will return something like:

```
{
  "results": [
    {
      "contexts": [
        "https://w3id.org/security/bbs/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://www.w3.org/2018/credentials/v1"
      ],
      "types": [
        "UniversityDegreeCredential",
        "VerifiableCredential"
      ],
      "schema_ids": [],
      "issuer_id": "did:key:zUC71KdwBhq1FioWh53VXmyFiGpewNcg8Ld42WrSChpMzzskRWwHZfG9TJ7hPj8wzmKNrek3rW4ZkXNiHAjVchSmTr9aNUQaArK3KSkTySzjEM73FuDV62bjdAHF7EMnZ27poCE",
      "subject_ids": [],
      "proof_types": [
        "BbsBlsSignature2020"
      ],
      "cred_value": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://www.w3.org/2018/credentials/examples/v1",
          "https://w3id.org/security/bbs/v1"
        ],
        "type": [
          "VerifiableCredential",
          "UniversityDegreeCredential"
        ],
        "issuer": "did:key:zUC71Kd...poCE",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
          "givenName": "Sally",
          "familyName": "Student",
          "degree": {
            "type": "BachelorDegree",
            "degreeType": "Undergraduate",
            "name": "Bachelor of Science and Arts"
          },
          "college": "Faber College"
        },
        "proof": {
          "type": "BbsBlsSignature2020",
          "proofPurpose": "assertionMethod",
          "verificationMethod": "did:key:zUC71Kd...poCE#zUC71Kd...poCE",
          "created": "2021-05-19T16:19:44.458170",
          "proofValue": "g0weLyw2Q+niQ4pGfiXB...tL9C9ORhy9Q=="
        }
      },
      "cred_tags": {},
      "record_id": "365ab87b12f74b2db784fdd4db8419f5"
    }
  ]
}
```

If you *don't* see the credential in your wallet, look up the credential exchange record (in alice's admin api - `/issue-credential-2.0/records`) and check the state.  If the state is `credential-received`, then the credential has been received but not stored, in this case just call the `/store` endpoint for this credential exchange.


## Building More Realistic JSON-LD Credentials

The above example uses the "https://www.w3.org/2018/credentials/examples/v1" context, which should never be used in a real application.

To build credentials in real life, you first determine which attributes you need and then include the appropriate contexts.


### Context schema.org

You can use attributes defined on [schema.org](https://schema.org).  Although this is *NOT RECOMMENDED* (included here for illustrative purposes only) - individual attributes can't be validated (see the comment later on).

You first include `https://schema.org` in the `@context` block of the credential as follows:

```
"@context": [
  "https://www.w3.org/2018/credentials/v1",
  "https://schema.org"
],
```

Then you review the [attributes and objects defined by `https://schema.org`](https://schema.org/docs/schemas.html) and decide what you need to include in your credential.

For example to issue a credetial with [givenName](https://schema.org/givenName), [familyName](https://schema.org/familyName) and [alumniOf](https://schema.org/alumniOf) attributes, submit the following:

```
{
  "connection_id": "ad35a4d8-c84b-4a4f-a83f-1afbf134b8b9",
  "filter": {
    "ld_proof": {
      "credential": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://schema.org"
        ],
        "type": ["VerifiableCredential", "Person"],
        "issuer": "did:key:zUC71pj2gpDLfcZ9DE1bMtjZGWCSLhkQsUCaKjqXtCftGkz27894pEX9VvGNiFsaV67gqv2TEPQ2aDaDDdTDNp42LfDdK1LaWSBCfzsQEyaiR1zjZm1RtoRu1ZM6v6vz4TiqDgU",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
          "givenName": "Sally",
          "familyName": "Student",
          "alumniOf": "Example University"
        }
      },
      "options": {
        "proofType": "BbsBlsSignature2020"
      }
    }
  }
}
```

Note that with `https://schema.org`, if you include attributes that aren't defined by *any* context, you will *not* get an error.  For example you can try replacing the `credentialSubject` in the above with:

```
"credentialSubject": {
  "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
  "givenName": "Sally",
  "familyName": "Student",
  "alumniOf": "Example University",
  "someUndefinedAttribute": "the value of the attribute"
}
```

... and the credential issuance *should* fail, however `https://schema.org` defines a `@vocab` that by default all terms derive from ([see here](https://stackoverflow.com/questions/30945898/what-is-the-use-of-vocab-in-json-ld-and-what-is-the-difference-to-context/30948037#30948037)).

You can include more complex schemas, for example to use the schema.org [Person](https://schema.org/Person) schema (which includes `givenName` and `familyName`):

```
{
  "connection_id": "ad35a4d8-c84b-4a4f-a83f-1afbf134b8b9",
  "filter": {
    "ld_proof": {
      "credential": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://schema.org"
        ],
        "type": ["VerifiableCredential", "Person"],
        "issuer": "did:key:zUC71pj2gpDLfcZ9DE1bMtjZGWCSLhkQsUCaKjqXtCftGkz27894pEX9VvGNiFsaV67gqv2TEPQ2aDaDDdTDNp42LfDdK1LaWSBCfzsQEyaiR1zjZm1RtoRu1ZM6v6vz4TiqDgU",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
          "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
          "student": {
            "type": "Person",
            "givenName": "Sally",
            "familyName": "Student",
            "alumniOf": "Example University"
          }
        }
      },
      "options": {
        "proofType": "BbsBlsSignature2020"
      }
    }
  }
}
```


## Credential-Specific Contexts

The recommended approach to defining credentials is to define a credential-specific vocaublary (or make use of existing ones).  (Note that these can include references to `https://schema.org`, you just shouldn't uste this directly in your credential.)


### Credential Issue Example

The following example uses the W3C citizenship context to issue a PermanentResident credential (replace the `connection_id`, `issuer` and `credentialSubject.id` with your local values):

```
{
    "connection_id": "41acd909-9f45-4c69-8641-8146e0444a57",
    "filter": {
        "ld_proof": {
            "credential": {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://w3id.org/citizenship/v1"
                ],
                "type": [
                    "VerifiableCredential",
                    "PermanentResident"
                ],
                "id": "https://credential.example.com/residents/1234567890",
                "issuer": "did:key:zUC7Dus47jW5Avcne8LLsUvJSdwspmErgehxMWqZZy8eSSNoHZ4x8wgs77sAmQtCADED5RQP1WWhvt7KFNm6GGMxdSGpKu3PX6R9a61G9VoVsiFoRf1yoK6pzhq9jtFP3e2SmU9",
                "issuanceDate": "2020-01-01T12:00:00Z",
                "credentialSubject": {
                    "type": [
                        "PermanentResident"
                    ],
                    "id": "did:key:zUC7CXi82AXbkv4SvhxDxoufrLwQSAo79qbKiw7omCQ3c4TyciDdb9s3GTCbMvsDruSLZX6HNsjGxAr2SMLCNCCBRN5scukiZ4JV9FDPg5gccdqE9nfCU2zUcdyqRiUVnn9ZH83",
                    "givenName": "ALICE",
                    "familyName": "SMITH",
                    "gender": "Female",
                    "birthCountry": "Bahamas",
                    "birthDate": "1958-07-17"
                }
            },
            "options": {
                "proofType": "BbsBlsSignature2020"
            }
        }
    }
}
```

Copy and paste this content into Faber's `/issue-credential-2.0/send-offer` endpoint, and it will kick off the exchange process to issue a W3C credential to Alice.

In Alice's swagger page, submit the `/credentials/records/w3c` endpoint to see the issued credential.


### Request Presentation Example

To request a proof, submit the following (with appropriate `connection_id`) to Faber's `/present-proof-2.0/send-request` endpoint:

```
{
    "comment": "string",
    "connection_id": "41acd909-9f45-4c69-8641-8146e0444a57",
    "presentation_request": {
        "dif": {
            "options": {
                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "domain": "4jt78h47fh47"
            },
            "presentation_definition": {
                "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
                "format": {
                    "ldp_vp": {
                        "proof_type": [
                            "BbsBlsSignature2020"
                        ]
                    }
                },
                "input_descriptors": [
                    {
                        "id": "citizenship_input_1",
                        "name": "EU Driver's License",
                        "schema": [
                            {
                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                            },
                            {
                                "uri": "https://w3id.org/citizenship#PermanentResident"
                            }
                        ],
                        "constraints": {
                            "limit_disclosure": "required",
                            "is_holder": [
                                {
                                    "directive": "required",
                                    "field_id": [
                                        "1f44d55f-f161-4938-a659-f8026467f126"
                                    ]
                                }
                            ],
                            "fields": [
                                {
                                    "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                    "path": [
                                        "$.credentialSubject.familyName"
                                    ],
                                    "purpose": "The claim must be from one of the specified issuers",
                                    "filter": {
                                        "const": "SMITH"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.givenName"
                                    ],
                                    "purpose": "The claim must be from one of the specified issuers"
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
}
```

Note that the `is_holder` property can be used by Faber to verify that the holder of credential is the same as the subject of the attribute (`familyName`). Later on, the received presentation will be signed and verifiable only if `is_holder` with ` "directive": "required"` is included in the presentation request.

There are several ways that Alice can respond with a presentation.  The simplest will just tell aca-py to put the presentation together and send it to Faber - submit the following to Alice's `/present-proof-2.0/records/{pres_ex_id}/send-presentation`:

```
{
  "dif": {
  }
}
```

There are two ways that Alice can provide some constraints to tell aca-py which credential(s) to include in the presentation.

Firstly, Alice can include the received presentation request in the body to the `/send-presentation` endpoint, and can include additional constraints on the fields:

```
{
  "dif": {
    "issuer_id": "did:key:zUC7Dus47jW5Avcne8LLsUvJSdwspmErgehxMWqZZy8eSSNoHZ4x8wgs77sAmQtCADED5RQP1WWhvt7KFNm6GGMxdSGpKu3PX6R9a61G9VoVsiFoRf1yoK6pzhq9jtFP3e2SmU9",
    "presentation_definition": {
      "format": {
        "ldp_vp": {
          "proof_type": [
            "BbsBlsSignature2020"
          ]
        }
      },
      "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
      "input_descriptors": [
        {
          "id": "citizenship_input_1",
          "name": "Some kind of citizenship check",
          "schema": [
            {
              "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
            },
            {
              "uri": "https://w3id.org/citizenship#PermanentResident"
            }
          ],
          "constraints": {
            "limit_disclosure": "required",
            "is_holder": [
                {
                    "directive": "required",
                    "field_id": [
                        "1f44d55f-f161-4938-a659-f8026467f126",
                        "332be361-823a-4863-b18b-c3b930c5623e"
                    ],
                }
            ],
            "fields": [
              {
                "id": "1f44d55f-f161-4938-a659-f8026467f126",
                "path": [
                  "$.credentialSubject.familyName"
                ],
                "purpose": "The claim must be from one of the specified issuers",
                "filter": {
                  "const": "SMITH"
                }
              },
              {
                  "id": "332be361-823a-4863-b18b-c3b930c5623e",
                  "path": [
                      "$.id"
                  ],
                  "purpose": "Specify the id of the credential to present",
                  "filter": {
                      "const": "https://credential.example.com/residents/1234567890"
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

Note the additional constraint on `"path": [ "$.id" ]` - this restricts the presented credential to the one with the matching `credential.id`.  Any credential attributes can be used, however this presumes that the issued credentials contain a uniquely identifying attribute.

Another option is for Alice to specify the credential `record_id` - this is an internal value within aca-py:

```
{
  "dif": {
    "issuer_id": "did:key:zUC7Dus47jW5Avcne8LLsUvJSdwspmErgehxMWqZZy8eSSNoHZ4x8wgs77sAmQtCADED5RQP1WWhvt7KFNm6GGMxdSGpKu3PX6R9a61G9VoVsiFoRf1yoK6pzhq9jtFP3e2SmU9",
    "presentation_definition": {
      "format": {
        "ldp_vp": {
          "proof_type": [
            "BbsBlsSignature2020"
          ]
        }
      },
      "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
      "input_descriptors": [
        {
          "id": "citizenship_input_1",
          "name": "Some kind of citizenship check",
          "schema": [
            {
              "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
            },
            {
              "uri": "https://w3id.org/citizenship#PermanentResident"
            }
          ],
          "constraints": {
            "limit_disclosure": "required",
            "fields": [
              {
                "path": [
                  "$.credentialSubject.familyName"
                ],
                "purpose": "The claim must be from one of the specified issuers",
                "filter": {
                  "const": "SMITH"
                }
              }
            ]
          }
        }
      ]
    },
    "record_ids": {
      "citizenship_input_1": [ "1496316f972e40cf9b46b35971182337" ]
    }
  }
}
```

### Another Credential Issue Example

TBD the following credential is based on the W3C Vaccination schema:

```
{
  "connection_id": "ad35a4d8-c84b-4a4f-a83f-1afbf134b8b9",
  "filter": {
    "ld_proof": {
      "credential": {
        "@context": [
          "https://www.w3.org/2018/credentials/v1",
          "https://w3id.org/vaccination/v1"
        ],
        "type": ["VerifiableCredential", "VaccinationCertificate"],
        "issuer": "did:key:zUC71pj2gpDLfcZ9DE1bMtjZGWCSLhkQsUCaKjqXtCftGkz27894pEX9VvGNiFsaV67gqv2TEPQ2aDaDDdTDNp42LfDdK1LaWSBCfzsQEyaiR1zjZm1RtoRu1ZM6v6vz4TiqDgU",
        "issuanceDate": "2020-01-01T12:00:00Z",
        "credentialSubject": {
            "id": "did:key:aksdkajshdkajhsdkjahsdkjahsdj",
            "type": "VaccinationEvent",
            "batchNumber": "1183738569",
            "administeringCentre": "MoH",
            "healthProfessional": "MoH",
            "countryOfVaccination": "NZ",
            "recipient": {
              "type": "VaccineRecipient",
              "givenName": "JOHN",
              "familyName": "SMITH",
              "gender": "Male",
              "birthDate": "1958-07-17"
            },
            "vaccine": {
              "type": "Vaccine",
              "disease": "COVID-19",
              "atcCode": "J07BX03",
              "medicinalProductName": "COVID-19 Vaccine Moderna",
              "marketingAuthorizationHolder": "Moderna Biotech"
            }
        }
      },
      "options": {
        "proofType": "BbsBlsSignature2020"
      }
    }
  }
}
```

