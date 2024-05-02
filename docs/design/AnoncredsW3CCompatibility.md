# Supporting AnonCreds in W3C VC/VP Formats in Aries Cloud Agent Python

This design proposes to extend the Aries Cloud Agent Python (ACA-PY) to support Hyperledger AnonCreds credentials and presentations in the W3C Verifiable Credentials (VC) and Verifiable Presentations (VP) Format. The aim is to transition from the legacy AnonCreds format specified in Aries-Legacy-Method to the W3C VC format.

## Overview

The pre-requisites for the work are:

- The availability of the AnonCreds RS library supporting the generation and processing of AnonCreds VCs in W3C VC format.
- The availability of the AnonCreds RS library supporting the generation and verification of AnonCreds VPs in W3C VP format.
- The availability of support in the AnonCreds RS Python Wrapper for the W3C VC/VP capabilities in AnonCreds RS.
- Agreement on the Aries Issue Credential v2.0 and Present Proof v2.0 protocol attachment formats to use when issuing AnonCreds W3C VC format credentials, and when presenting AnonCreds W3C VP format presentations.
  - For issuing, use the (proposed) [RFC 0809 VC-DI] Attachments
  - For presenting, use the [RFC 0510 DIF Presentation Exchange] Attachments

[RFC 0809 VC-DI]: https://github.com/hyperledger/aries-rfcs/pull/809
[RFC 0510 DIF Presentation Exchange]: https://github.com/hyperledger/aries-rfcs/blob/main/features/0510-dif-pres-exch-attach/README.md

As of 2024-01-15, these pre-requisites have been met.

## Impacts on ACA-Py

### Issuer

Issuer support needs to be added for using the [RFC 0809 VC-DI] attachment format when sending Issue Credential v2.0 protocol`offer` and `issue` messages and when receiving `request` messages.

Related notes:

- The Issue Credential v1.0 protocol will not be updated to support AnonCreds W3C VC format credentials.
- Once an instance of the Issue Credential v2.0 protocol is started using [RFC 0809 VC-DI] format attachments, subsequent messages in the protocol **MUST** use [RFC 0809 VC-DI] attachments.
- The ACA-Py maintainers are discussing the possibility of making pluggable the Issue Credential v2.0 and Present Proof v2.0 attachment formats, to simplify supporting additional formats, including [RFC 0809 VC-DI].

A mechanism must be defined such that an Issuer controller can use the ACA-Py Admin API to initiate the sending of an AnonCreds credential Offer using the [RFC 0809 VC-DI] attachment format.

A credential's encoded attributes are not included in the issued AnonCreds W3C VC format credential. To be determined how that impacts the issuing process.

### Verifier

A verifier wanting a W3C VP Format presentation will send the Present Proof v2.0 `request` message with an [RFC 0510 DIF Presentation Exchange] format attachment.

If needed, the [RFC 0510 DIF Presentation Exchange] document will be clarified and possibly updated to enable its use for handling AnonCreds W3C VP format presentations.

An AnonCreds W3C VP format presentation does not include the encoded revealed attributes, and the encoded values must be calculated as needed. To be determined where those would be needed.

### Holder

A holder must support [RFC 0809 VC-DI] attachments when receiving Issue Credential v2.0 `offer` and `issue` messages, and when sending `request` messages.

On receiving an Issue Credential v2.0 `offer` message with a [RFC 0809 VC-DI], the holder **MUST** respond using the [RFC 0809 VC-DI] on the subsequent `request` message.

On receiving a credential from an issuer in an [RFC 0809 VC-DI] attachment, the holder must process and store the credential for subsequent use in presentations.

- The AnonCreds verifiable credential **MUST** support being used in both legacy AnonCreds and W3C VP format (DIF Presentation Exchange) presentations.

On receiving an [RFC 0510 DIF Presentation Exchange] `request` message, a holder must include AnonCreds verifiable credentials in the search for credentials satisfying the request, and if found and selected for use, must construct the presentation using the [RFC 0510 DIF Presentation Exchange] presentation format, with an embedded AnonCreds W3C VP format presentation.

