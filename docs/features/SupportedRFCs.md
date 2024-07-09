# Aries AIP and RFCs Supported in Aries Cloud Agent Python

This document provides a summary of the adherence of ACA-Py to the [Aries Interop
Profiles](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile),
and an overview of the ACA-Py feature set. This document is
manually updated and as such, may not be up to date with the most recent release of
ACA-Py or the repository `main` branch. Reminders (and PRs!) to update this page are
welcome! If you have any questions, please contact us on the #aries channel on
[Hyperledger Discord](https://discord.gg/hyperledger) or through an issue in this repo.

**Last Update**: 2024-07-08, Release 1.0.0rc4

> The checklist version of this document was created as a joint effort
> between [Northern Block](https://northernblock.io/), [Animo Solutions](https://animo.id/) and the Ontario government, on behalf of the Ontario government.

## AIP Support and Interoperability

See the [Aries Agent Test Harness](https://github.com/hyperledger/aries-agent-test-harness) and the
[Aries Interoperability Status](https://aries-interop.info) for daily interoperability test run results between
ACA-Py and other Aries Frameworks and Agents.

| AIP Version | Supported | Notes |
|  - | :-------: | -------- |
| AIP 1.0     | :white_check_mark:  | Fully supported. |
| AIP 2.0     | :white_check_mark:  | Fully supported. |

A summary of the Aries Interop Profiles and Aries RFCs supported in ACA-Py can be found [later in this document](#supported-rfcs).

## Platform Support

| Platform   |     Supported      | Notes                                                                                                                      |
| ---------- | :----------------: | -------------------------------------------------------------------------------------------------------------------------- |
| Server     | :white_check_mark: |                                                                                                                            |
| Kubernetes | :white_check_mark: | BC Gov has extensive experience running ACA-Py on Red Hat's OpenShift Kubernetes Distribution.                             |
| Docker     | :white_check_mark: | Official docker images are published to the GitHub  container repository at `ghcr.io/hyperledger/aries-cloudagent-python`. |
| Desktop    |     :warning:      | Could be run as a local service on the computer                                                                            |
| iOS        |        :x:         |                                                                                                                            |
| Android    |        :x:         |                                                                                                                            |
| Browser    |        :x:         |                                                                                                                            |

## Agent Types

| Role     | Supported | Notes      |
| -------- | :-------: |  --------- |
| Issuer   | :white_check_mark:        |            |
| Holder   | :white_check_mark:        |            |
| Verifier | :white_check_mark:        |            |
| Mediator Service | :white_check_mark:        | See the [aries-mediator-service](https://github.com/hyperledger/aries-mediator-service), a pre-configured, production ready Aries Mediator Service based on a released version of ACA-Py. |
| Mediator Client | :white_check_mark: | |
| Indy Transaction Author | :white_check_mark:        |    |
| Indy Transaction Endorser | :white_check_mark:  | |
| Indy Endorser Service | :white_check_mark:        | See the [aries-endorser-service](https://github.com/hyperledger/aries-endorser-service), a pre-configured, production ready Aries Endorser Service based on a released version of ACA-Py. |

## Credential Types

| Credential Type | Supported | Notes |
| --- | :--: | -- |
| [Hyperledger AnonCreds] | :white_check_mark: | Includes full issue VC, present proof, and revoke VC support. |
| [W3C Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/) | :white_check_mark: | Supports JSON-LD Data Integrity Proof Credentials using the `Ed25519Signature2018`, `BbsBlsSignature2020` and `BbsBlsSignatureProof2020` signature suites.<br><br>Supports the [DIF Presentation Exchange](https://identity.foundation/presentation-exchange/) data format for presentation requests and presentation submissions.<br><br>Work currently underway to add support for [Hyperledger AnonCreds] in W3C VC JSON-LD Format |

[Hyperledger AnonCreds]: https://www.hyperledger.org/projects/anoncreds

## DID Methods

| Method | Supported | Notes |
| --- | :--: | -- |
| "unqualified" | :warning: Deprecated | Pre-DID standard identifiers. Used either in a peer-to-peer context, or as an alternate form of a `did:sov` DID published on an Indy network. |
| `did:sov` | :white_check_mark: |  |
| `did:web` | :white_check_mark: | Resolution only |
| `did:key` | :white_check_mark: | |
| `did:peer` | :white_check_mark:| Algorithms `2`/`3` and `4` |
| Universal Resolver | :white_check_mark: | A [plug in](https://github.com/sicpa-dlab/acapy-resolver-universal) from [SICPA](https://www.sicpa.com/) is available that can be added to an ACA-Py installation to support a [universal resolver](https://dev.uniresolver.io/) capability, providing support for most DID methods in the [W3C DID Method Registry](https://w3c.github.io/did-spec-registries/#did-methods). |

## Secure Storage Types

| Secure Storage Types | Supported | Notes |
| --- | :--: | -- |
| [Aries Askar] | :white_check_mark: | Recommended - Aries Askar provides equivalent/evolved secure storage and cryptography support to the "indy-wallet" part of the Indy SDK. When using Askar (via the `--wallet-type askar` startup parameter), other functionality is handled by [CredX](https://github.com/hyperledger/indy-shared-rs) (AnonCreds) and [Indy VDR](https://github.com/hyperledger/indy-vdr) (Indy ledger interactions). |
| [Aries Askar]-AnonCreds | :white_check_mark: | Recommended - When using Askar/AnonCreds (via the `--wallet-type askar-anoncreds` startup parameter), other functionality is handled by [AnonCreds RS](https://github.com/hyperledger/anoncreds-rs) (AnonCreds) and [Indy VDR](https://github.com/hyperledger/indy-vdr) (Indy ledger interactions).<br><br>This `wallet-type` will eventually be the same as `askar` when we have fully integrated the AnonCreds RS library into ACA-Py. |
| [Indy SDK](https://github.com/hyperledger/indy-sdk/tree/master/docs/design/003-wallet-storage) | :x: | **Removed in ACA-Py Release 1.0.0rc4** |

> Existing deployments using the [Indy SDK] **MUST** transition to [Aries Askar] and related components as soon as possible. See the [Indy SDK to Askar Migration Guide] for guidance.

[Aries Askar]: https://github.com/hyperledger/aries-askar
[Indy SDK]: https://github.com/hyperledger/indy-sdk/tree/master/docs/design/003-wallet-storage

## Miscellaneous Features

| Feature | Supported | Notes |
| --- | :--: | -- |
| ACA-Py Plugins | :white_check_mark:  | The [ACA-Py Plugins] repository contains a growing set of plugins that are maintained and (mostly) tested against new releases of ACA-Py. |
| Multi use invitations            | :white_check_mark:  |         |
| Invitations using public did     | :white_check_mark:        |         |
| Invitations using peer dids supporting connection reuse     | :white_check_mark:        |         |
| Implicit pickup of messages in role of mediator | :white_check_mark:        |         |
| [Revocable AnonCreds Credentials](https://github.com/hyperledger/indy-hipe/tree/main/text/0011-cred-revocation) | :white_check_mark:        |         |
| Multi-Tenancy      | :white_check_mark:        | [Documentation](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Multitenancy.md) |
| Multi-Tenant Management | :white_check_mark: | The [Traction] open source project from BC Gov is a layer on top of ACA-Py that enables the easy management of ACA-Py tenants, with an Administrative UI ("The Innkeeper") and a Tenant UI for using ACA-Py in a web UI (setting up, issuing, holding and verifying credentials) |
| Connection-less (non OOB protocol / AIP 1.0)               | :white_check_mark:        | Only for issue credential and present proof          |
| Connection-less (OOB protocol / AIP 2.0)               | :white_check_mark:        | Only for present proof          |
| Signed Attachments               | :white_check_mark:        | Used for OOB         |
| Multi Indy ledger support (with automatic detection) | :white_check_mark: | Support added in the 0.7.3 Release.   |
| Persistence of mediated messages | :white_check_mark:        | Plugins in the [ACA-Py Plugins] repository are available for persistent queue support using Redis and Kafka. Without persistent queue support, messages are stored in an in-memory queue and so are subject to loss in the case of a sudden termination of an ACA-Py process. The in-memory queue is properly handled in the case of a graceful shutdown of an ACA-Py process (e.g. processing of the queue completes and no new messages are accepted).  |
| Storage Import & Export           | :warning:        | Supported by directly interacting with the Aries Askar (e.g., no Admin API endpoint available for wallet import & export). Aries Askar support includes the ability to import storage exported from the Indy SDK's "indy-wallet" component. Documentation for migrating from Indy SDK storage to Askar can be found in the [Indy SDK to Askar Migration Guide].|
| SD-JWTs | :white_check_mark: | Signing and verifying SD-JWTs is supported |

[ACA-Py Plugins]: https://github.com/hyperledger/aries-acapy-plugins
[Indy SDK to Askar Migration Guide]: ../deploying/IndySDKtoAskarMigration.md
[Traction]: https://github.com/bcgov/traction

## Supported RFCs

### AIP 1.0

All RFCs listed in [AIP 1.0](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-10) are fully supported in ACA-Py. The following table
provides notes about the implementation of specific RFCs.

| RFC | Supported | Notes |
| --- | :--: | -- |
| [0025-didcomm-transports](https://github.com/hyperledger/aries-rfcs/tree/b490ebe492985e1be9804fc0763119238b2e51ab/features/0025-didcomm-transports)      | :white_check_mark:        | ACA-Py currently supports HTTP and WebSockets for both inbound and outbound messaging. Transports are pluggable and an agent instance can use multiple inbound and outbound transports.|
| [0160-connection-protocol](https://github.com/hyperledger/aries-rfcs/tree/9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol)    | :white_check_mark:        | The agent supports Connection/DID exchange initiated from both plaintext invitations and public DIDs that enable bypassing the invitation message. |

### AIP 2.0

All RFCs listed in [AIP 2.0](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-20) (including the sub-targets)
are fully supported in ACA-Py **EXCEPT** as noted in the table below.

| RFC | Supported | Notes |
| --- | :--: | -- |
| Fully Supported |  |  |

### Other Supported RFCs

| RFC | Supported | Notes |
| --- | :--: | -- |
| [0031-discover-features](https://github.com/hyperledger/aries-rfcs/blob/main/features/0031-discover-features/README.md)           | :white_check_mark:        | Rarely (never?) used, and in implementing the V2 version of the protocol, the V1 version was found to be incomplete and was updated as part of Release 0.7.3  |
| [0028-introduce](https://github.com/hyperledger/aries-rfcs/blob/main/features/0028-introduce/README.md)            | :white_check_mark:        |      |
| [00509-action-menu](https://github.com/hyperledger/aries-rfcs/blob/main/features/0509-action-menu/README.md)       | :white_check_mark:        |      |
