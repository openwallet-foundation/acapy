# Anoncreds W3C Compatibility

This design proposes to extend the Aries Cloud Agent Python (ACA-PY) to support Hyperledger AnonCreds credentials and presentations in the W3C Verifiable Credentials (VC) and Verifiable Presentations (VP) Format. The aim is to transition from the legacy AnonCreds format specified in Aries-Legacy-Method to the W3C VC format.
<br><br>

## Overview

We aim to wrap the enhancements made on the Rust Framework for Anoncreds first. Then we will work on the integration of AnonCreds with W3C VC Format in ACA-PY, which includes support for issuing, verifying, and managing W3C VC Format AnonCreds credentials.

Ideally the signatures will be delivered in parallel with the Javascript Framework Document. The [test-vectors](https://github.com/TimoGlastra/anoncreds-w3c-test-vectors/) repo may be used as a guide for interoperability.
<br><br>

## Caveats

As we are relying on the Rust framework, the version of the VC datamodel supported will depend on which is supported by that framework. This will include [VCDM (Verifiable Credential Data Model) 1.1](https://www.w3.org/TR/vc-data-model/) and may extend to [(Verifiable Credential Data Model) 2.0](https://www.w3.org/TR/vc-data-model-2.0/). Further the features supported will be those provided by the underlying framework, as follows:

- Credentials: Verify validity of non-Creds Data Integrity proof signatures
- Presentations: Create presentations using non-AnonCreds Data Integrity proof signature
- Presentations: Verify validity of presentations, including non-AnonCreds Data Integrity proof signatures
- Presentations: Support different formats (for example, DIF) of Presentation Request

A flag may be provided to request the Verifiable Credentials be produced in 1.1 or 2.0 compatible formats. The implementation SHOULD be as consistent as possible with a single function signature.
<br><br>

## Issues to consider

- If and how the W3C VC Format attachments for the Issue Credential V2.0 and Present Proof V2 Aries DIDComm Protocols should be used when using AnonCreds W3C VC Format credentials.
- How AnonCreds W3C VC Format verifiable credentials are stored by the holder such that they will be discoverable when needed for creating verifiable presentations.
- How and when multiple signatures can/should be added to a W3C VC Format credential, enabling both AnonCreds and non-AnonCreds signatures on a single credential and their use in presentations.
  <br><br>

## Flow Chart

![image](./anoncreds-w3c-verification-flow.png)

## Key Questions

### What is the roadmap for delivery? What will we build first, then second?

1. Adapt to new Python wrapper function signatures
2. W3C VC conversion (`to_w3c()`) in ACA-PY.
3. W3C VC issuance in ACA-PY.
4. W3C VC storage in holder's wallet in ACA-PY.
5. W3C VC presentation from an AnonCreds cred in ACA-PY.
6. Convert W3C VCs back to AnonCreds (`to_legacy()`) in ACA-PY.

### What are the functions we are going to wrap?

After thoroughly reviewing upcoming changes from [anoncreds-rs PR273](https://github.com/hyperledger/anoncreds-rs/pull/273), the classes or `AnoncredsObject` that we deemed necessary to be exported are:<br>

[W3CCredentialOffer](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R106)<br>
class methods (`create`, `load`)<br>
bindings functions (`create_w3c_credential_offer`)<br>

[W3CCredential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R424)<br>
class methods (`create`, `load`)<br>
instance methods (`proceess`, `to_legacy`, `add_non_anoncreds_integrity_proof`, `set_id`, `set_subject_id`, `add_context`, `add_type`)<br>
class properties (`schema_id`, `cred_def_id`, `rev_reg_id`, `rev_reg_index`)<br>
bindings functions (`create_w3c_credential`, `process_w3c_credential`, `_object_from_json`, `_object_get_attribute`, `w3c_credential_add_non_anoncreds_integrity_proof`, `w3c_credential_set_id`, `w3c_credential_set_subject_id`, `w3c_credential_add_context`, `w3c_credential_add_type`)<br>

[W3CPresentation](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R791)<br>
class methods (`create`, `load`)<br>
instance methods (`verify`)<br>
bindings functions (`create_w3c_presentation`, `_object_from_json`, `verify_w3c_presentation`)<br>

They will be added to [\_\_init\_\_.py](https://github.com/hyperledger/anoncreds-rs/blob/main/wrappers/python/anoncreds/__init__.py) as additional exports of AnoncredsObject. <br><br>

We also have to consider which classes or anoncreds objects have been modified

The classes modified according to the same [PR](https://github.com/hyperledger/anoncreds-rs/pull/273) mentioned above are:<br>

[Credential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R402)<br>
added class methods (`from_w3c`)<br>
added instance methods (`to_w3c`)<br>
added bindings functions (`credential_from_w3c`, `credential_to_w3c`)<br>

[PresentCredential](https://github.com/hyperledger/anoncreds-rs/pull/273/files#diff-6f8cbd34bbd373240b6af81f159177023c05b074b63c7757fc6b3796a66ee240R603)<br>
modified instance methods (`_get_entry`, `add_attributes`, `add_predicates`)<br>
<br>

### How will they fit into ACA-PY?

There are two scenarios to consider when we want to add w3c format support to ACA-PY.

- Creating a W3C VC credential from credential definition, and issuing and presenting it as is
- Converting an already issued legacy anoncreds to W3C format(vice versa) so the converted credential can be issued or presented.

#### Creating a W3C VC credential from credential definition, and issuing and presenting it as is

The issuance, presentation and verification of legacy anoncreds are implemented in this [./aries_cloudagent/anoncreds](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds) directory. Therefore, we will also start from there.<br>

Let us navigate these implementation examples through the respective processes of the concerning agents - **Issuer** and **Holder** as described in https://github.com/hyperledger/anoncreds-rs/blob/main/README.md.

Looking at the [issuer.py](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/issuer.py) file and this code block:

```
async def create_credential_offer(self, credential_definition_id: str) -> str:
...
...
  credential_offer = CredentialOffer.create(
                  schema_id or cred_def.schema_id,
                  credential_definition_id,
                  key_proof.raw_value,
              )
...
```

we can implement the same thing in w3c VC format to send a w3c credential offer like so:

- W3C Credential Offer

**NOTE: In the W3C VCDM, there is no concept of a credential offer, and most implementations of W3C VCs have no step where a credential is offered before it is issued. This is because, unlike AnonCreds, W3C VCs require no cryptographic commitment from the holder. So an alternative approach to credential offers is to simply not provide them in the W3C case. However, we think that it is simpler to expose the step as part of our support, thus giving the option for the future and making the correspondence between W3C and AnonCreds features more regular.**

```
async def create_w3c_credential_offer(self, credential_definition_id: str) -> str:
...
...
  w3c_credential_offer = W3CCredentialOffer.create(...)
...
```

provided `W3CCredentialOffer` is already imported from `anoncreds` module.<br>

In a similar manner, we will proceed through the following processes in comparison with the legacy anoncreds implementations while watching out for signature differences between the two.<br>

- W3C Credential Create

**NOTE: There has been some changes to _encoding of attribute values_ for creating a credential, so we have to be adjust to the new changes.**

```
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

- W3C Credential Request

```
async def create_w3c_credential_request(
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

- W3C Credential Present

```
async def create_w3c_presentation(
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

#### Converting an already issued legacy anoncreds to W3C format(vice versa)

In this case, we can use `to_w3c` method of `Credential` class to convert from legacy to w3c and `to_legacy` method of `W3CCredential` class to convert from w3c to legacy.<br>

We could call `to_w3c` method like this:

```
w3c_cred = Credential.to_w3c(cred_def)
```

and for `to_legacy`:

```
legacy_cred = W3CCredential.to_legacy()
```

We don't need to input any parameters to it as it in turn calls `Credential.from_w3c()` method under the hood

### Format Handler for Issue_credential V2_0 Protocol

Keeping in mind that we are trying to create anoncreds(not another type of VC) in w3c format, what if we add a protocol-level w3c format support by adding a new format `W3C` in `./protocols/issue_credential/v2_0/messages/cred_format.py` -

```
# /protocols/issue_credential/v2_0/messages/cred_format.py

class Format(Enum):
    “””Attachment Format”””
    INDY = FormatSpec(...)
    LD_PROOF = FormatSpec(...)
    W3C = FormatSpec(
	“w3c/”,
	CredExRecordW3C,
	DeferLoad(
	    “aries_cloudagent.protocols.issue_credential.v2_0”
	    “.formats.w3c.handler.AnonCredsW3CFormatHandler”
	),
    )
```

And create a new CredExRecordW3C in reference to V20CredExRecordLDProof

```
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

Create w3c format handler with mapping like so:

```
# /protocols/issue_credential/v2_0/formats/w3c/handler.py

mapping = {
            CRED_20_PROPOSAL: VCDetailSchema,
            CRED_20_OFFER: VCDetailSchema,
            CRED_20_REQUEST: VCDetailSchema,
            CRED_20_ISSUE: VerifiableCredentialSchema,
        }
```

Doing so would allow us to be more independent in defining the schema suited for anoncreds in w3c format and once the proposal protocol can handle the w3c format, probably the rest of the flow can be easily implemented by adding `w3c` flag to the coressponding routes.

### How a W3C credential is stored in the wallet.

Storing a credential in the wallet is somewhat dependent on the kinds of metadata that are relevent. The metadata mapping between the W3C credential and an anoncreds credential is not fully clear yet.

One of the questions we need to answer is whether the preferred approach is to modify the existing store credential function so that any credential type is a valid input, or whether there should be a special function just for storing W3C credentials.

We will duplicate this [store_credential](https://github.com/hyperledger/aries-cloudagent-python/blob/8cfe8283ddb2a85e090ea1b8a916df2d78298ec0/aries_cloudagent/anoncreds/holder.py#L167) function and modify it:

```
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

### How can we handle multiple signatures on a W3C VC Format credential?

Only one of the signature types (CL) is allowed in the AnonCreds format, so if a W3C VC is created by `to_legacy()`, all signature types that can't be turned into a CL signature will be dropped. This would make the conversion lossy. Similarly, an AnonCreds credential carries only the CL signature, limiting output from `to_w3c()` signature types that can be derived from the source CL signature. A possible future enhancement would be to add an extra field to the AnonCreds data structure, in which additional signatures could be stored, even if they are not used. This could eliminate the lossiness, but it adds extra complexity and may not be worth doing.

### Compatibility with AFJ: how can we make sure that we are compatible?

We will write a test for the Aries Agent Test Framework that issues a W3C VC instead of an AnonCreds credential, and then run that test where one of the agents is ACA-PY and the other is based on AFJ -- and vice versa. Also write a test where a W3C VC is presented after an AnonCreds issuance, and run it with the two roles played by the two different agents. This is a simple approach, but if the tests pass, this should eliminate almost all risk of incompatibility.

### Will we introduce new dependencies, and what is risky or easy?

Any signfiicant bugs in the Rust implementation may prevent our wrappers from working, which would also prevent progress (or at least confirmed test results) on the higher-level code.

If AFJ lags behind in delivering equivalent functionality, we may not be able to demonstrate compatibility with the test harness.

### Where should the new issuance code go?

So the [vc](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/vc) directory contains code to verify vc's, is this a logical place to add the code for issuance?

### What do we call the new things? Flexcreds? or just W3C_xxx

Are we defining a concept called Flexcreds that is a credential with a proof array that you can generate more specific or limited credentials from? If so should this be included in the naming?

### How can a wallet retain the capability to present ONLY an anoncred credential?

If the wallet receives a "Flexcred" credential object with an array of proofs, the wallet may wish to present ONLY the more zero-knowledge anoncreds proof

How will wallets support that in a way that is developer-friendly to wallet devs?