## Issues to consider

- If and how the W3C VC Format attachments for the Issue Credential V2.0 and Present Proof V2 Aries DIDComm Protocols should be used when using AnonCreds W3C VC Format credentials. Anticipated triggers:
  - An Issuer Controller invokes the Admin API to trigger an Issue Credential v2.0 protocol instance such that the [RFC 0809 VC-DI] will be used.
  - A Holder receives an Issue Credential v2.0 `offer` message with an [RFC 0809 VC-DI] attachment.
  - A Verifier initiates a Present Proof v2.0 protocol instance with an [RFC 0510 DIF Presentation Exchange] that can be satisfied by AnonCreds VCs held by the holder.
  - A Holder receives a present proof `request` message with an [RFC 0510 DIF Presentation Exchange] format attachment that can be satisfied with AnonCreds credentials held by the holder.
    - How are the `restrictions` and `revocation` data elements conveyed?
- How AnonCreds W3C VC Format verifiable credentials are stored by the holder such that they will be discoverable when needed for creating verifiable presentations.
- How and when multiple signatures can/should be added to a W3C VC Format credential, enabling both AnonCreds and non-AnonCreds signatures on a single credential and their use in presentations. Completing a multi-signature controller is out of scope, however we want to consider and ensure the design is fundamentally compatible with multi-sig credentials.

## Flow Chart

