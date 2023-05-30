# DID Resolution in ACA-Py

Decentralized Identifiers, or DIDs, are URIs that point to documents that describe cryptographic primitives and protocols used in decentralized identity management. DIDs include methods that describe where and how documents can be retrieved. DID resolution is the process of "resolving" a DID Document from a DID as dictated by the DID method.

A DID Resolver is a piece of software that implements the methods for resolving a document from a DID.

For example, given the DID `did:example:1234abcd`, a DID Resolver that supports `did:example` might return:

```json
{
 "@context": "https://www.w3.org/ns/did/v1",
 "id": "did:example:1234abcd",
 "verificationMethod": [{
  "id": "did:example:1234abcd#keys-1",
  "type": "Ed25519VerificationKey2018",
  "controller": "did:example:1234abcd",
  "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
 }],
 "service": [{
  "id": "did:example:1234abcd#did-communication",
  "type": "did-communication",
  "serviceEndpoint": "https://agent.example.com/8377464"
 }]
}
```

For more details on DIDs and DID Resolution, see the [W3C DID Specification](https://www.w3.org/TR/did-core/).

In practice, DIDs and DID Documents are used for a variety of purposes but especially to help establish connections between Agents and verify credentials.

## `DIDResolver`

In ACA-Py, the `DIDResolver` provides the interface to resolve DIDs using registered method resolvers. Method resolver registration happens on startup in a `did_resolvers` list. This registry enables additional resolvers to be loaded via plugin.

### Example usage

```python
class ExampleMessageHandler:
    async def handle(context: RequestContext, responder: BaseResponder):
    """Handle example message."""
    resolver = await context.inject(DIDResolver)

    doc: dict = await resolver.resolve("did:example:123")
    assert doc["id"] == "did:example:123"
    
    verification_method = await resolver.dereference("did:example:123#keys-1")
    
    # ...
```

## Method Resolver Selection

On `DIDResolver.resolve` or `DIDResolver.dereference`, the resolver interface will select the most appropriate method resolver to handle the given DID. In this selection process, method resolvers are distinguished from each other by:

- Type. The resolver's type falls into one of two categories: native or non-native. A "native" resolver will perform all resolution steps directly. A "non-native" resolver delegates all or part of resolution to another service or entity.
- Self-reported supported DIDs. Each method resolver implements a `supports` method or a `supported_did_regex` method. These methods are used to determine whether the given DID can be handled by the method resolver.

The selection algorithm roughly follows the following steps:

1. Filter out all resolvers where `resolver.supports(did)` returns `false`.
2. Partition remaining resolvers by type with all native resolvers followed by non-native resolvers (registration order preserved within partitions).
3. For each resolver in the resulting list, attempt to resolve the DID and return the first successful result.

## Resolver Plugins

Extending ACA-Py with additional Method Resolvers should be relatively simple. Supposing that you want to resolve DIDs for the `did:cool` method, this should be as simple as installing a method resolver into your python environment and loading the resolver on startup. If no method resolver exists yet for `did:cool`, writing your own should require minimal overhead.

### Writing a resolver plugin

Method resolver plugins are composed of two primary pieces: plugin injection and resolution logic. The resolution logic dictates how a DID becomes a DID Document, following the given DID Method Specification. This logic is implemented using the `BaseDIDResolver` class as the base. `BaseDIDResolver` is an abstract base class that defines the interface that the core `DIDResolver` expects for Method resolvers.

The following is an example method resolver implementation. In this example, we have 2 files, one for each piece (injection and resolution). The `__init__.py` will be in charge of injecting the plugin, and `example_resolver.py` will have the logic implementation to resolve for a fabricated `did:example` method.

#### `__init __.py`

```python=
from aries_cloudagent.config.injection_context import InjectionContext
from ..resolver.did_resolver import DIDResolver

from .example_resolver import ExampleResolver


async def setup(context: InjectionContext):
    """Setup the plugin."""
    registry = context.inject(DIDResolver)
    resolver = ExampleResolver()
    await resolver.setup(context)
    registry.append(resolver)
```

#### `example_resolver.py`

```python=
import re
from typing import Pattern
from aries_cloudagent.resolver.base import BaseDIDResolver, ResolverType

class ExampleResolver(BaseDIDResolver):
    """ExampleResolver class."""

    def __init__(self):
        super().__init__(ResolverType.NATIVE)
        # Alternatively, ResolverType.NON_NATIVE
        self._supported_did_regex = re.compile("^did:example:.*$")

    @property
    def supported_did_regex(self) -> Pattern:
        """Return compiled regex matching supported DIDs."""
        return self._supported_did_regex

    async def setup(self, context):
        """Setup the example resolver (none required)."""

    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve example DIDs."""
        if did != "did:example:1234abcd":
            raise DIDNotFound(
                "We only actually resolve did:example:1234abcd. Sorry!"
            )

        return {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:example:1234abcd",
            "verificationMethod": [{
                "id": "did:example:1234abcd#keys-1",
                "type": "Ed25519VerificationKey2018",
                "controller": "did:example:1234abcd",
                "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
            }],
            "service": [{
                "id": "did:example:1234abcd#did-communication",
                "type": "did-communication",
                "serviceEndpoint": "https://agent.example.com/"
            }]
        }
```

#### Errors

There are 3 different errors associated with resolution in ACA-Py that could be used for development purposes.

- ResolverError
  - Base class for resolver exceptions.
- DIDNotFound
  - Raised when DID is not found using DID method specific algorithm.
- DIDMethodNotSupported
  - Raised when no resolver is registered for a given did method.

### Using Resolver Plugins

In this section, the [Github Resolver Plugin found here](https://github.com/dbluhm/acapy-resolver-github) will be used as an an example plugin to work with. This resolver resolves `did:github` DIDs.

The resolution algorithm is simple: for the github DID `did:github:dbluhm`, the method specific identifier `dbluhm` (a GitHub username) is used to lookup a `index.jsonld` file in the `ghdid` repository in that GitHub users profile. See [GitHub DID Method Specification](http://docs.github-did.com/did-method-spec/) for more details.

To use this plugin, first install it into your project's python environment:

```shell
pip install git+https://github.com/dbluhm/acapy-resolver-github
```

Then, invoke ACA-Py as you normally do with the addition of:

```shell
$ aca-py start \
    --plugin acapy_resolver_github \
    # ... the remainder of your startup arguments
```

Or add the following to your configuration file:

```yaml
plugin:
  - acapy_resolver_github
```

The following is a fully functional Dockerfile encapsulating this setup:

```dockerfile=
# TODO replace the following two lines with ACA-Py 0.7.0 when released
FROM bcgovimages/von-image:py36-1.16-0
RUN pip3 install git+https://github.com/hyperledger/aries-cloudagent-python@2ff1ddba897d26a7deb761924018145162cc867c
RUN pip3 install git+https://github.com/dbluhm/acapy-resolver-github

CMD ["aca-py", "start", "-it", "http", "0.0.0.0", "3000", "-ot", "http", "-e", "http://localhost:3000", "--admin", "0.0.0.0", "3001", "--admin-insecure-mode", "--no-ledger", "--plugin", "acapy_resolver_github"]
```

To use the above dockerfile:

```shell
docker build -t resolver-example .
docker run --rm -it -p 3000:3000 -p 3001:3001 resolver-example
```

### Directory of Resolver Plugins

- [Github Resolver](https://github.com/dbluhm/acapy-resolver-github)
- [Universal Resolver](https://github.com/sicpa-dlab/acapy-resolver-universal)
- [DIDComm Resolver](https://github.com/sicpa-dlab/acapy-resolver-didcomm)

## References

<https://www.w3.org/TR/did-core/>
<https://w3c-ccg.github.io/did-resolution/>
