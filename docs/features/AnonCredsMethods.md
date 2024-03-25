# Adding AnonCreds Methods to ACA-Py

ACA-Py was originally developed to be used with [Hyperledger AnonCreds] objects (Schemas,
Credential Definitions and Revocation Registries) published on [Hyperledger Indy] networks. However,
with the evolution of "ledger-agnostic" AnonCreds, ACA-Py supports publishing AnonCreds objects wherever
you want to put them. If you want to add a new "AnonCreds Methods" to publish AnonCreds
objects to a new Verifiable Data Registry (VDR) (perhaps to your favorite blockchain, or using a web-based DID method),
you'll find the details of how to do that here. We often using the term "ledger" for the
location where AnonCreds objects are published, but here will use "VDR", since a VDR does
not have to be a ledger.

[Hyperledger AnonCreds]: https://www.hyperledger.org/projects/anoncreds
[Hyperledger Indy]: https://www.hyperledger.org/projects/hyperledger-indy

The information in this document was discussed on an ACA-Py Maintainers call in March 2024.
You can watch the call recording by clicking [here](https://youtu.be/tJXY4IM-2l8).

:warning: This is an early version of this document and we assume those reading it
are quite familiar with using ACA-Py, have a good understanding of ACA-Py internals, and are
Python experts. See the [Questions or Comments](#questions-or-comments) section below
for how to get help as you work through this.

[Hyperledger Discord Server]: https://discord.gg/hyperledger

## Create a Plugin

We recommend that if you are adding a new AnonCreds method, you do so by creating an ACA-Py plugin.
See the documentation on [ACA-Py plugins] and use the set of plugins available in the [aries-acapy-plugins]
repository to help you get started. When you finish your AnonCreds method, we recommend that you publish the plugin
in the [aries-acapy-plugins] repository. If you think that the AnonCreds method you create should
be part of ACA-Py core, get your plugin complete and raise the question of adding it to ACA-Py. The
Maintainers will be happy to discuss the merits of the idea. No promises though.

[ACA-Py plugins]: ./PlugIns.md
[aries-acapy-plugins]: https://github.com/hyperledger/aries-acapy-plugins

Your AnonCreds plugin will have an [initialization routine] that will register your AnonCreds
implementation. It will be registering the identifiers that your method will be using such. It
will be the identifier constructs that will trigger the appropriate AnonCreds Registrar and
Resolver that will be called for any given AnonCreds object identifier. Check out this
[example of the registration] of the ["legacy" Indy] AnonCreds method for more details.

[initialization routine]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/__init__.py
[example of the registration]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/default/legacy_indy/registry.py

## The Implementation

The basic work involved in creating an AnonCreds method is the implementation of both a "registrar" to
write AnonCreds objects to a VDR, and a "resolver" to read AnonCreds objects from a VDR. To do
that for your new AnonCreds method, you will need to:

- Implement `BaseAnonCredsResolver` - [here](https://github.com/hyperledger/aries-cloudagent-python/blob/1786553ffea244c67d82ceaa3f1793dd1ec1c0f5/aries_cloudagent/anoncreds/base.py#L113)
- Implement `BaseAnonCredsRegistrar` - [here](https://github.com/hyperledger/aries-cloudagent-python/blob/1786553ffea244c67d82ceaa3f1793dd1ec1c0f5/aries_cloudagent/anoncreds/base.py#L139)

The links above are to a specific commit and the code may have been updated since. You might want to
look at the methods in the current version of [aries_cloudagent/anoncreds/base.py](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/base.py) in the `main` branch.

The interface for those methods are very clean, and there are currently two implementations of the 
methods in the ACA-Py codebase -- the ["legacy" Indy] implementation, and the [did:indy] Indy implementation.
There is also a [did:web] resolver implementation.

["legacy" Indy]: https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds/default/legacy_indy
[did:indy]: https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds/default/did_indy
[did:web]: https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds/default/did_web

Models for the API are defined [here](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/anoncreds/models)

## Events

When you create your AnonCreds method registrar, make sure that your implementations call appropriate
`finish_*` event (e.g., `AnonCredsIssuer.finish_schema`, `AnonCredsIssuer.finish_cred_def`, etc.) in
[AnonCreds Issuer]. The calls are necessary to trigger the automation of AnonCreds event creation that
is done by ACA-Py, particularly around the handling of Revocation Registries. As you (should) know, when
an Issuer uses ACA-Py to create a Credential Definition that supports revocation, ACA-Py automatically
creates and publishes two Revocation Registries related to the Credential Definition, publishes the tails
file for each, makes one active, and sets the other to be activated as soon as the active one runs out of
credentials. Your AnonCreds method implementation doesn't have to do much to make that happen -- ACA-Py
does it automatically -- but your implementation must call the `finish_*` to make trigger ACA-Py to continue
the automation. You can see in [Revocation Setup] the automation setup.

[AnonCreds Issuer]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/issuer.py#L56
[Revocation Setup]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/anoncreds/revocation_setup.py

## Questions or Comments

The ACA-Py maintainers welcome questions from those new to the community that
have the skills to implement a new AnonCreds method. Use the `#aries-cloudagent-python` channel
on the [Hyperledger Discord Server] or open an issue in this repo to get help.

Pull Requests to the ACA-Py repository to improve this content are welcome!
