# DID Methods in ACA-Py

Decentralized Identifiers, or DIDs, are URIs that point to documents that describe cryptographic primitives and protocols used in decentralized identity management.
DIDs include methods that describe where and how documents can be retrieved.
DID methods support specific types of keys and may or may not require the holder to specify the DID itself.

ACA-Py provides a `DIDMethods` registry holding all the DID methods supported for storage in a wallet

> :warning: Askar and InMemory are the only wallets supporting this registry.

## Registering a DID method

By default, ACA-Py supports `did:key` and `did:sov`.
Plugins can register DID additional methods to make them available to holders.
Here's a snippet adding support for `did:web` to the registry from a plugin `setup` method.

```python
WEB = DIDMethod(
    name="web",
    key_types=[ED25519, BLS12381G2],
    rotation=True,
    holder_defined_did=HolderDefinedDid.REQUIRED  # did:web is not derived from key material but from a user-provided respository name
)

async def setup(context: InjectionContext):
    methods = context.inject(DIDMethods)
    methods.register(WEB)
```

## Creating a DID

`POST /wallet/did/create` can be provided with parameters for any registered DID method. Here's a follow-up to the
`did:web` method example:

```json
{
    "method": "web",
    "options": {
        "did": "did:web:doma.in",
        "key_type": "ed25519"
    }
}
```

## Resolving DIDs

For specifics on how DIDs are resolved in ACA-Py, see: [DID Resolution](DIDResolution.md).