![image](https://github.com/Whats-Cookin/aries-cloudagent-python/blob/design/w3c-compatibility/docs/design/anoncreds-w3c-verification-flow.png?raw=true)

## Key Questions

### What is the roadmap for delivery? What will we build first, then second?

It appears that the issue and presentation sides can be approached independently, assuming that any stored AnonCreds VC can be used in an AnonCreds W3C VP format presentation.

#### Issue Credential

1. Update Admin API endpoints to initiate an Issue Credential v2.0 protocol to issue an AnonCreds credential in W3C VC format using [RFC 0809 VC-DI] format attachments.
2. Add support for the [RFC 0809 VC-DI] message attachment formats.
   1. Should the attachment format be made pluggable as part of this? From the maintainers: _If we did make it pluggable, [this](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/messages/cred_format.py#L23) would be the point where that would take place. Since these values are hard coded, it is not pluggable currently, as noted. I've been dissatisfied with how this particular piece works for a while. I think making it pluggable, if done right, could help clean it up nicely. A plugin would then define their own implementation of [V20CredFormatHandler](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/formats/handler.py#L28). (@dbluhm)_
3. Update the v2.0 Issue Credential protocol handler to support a "[RFC 0809 VC-DI] mode" such that when a protocol instance starts with that format, it continues with it until completion, supporting issuing AnonCreds credentials in the process. This includes both the sending and receiving of all protocol message types.

#### Present Proof

1. Adjust as needed the sending of a Present Proof request using the [RFC 0510 DIF Presentation Exchange] with support (to be defined) for requesting AnonCreds VCs.
2. Adjust as needed the processing of a Present Proof `request` message with an [RFC 0510 DIF Presentation Exchange] attachment so that AnonCreds VCs can found and used in the subsequent response.
   1. AnonCreds VCs issued as legacy or W3C VC format credentials should be usable in AnonCreds W3C VP format presentations.
3. Update the creation of an [RFC 0510 DIF Presentation Exchange] presentation submission to support the use of AnonCreds VCs as the source of the VPs.
4. Update the verifier receipt of a Present Proof v2.0 `presentation` message with an [RFC 0510 DIF Presentation Exchange] containing AnonCreds W3C VP(s) derived from AnonCreds source VCs.

### What are the functions we are going to wrap?

After thoroughly reviewing upcoming changes from [anoncreds-rs PR273](https://github.com/hyperledger/anoncreds-rs/pull/273), the classes or `AnoncredsObject` impacted by changes are as follows:

[W3CCredential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R424)

- class methods (`create`, `load`)
- instance methods (`process`, `to_legacy`, `add_non_anoncreds_integrity_proof`, `set_id`, `set_subject_id`, `add_context`, `add_type`)
- class properties (`schema_id`, `cred_def_id`, `rev_reg_id`, `rev_reg_index`)
- bindings functions (`create_w3c_credential`, `process_w3c_credential`, `_object_from_json`, `_object_get_attribute`, `w3c_credential_add_non_anoncreds_integrity_proof`, `w3c_credential_set_id`, `w3c_credential_set_subject_id`, `w3c_credential_add_context`, `w3c_credential_add_type`)

[W3CPresentation](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R791)

- class methods (`create`, `load`)
- instance methods (`verify`)
- bindings functions (`create_w3c_presentation`, `_object_from_json`, `verify_w3c_presentation`)

They will be added to [\_\_init\_\_.py](https://github.com/hyperledger/anoncreds-rs/blob/main/wrappers/python/anoncreds/__init__.py) as additional exports of AnoncredsObject.

We also have to consider which classes or anoncreds objects have been modified

The classes modified according to the same [PR](https://github.com/hyperledger/anoncreds-rs/pull/273) mentioned above are:

[Credential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R402)

- added class methods (`from_w3c`)
- added instance methods (`to_w3c`)
- added bindings functions (`credential_from_w3c`, `credential_to_w3c`)

[PresentCredential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R603)

- modified instance methods (`_get_entry`, `add_attributes`, `add_predicates`)

#### Creating a W3C VC credential from credential definition, and issuing and presenting it as is

The issuance, presentation and verification of legacy anoncreds are implemented in this [./aries_cloudagent/anoncreds](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds) directory. Therefore, we will also start from there.

Let us navigate these implementation examples through the respective processes of the concerning agents - **Issuer** and **Holder** as described in [https://github.com/hyperledger/anoncreds-rs/blob/main/README.md](https://github.com/hyperledger/anoncreds-rs/blob/main/README.md).
We will proceed through the following processes in comparison with the legacy anoncreds implementations while watching out for signature differences between the two.
Looking at the [/anoncreds/issuer.py](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/issuer.py) file, from `AnonCredsIssuer` class:

Create VC_DI Credential Offer

According to this DI credential offer attachment format - [didcomm/w3c-di-vc-offer@v0.1](https://github.com/hyperledger/aries-rfcs/pull/809/files#diff-40b1f86053dd6f0b34250d5be1319d3a0662b96a5a121957fe4dc8cceaa9cbc8R30-R63),

- binding_required
- binding_method
- credential_definition

could be the parameters for `create_offer` method.

Create VC_DI Credential

**NOTE: There has been some changes to _encoding of attribute values_ for creating a credential, so we have to be adjust to the new changes.**

```python
async def create_credential(
        self,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
    ) -> str:
...
...
  try:
    credential = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: W3CCredential.create(
            cred_def.raw_value,
            cred_def_private.raw_value,
            credential_offer,
            credential_request,
            raw_values,
            None,
            None,
            None,
            None,
        ),
    )
...
```

Create VC_DI Credential Request

```python
async def create_vc_di_credential_request(
        self, credential_offer: dict, credential_definition: CredDef, holder_did: str
    ) -> Tuple[str, str]:
...
...
try:
  secret = await self.get_master_secret()
  (
      cred_req,
      cred_req_metadata,
  ) = await asyncio.get_event_loop().run_in_executor(
      None,
      W3CCredentialRequest.create,
      None,
      holder_did,
      credential_definition.to_native(),
      secret,
      AnonCredsHolder.MASTER_SECRET_ID,
      credential_offer,
  )
...
```

Create VC_DI Credential Presentation

```python
async def create_vc_di_presentation(
        self,
        presentation_request: dict,
        requested_credentials: dict,
        schemas: Dict[str, AnonCredsSchema],
        credential_definitions: Dict[str, CredDef],
        rev_states: dict = None,
    ) -> str:
...
...
  try:
    secret = await self.get_master_secret()
    presentation = await asyncio.get_event_loop().run_in_executor(
        None,
        Presentation.create,
        presentation_request,
        present_creds,
        self_attest,
        secret,
        {
            schema_id: schema.to_native()
            for schema_id, schema in schemas.items()
        },
        {
            cred_def_id: cred_def.to_native()
            for cred_def_id, cred_def in credential_definitions.items()
        },
    )
...
```

#### Converting an already issued legacy anoncreds to VC_DI format(vice versa)

In this case, we can use `to_w3c` method of `Credential` class to convert from legacy to w3c and `to_legacy` method of `W3CCredential` class to convert from w3c to legacy.

We could call `to_w3c` method like this:

```python
vc_di_cred = Credential.to_w3c(cred_def)
```

and for `to_legacy`:

```python
legacy_cred = W3CCredential.to_legacy()
```

We don't need to input any parameters to it as it in turn calls `Credential.from_w3c()` method under the hood.

### Format Handler for Issue_credential V2_0 Protocol

Keeping in mind that we are trying to create anoncreds(not another type of VC) in w3c format, what if we add a protocol-level **vc_di** format support by adding a new format `VC_DI` in `./protocols/issue_credential/v2_0/messages/cred_format.py` -

```python
# /protocols/issue_credential/v2_0/messages/cred_format.py

class Format(Enum):
    “””Attachment Format”””
    INDY = FormatSpec(...)
    LD_PROOF = FormatSpec(...)
    VC_DI = FormatSpec(
        “vc_di/”,
        CredExRecordVCDI,
        DeferLoad(
            “aries_cloudagent.protocols.issue_credential.v2_0”
            “.formats.vc_di.handler.AnonCredsW3CFormatHandler”
        ),
    )
```

And create a new CredExRecordVCDI in reference to V20CredExRecordLDProof

```python
# /protocols/issue_credential/v2_0/models/detail/w3c.py

class CredExRecordW3C(BaseRecord):
    """Credential exchange W3C detail record."""

    class Meta:
        """CredExRecordW3C metadata."""

        schema_class = "CredExRecordW3CSchema"

    RECORD_ID_NAME = "cred_ex_w3c_id"
    RECORD_TYPE = "w3c_cred_ex_v20"
    TAG_NAMES = {"~cred_ex_id"} if UNENCRYPTED_TAGS else {"cred_ex_id"}
    RECORD_TOPIC = "issue_credential_v2_0_w3c"

```

Based on the proposed credential attachment format with the new Data Integrity proof in [aries-rfcs 809](https://github.com/hyperledger/aries-rfcs/pull/809/files#diff-40b1f86053dd6f0b34250d5be1319d3a0662b96a5a121957fe4dc8cceaa9cbc8R132-R151) -

```json
{
  "@id": "284d3996-ba85-45d9-964b-9fd5805517b6",
  "@type": "https://didcomm.org/issue-credential/2.0/issue-credential",
  "comment": "<some comment>",
  "formats": [
    {
      "attach_id": "5b38af88-d36f-4f77-bb7a-2f04ab806eb8",
      "format": "didcomm/w3c-di-vc@v0.1"
    }
  ],
  "credentials~attach": [
    {
      "@id": "5b38af88-d36f-4f77-bb7a-2f04ab806eb8",
      "mime-type": "application/ld+json",
      "data": {
        "base64": "ewogICAgICAgICAgIkBjb250ZXogWwogICAgICAg...(clipped)...RNVmR0SXFXZhWXgySkJBIgAgfQogICAgICAgIH0="
      }
    }
  ]
}
```

Assuming `VCDIDetail` and `VCDIOptions` are already in place, `VCDIDetailSchema` can be created like so:

```python
# /protocols/issue_credential/v2_0/formats/vc_di/models/cred_detail.py

class VCDIDetailSchema(BaseModelSchema):
    """VC_DI verifiable credential detail schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = VCDIDetail

    credential = fields.Nested(
        CredentialSchema(),
        required=True,
        metadata={
            "description": "Detail of the VC_DI Credential to be issued",
            "example": {
                "@id": "284d3996-ba85-45d9-964b-9fd5805517b6",
                "@type": "https://didcomm.org/issue-credential/2.0/issue-credential",
                "comment": "<some comment>",
                "formats": [
                    {
                        "attach_id": "5b38af88-d36f-4f77-bb7a-2f04ab806eb8",
                        "format": "didcomm/w3c-di-vc@v0.1"
                    }
                ],
                "credentials~attach": [
                    {
                        "@id": "5b38af88-d36f-4f77-bb7a-2f04ab806eb8",
                        "mime-type": "application/ld+json",
                        "data": {
                            "base64": "ewogICAgICAgICAgIkBjb250ZXogWwogICAgICAg...(clipped)...RNVmR0SXFXZhWXgySkJBIgAgfQogICAgICAgIH0="
                        }
                    }
                ]
            }
        },
    )
```

Then create w3c format handler with mapping like so:

```python
# /protocols/issue_credential/v2_0/formats/w3c/handler.py

mapping = {
            CRED_20_PROPOSAL: VCDIDetailSchema,
            CRED_20_OFFER: VCDIDetailSchema,
            CRED_20_REQUEST: VCDIDetailSchema,
            CRED_20_ISSUE: VerifiableCredentialSchema,
        }
```

Doing so would allow us to be more independent in defining the schema suited for anoncreds in w3c format and once the proposal protocol can handle the w3c format, probably the rest of the flow can be easily implemented by adding `vc_di` flag to the corresponding routes.

### Admin API Attachments

To make sure that once an endpoint has been called to trigger the `Issue Credential` flow in `0809 W3C_DI attachment formats` the subsequent endpoints also follow this format, we can keep track of this [ATTACHMENT_FORMAT](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/message_types.py#L41-L59) dictionary with the proposed `VC_DI` format.

```python
# Format specifications
ATTACHMENT_FORMAT = {
    CRED_20_PROPOSAL: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-filter@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
        V20CredFormat.Format.VC_DI.api: "aries/vc-di-detail@v2.0",
    },
    CRED_20_OFFER: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-abstract@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
        V20CredFormat.Format.VC_DI.api: "aries/vc-di-detail@v2.0",
    },
    CRED_20_REQUEST: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-req@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
        V20CredFormat.Format.VC_DI.api: "aries/vc-di-detail@v2.0",
    },
    CRED_20_ISSUE: {
        V20CredFormat.Format.INDY.api: "hlindy/cred@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc@v1.0",
        V20CredFormat.Format.VC_DI.api: "aries/vc-di@v2.0",
    },
}
```

And this [\_formats_filter](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/routes.py#L442-L461) function takes care of keeping the attachment formats uniform across the iteration of the flow. We can see this function gets called in:

- [\_create_free_offer](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/routes.py#L877) function that gets called in the handler function of `/issue-credential-2.0/send-offer` route (in addition to other offer routes)
- [credential_exchange_send_free_request](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/routes.py#L1229) handler function of `/issue-credential-2.0/send-request` route
- [credential_exchange_create](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/routes.py#L630) handler function of `/issue-credential-2.0/create` route
- [credential_exchange_send](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/issue_credential/v2_0/routes.py#L721) handler function of `/issue-credential-2.0/send` route

The same goes for [ATTACHMENT_FORMAT](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/present_proof/v2_0/message_types.py#L33-L47) of `Present Proof` flow. In this case, DIF Presentation Exchange formats in these [test vectors](https://github.com/TimoGlastra/anoncreds-w3c-test-vectors/tree/main/test-vectors) that are influenced by [RFC 0510 DIF Presentation Exchange](https://github.com/hyperledger/aries-rfcs/blob/main/features/0510-dif-pres-exch-attach/README.md) will be implemented. Here, the [\_formats_attach](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/present_proof/v2_0/routes.py#L403-L422) function is the key for the same purpose above. It gets called in:

- [present_proof_send_proposal](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/present_proof/v2_0/routes.py#L833) handler function of `/present-proof-2.0/send-proposal` route
- [present_proof_create_request](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/present_proof/v2_0/routes.py#L916) handler function of `/present-proof-2.0/create-request` route
- [present_proof_send_free_request](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/protocols/present_proof/v2_0/routes.py#L998) handler function of `/present-proof-2.0/send-request` route

#### Credential Exchange Admin Routes

- /issue-credential-2.0/create-offer

This route indirectly calls `_formats_filters` function to create credential proposal, which is in turn used to create a credential offer in the filter format. The request body for this route might look like this:

```python
{
    "filter": ["vc_di"],
    "comment: <some_comment>,
    "auto-issue": true,
    "auto-remove": true,
    "replacement_id": <replacement_id>,
    "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": {
            ...
            ...
        }
    }
}
```

- /issue-credential-2.0/create

This route indirectly calls `_format_result_with_details` function to generate a cred_ex_record in the specified format, which is then returned. The request body for this route might look like this:

```python
{
    "filter": ["vc_di"],
    "comment: <some_comment>,
    "auto-remove": true,
    "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": {
           ...
           ...
        }
    }
}
```

- /issue-credential-2.0/send

The request body for this route might look like this:

```python
{
    "connection_id": <connection_id>,
    "filter": ["vc_di"],
    "comment: <some_comment>,
    "auto-remove": true,
    "replacement_id": <replacement_id>,
    "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": {
           ...
           ...
        }
    }
}
```

- /issue-credential-2.0/send-offer

The request body for this route might look like this:

```python
{
    "connection_id": <connection_id>,
    "filter": ["vc_di"],
    "comment: <some_comment>,
    "auto-issue": true,
    "auto-remove": true,
    "replacement_id": <replacement_id>,
    "holder_did": <holder_did>,
    "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": {
           ...
           ...
        }
    }
}
```

- /issue-credential-2.0/send-request

The request body for this route might look like this:

```python
{
    "connection_id": <connection_id>,
    "filter": ["vc_di"],
    "comment: <some_comment>,
    "auto-remove": true,
    "replacement_id": <replacement_id>,
    "holder_did": <holder_did>,
    "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": {
           ...
           ...
        }
    }
}
```

#### Presentation Admin Routes

- /present-proof-2.0/send-proposal

The request body for this route might look like this:

```python
{
    ...
    ...
    "connection_id": <connection_id>,
    "presentation_proposal": ["vc_di"],
    "comment: <some_comment>,
    "auto-present": true,
    "auto-remove": true,
    "trace": false
}
```

- /present-proof-2.0/create-request

The request body for this route might look like this:

```python
{
    ...
    ...
    "connection_id": <connection_id>,
    "presentation_proposal": ["vc_di"],
    "comment: <some_comment>,
    "auto-verify": true,
    "auto-remove": true,
    "trace": false
}
```

- /present-proof-2.0/send-request

The request body for this route might look like this:

```python
{
    ...
    ...
    "connection_id": <connection_id>,
    "presentation_proposal": ["vc_di"],
    "comment: <some_comment>,
    "auto-verify": true,
    "auto-remove": true,
    "trace": false
}

```

- /present-proof-2.0/records/{pres_ex_id}/send-presentation

The request body for this route might look like this:

```python
{
    "presentation_definition": <presentation_definition_schema>,
    "auto_remove": true,
    "dif": {
        issuer_id: "<issuer_id>",
        record_ids: {
            "<input descriptor id_1>": ["<record id_1>", "<record id_2>"],
            "<input descriptor id_2>": ["<record id>"],
        }
    },
    "reveal_doc": {
        // vc_di dict
    }

}

```

### How a W3C credential is stored in the wallet

Storing a credential in the wallet is somewhat dependent on the kinds of metadata that are relevant. The metadata mapping between the W3C credential and an AnonCreds credential is not fully clear yet.

One of the questions we need to answer is whether the preferred approach is to modify the existing store credential function so that any credential type is a valid input, or whether there should be a special function just for storing W3C credentials.

We will duplicate this [store_credential](https://github.com/hyperledger/aries-cloudagent-python/blob/8cfe8283ddb2a85e090ea1b8a916df2d78298ec0/aries_cloudagent/anoncreds/holder.py#L167) function and modify it:

```python
async def store_w3c_credential(...) {
    ...
    ...
    try:
        cred = W3CCredential.load(credential_data)
    ...
    ...
}
```

**Question: Would it also be possible to generate the credentials on the fly to eliminate the need for storage?**

**Answer: I don't think it is possible to eliminate the need for storage, and notably the secure storage (encrypted at rest) supported in Askar.**

### How can we handle multiple signatures on a W3C VC Format credential?

Only one of the signature types (CL) is allowed in the AnonCreds format, so if a W3C VC is created by `to_legacy()`, all signature types that can't be turned into a CL signature will be dropped. This would make the conversion lossy. Similarly, an AnonCreds credential carries only the CL signature, limiting output from `to_w3c()` signature types that can be derived from the source CL signature. A possible future enhancement would be to add an extra field to the AnonCreds data structure, in which additional signatures could be stored, even if they are not used. This could eliminate the lossiness, but it adds extra complexity and may not be worth doing.

- Unlike a "typical" non-AnonCreds W3C VC, an AnonCreds VC is _never_ directly presented to a verifier. Rather, a derivation of the credential is generated, and it is the derivation that is shared with the verifier as a presentation. The derivation:
  - Generates presentation-specific signatures to be verified.
  - Selectively reveals attributes.
  - Generates proofs of the requested predicates.
  - Generates a proof of knowledge of the link secret blinded in the verifiable credential.

### Compatibility with AFJ: how can we make sure that we are compatible?

We will write a test for the Aries Agent Test Framework that issues a W3C VC instead of an AnonCreds credential, and then run that test where one of the agents is ACA-PY and the other is based on AFJ -- and vice versa. Also write a test where a W3C VC is presented after an AnonCreds issuance, and run it with the two roles played by the two different agents. This is a simple approach, but if the tests pass, this should eliminate almost all risk of incompatibility.

### Will we introduce new dependencies, and what is risky or easy?

Any significant bugs in the Rust implementation may prevent our wrappers from working, which would also prevent progress (or at least confirmed test results) on the higher-level code.

If AFJ lags behind in delivering equivalent functionality, we may not be able to demonstrate compatibility with the test harness.

### Where should the new issuance code go?

So the [vc](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/vc) directory contains code to verify vc's, is this a logical place to add the code for issuance?

### What do we call the new things? Flexcreds? or just W3C_xxx

Are we defining a concept called Flexcreds that is a credential with a proof array that you can generate more specific or limited credentials from? If so should this be included in the naming?

- I don't think naming comes into play. We are creating and deriving presentations from VC Data Integrity Proofs using an AnonCreds cryptosuite. As such, these are "stock" W3C verifiable credentials.

### How can a wallet retain the capability to present ONLY an anoncred credential?

If the wallet receives a "Flexcred" credential object with an array of proofs, the wallet may wish to present ONLY the more zero-knowledge anoncreds proof

How will wallets support that in a way that is developer-friendly to wallet devs?

- The trigger for wallets to generate a W3C VP Format presentation is that they have receive a [RFC 0510 DIF Presentation Exchange] that can be satisfied with an AnonCreds verifiable credential in their storage. Once we decide to use one or more AnonCreds VCs to satisfy a presentation, we'll derive such a presentation and send it using the [RFC 0510 DIF Presentation Exchange] for the `presentation` message of the Present Proof v2.0 protocol.
