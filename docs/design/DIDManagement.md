# DID Management: Updates to DID and Key Storage

## Introduction

As part of our initiative to support a wider range of DID Methods in ACA-Py, we need to update the primitives related to DID and key storage within ACA-Py. This document outlines the proposed changes to how DIDs and keys are stored and managed, the rationale behind these changes, and the migration strategy from the current implementation.

## Background

### Askar Records and Lookup Mechanisms

[Askar](https://github.com/openwallet-foundation/askar) is the secure storage solution used by ACA-Py. Askar encrypts all data and provides a tagging mechanism to enable lookup of encrypted records. An entry in Askar is composed of the following elements:

- **Category:** The major group or "bucket" that the entry belongs to.
- **Name:** The primary identifier for the record; this is roughly equivalent to primary keys on a traditional DB table. The most efficient lookup possible is by name.
- **Value:** The value stored in the entry. This is usually a serialized JSON object.
- **Tags:** A mapping of strings to strings or lists of strings. These values can be used with the ["Wallet Query Language (WQL)"](https://github.com/hyperledger-archives/indy-sdk/tree/main/docs/design/011-wallet-query-language) to look up encrypted Askar entries efficiently.

Askar has a dedicated API for storage and retrieval of keys. However, this API is conceptually just a shorthand for record storage and retrieval from a "private" `key` category with the key itself as the value of the entry. Key entries behave almost exactly the same as non-key entries, including names and tags.

### Current State of DID Storage

At present, the `DIDInfo` class in ACA-Py is structured as follows:

```python
DIDInfo = NamedTuple( 
    "DIDInfo", 
    [ 
        ("did", str), 
        ("verkey", str), 
        ("metadata", dict), 
        ("method", DIDMethod), 
        ("key_type", KeyType), 
    ], 
) 
```

When stored in Askar, DID records have the following characteristics:

- **Category:** did
- **Name:** the value of the did, e.g. `did:example:123`. For Indy/did:sov, the value is the nym, e.g. `As728S9715ppSToDurKnvT`
- **Value:** a JSON object with the following attributes:
    - `did`: the DID (or nym)
    - `method`: the method name, e.g. `peer`
    - `verkey`: the base58 encoding of the public key associated with this DID
    - `verkey_type`: the key type of the verkey, e.g. `ed25519`
    - `metadata`: A container for arbitrary metadata. In practice, the following values are inserted into metadata:
        - `posted`: a boolean value representing whether this DID has been published to an indy network
        - `endpoint`: a string value representing the endpoint attrib of this DID on an indy network
- **Tags:**
    - `method`: the method name, e.g. `peer`
    - `verkey`: the base58 encoding of the public key associated with this DID
    - `verkey_type`: the key type of the verkey, e.g. `ed25519`

### Current State of Key Storage

Keys are managed by using the "verkey" as the name of the Askar record. Operations like signing or encrypting DIDComm messages retrieve the key by verkey. Usually, when initiating a cryptographic operation, the key is looked up by first retrieving the `DIDInfo` object by DID (or by nym) from the wallet and then the `DIDInfo.verkey` value is used to retrieve the key.

### Limitations

- **Indy-Centric Design:** The current structure is closely tied to Indy, making it less suitable for other DID Methods.
- **Single Key per DID:** Assumes a one-to-one relationship between DIDs and keys, which is not the case for many DID Methods.
- **Inefficient for Multiple Keys:** Lacks support for DIDs with multiple verification methods and keys.

## Proposed Updates

### Goals

- **Support Multiple Keys per DID:** Allow DIDs to have multiple associated keys and verification methods.
- **Method-Agnostic Design:** Create a storage structure that supports various DID Methods beyond Indy.
- **Efficient Key Retrieval:** Enable efficient lookup of keys based on DIDs, verification method IDs, verification relationships, and key types.

### Key Storage

#### Unbound Keys

Unbound keys are keys not (or not yet) associated with a specific DID.

Some DID Methods require knowledge of key material prior to creation of the DID. For example, in did:peer, the key material contributes directly to the formation of the DID itself. Unbound keys enable us to create and reference the key material during this early phase of DID creation for methods such as did:peer.

Additionally, there may be use cases that we have not yet identified that may be best served by creating and referencing keys not associated with a DID at all. Unbound keys serve this purpose as well.

- **Category:** `key`
- **Name:** Multikey representation (e.g., `z6Mkw...`)
- **Value:** The key material (private or public key)
- **Tags:**
  - `KeyAlg`: Implicit tag indicating the key algorithm (e.g., `ed25519`)
  - `alias`: A list of human-friendly aliases for the key

#### Bound Keys

Bound keys are associated with a specific DID.

When an unbound key is used to generate a DID for a method like did:peer, bound key representations MUST be stored in the wallet. The unbound representation MAY be removed after the bound representation is added.

- **Category:** `key`
- **Name:** Verification Method ID (absolute DID URL, e.g., `did:example:123#key-1`)
- **Value:** The key material
- **Tags:**
  - `KeyAlg`: Implicit tag indicating the key algorithm (e.g. `ed25519`)
  - `did`: The DID associated with the key
  - `rel`: A list of verification relationships (e.g., `["authentication", "assertionMethod"]`)

With this structure and tagging mechanism, we achieve direct retrieval without additional lookups when using verification method ID; efficient querying based on DID, purpose, and key type; and a single key supporting multiple verification relationships.

#### DIDComm v1 Keys

The DIDComm v1 stack is of sufficient complexity that it is necessary to make accommodations for it to continue operating more or less unchanged. To do this, any keys intended for use as a DIDComm v1 sender or receiver must also be stored in the following way:

- **Category:** `key`
- **Name:** verkey or base58 ed25519 public key
- **Value:** The key material (private or public key)
- **Tags:**
  - `KeyAlg`: Implicit tag indicating the key algorithm; for DIDComm v1 keys, this will always be `ed25519`
  - `did`: The DID this key is associated with

In DIDComm v1, it is required that the X25519 key used to perform key agreement will always be derived from the Ed25519 verkey. This X25519 key may be represented in bound keys for a DID but it MUST be the key derived from the Ed25519 key.

### DID Storage

With the Key storage updates, the DID records become less significant of a construct; rather than looking up a DID and then looking up a key, the usual pattern will be to look up a key directly with the DID value being used as a tag filter.

- **Category:** did
- **Name:** the value of the did, e.g. `did:example:123` (no "unqualified" DIDs allowed)
- **Value:** a JSON object with the following attributes:
    - `method`: the method name, e.g. `peer`
    - `metadata`: A container for arbitrary metadata; the DID Method implementation may determine what, if any, metadata is used
- **Tags:**
    - `method`: the method name, e.g. `peer`

### `Wallet.get_local_did_for_verkey`

This method looks up a DID we own by "verkey." This method is used to:

1. Associate an inbound message with a connection (`BaseConnectionManager.resolve_inbound_connection`)
2. Look up a connection based on recipient key of a mediation key list update (`RouteManager.connection_from_recipient_key`)
  - This method currently has issues. See #2818.
3. Apply a verkey filter on the `GET /wallet/did` Admin API Endpoint

For use cases 1 and 2, this should use the DIDComm v1 key record and return DID info based off the associated `did` tag.

For use case 3, filtering by verkey when listing DIDs should be deprecated.

### Nym Storage

To continue supporting Legacy Indy (i.e. Not did:indy), a new Nym record should be added.

- **Category:** nym
- **Name:** the value of the nym, e.g. `As728S9715ppSToDurKnvT`
- **Value:** a JSON object with the following attributes:
    - `nym`: the nym
    - `verkey`: the base58 encoding of the public key associated with this nym
    - `metadata`: A container for arbitrary metadata. In practice, the following values are inserted into metadata:
        - `posted`: a boolean value representing whether this DID has been published to an indy network
        - `endpoint`: a string value representing the endpoint attrib of this DID on an indy network
- **Tags:**
    - `verkey`: the base58 encoding of the public key associated with this DID

This record looks essentially the same as the previous DID record but simplified to remove past attempts to make DID records better support various DID Methods.

All Indy operations that depend on retrieving a `DIDInfo` object should be updated to retrieve a `Nym` object.

In the past, the term "DID" was used to describe what is more accurately a "Nym." Expectations about how the "DID" could be used, what keys were (or were not) capable of being associated with it, whether the "DID" was published to a public location or not, etc. were really limitations and expectations that apply uniquely to nyms. By making this distinction between DIDs and Nyms, support for Legacy Indy and support for new DID Methods should be able to coexist more harmoniously.

## Migration Strategy

To transition from the current storage model to the proposed one, we need to migrate existing data and ensure backward compatibility.

### Migrating `did:sov` DIDs that have been posted

- Duplicate all existing `did:sov` records into the new `nym` category, mapping attributes and tags appropriately.
- Create a bound key record for every `verkey`, using `did:sov:<nym>#key-1` as the verification method ID.
  - The key's `rel` tag must include at least `authentication` and `assertionMethod`
- Update the existing key record, identified by `verkey`, to include the `did` tag; this will become the DIDComm v1 key record.
- Update all DIDs to be fully qualified by adding `did:sov:` prefix
- Update all DID records to the new data model

### Migrating "unqualified peer DIDs"

- Replace the DID record with a `did:peer:4` short form DID constructed using the `verkey`.
  - Service endpoints MAY be excluded; this DID record will only be used for DIDComm v1 communication and the other end of the connection need not and will never know that we changed how we view the DID.
- Create a bound key record for the `verkey`, using the verification method ID used in the `did:peer:4` generation.
- Update the existing key record to include the `did` tag; this will become the DIDComm v1 key record.

### Migrating DIDs of other Methods

> TODO
