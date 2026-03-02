# Aries AIP, Protocols, Credential Formats, and Other Capabilities Supported in ACA-Py

This document provides a summary of the adherence of ACA-Py to the [Aries Interop
Profiles](https://github.com/decentralized-identity/aries-rfcs/tree/main/concepts/0302-aries-interop-profile),
and an overview of the ACA-Py feature set. This document is
manually updated and as such, may not be up to date with the most recent release of
ACA-Py or the repository `main` branch. Reminders (and PRs!) to update this page are
welcome! If you have any questions, please contact us on the #aries channel on
[OpenWallet Foundation Discord](https://discord.gg/openwallet-foundation) or through an issue in this repo.

**Last Update**: 2026-02-27, Release 1.5.1

> The checklist version of this document was created as a joint effort
> between [Northern Block](https://northernblock.io/), [Animo Solutions](https://animo.id/) and the Ontario government, on behalf of the Ontario government.

## AIP Support and Interoperability

See the [Aries Agent Test Harness](https://github.com/openwallet-foundation/owl-agent-test-harness) and the
[Aries Interoperability Status](https://aries-interop.info) for daily interoperability test run results between
ACA-Py and other decentralized trust Frameworks and Agents.

| AIP Version | Supported | Notes |
|  - | :-------: | -------- |
| AIP 1.0     | :white_check_mark:  | Partially supported. Deprecation notices published, Connections protocol moved into an [ACA-Py Plugin](https://plugins.aca-py.org/latest/connections/)|
| AIP 2.0     | :white_check_mark:  | Fully supported. |

A summary of the Aries Interop Profiles and Aries RFCs supported in ACA-Py can be found [later in this document](#supported-rfcs).

## Platform Support

| Platform   |     Supported      | Notes                                                                                                                      |
| ---------- | :----------------: | -------------------------------------------------------------------------------------------------------------------------- |
| Server     | :white_check_mark: |                                                                                                                            |
| Kubernetes | :white_check_mark: | An [ACA-Py Helm Chart] is available in the [OWF Helm Chart] repository.                            |
| Docker     | :white_check_mark: | Official docker images are published to the GitHub  container repository at [https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent). |
| Desktop    |     :warning:      | Could be run as a local service on the computer                                                                            |
| iOS        |        :x:         |                                                                                                                            |
| Android    |        :x:         |                                                                                                                            |
| Browser    |        :x:         |                                                                                                                            |

[ACA-Py Helm Chart]: https://github.com/openwallet-foundation/helm-charts/tree/main/charts/acapy
[OWF Helm Chart]: https://github.com/openwallet-foundation/helm-charts

## Agent Types

| Role     | Supported | Notes      |
| -------- | :-------: |  --------- |
| Issuer   | :white_check_mark:        |            |
| Holder   | :white_check_mark:        |            |
| Verifier | :white_check_mark:        |            |
| Mediator Service | :white_check_mark:        | See the [didcomm-mediator-service](https://github.com/openwallet-foundation/didcomm-mediator-service), a pre-configured, production ready Aries Mediator Service based on a released version of ACA-Py. |
| Mediator Client | :white_check_mark: | |
| Indy Transaction Author | :white_check_mark:        |    |
| Indy Transaction Endorser | :white_check_mark:  | |
| Indy Endorser Service | :white_check_mark:        | See the [acapy-endorser-service](https://github.com/openwallet-foundation/acapy-endorser-service), a pre-configured, production ready Aries Endorser Service based on a released version of ACA-Py. |

## Credential Types

| Credential Type | Supported | Notes |
| --- | :--: | -- |
| [Hyperledger AnonCreds] | :white_check_mark: | Includes full issue VC, present proof, and revoke VC support. |
| [W3C Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/) | :white_check_mark: | Supports JSON-LD Data Integrity Proof Credentials using the `Ed25519Signature2018`, `EcdsaSecp256r1Signature2019`, `BbsBlsSignature2020` and `BbsBlsSignatureProof2020` signature suites.<br><br>Supports the [DIF Presentation Exchange](https://identity.foundation/presentation-exchange/) data format for presentation requests and presentation submissions.<br><br>Work currently underway to add support for [Hyperledger AnonCreds] in W3C VC JSON-LD Format |

[Hyperledger AnonCreds]: https://www.lfdecentralizedtrust.org/projects/anoncreds

## DID Methods

| Method | Supported | Notes |
| --- | :--: | -- |
| "unqualified" | :warning: Deprecated | Pre-DID standard identifiers. Used either in a peer-to-peer context, or as an alternate form of a `did:sov` DID published on an Indy network. |
| `did:sov` | :white_check_mark: |  |
| `did:web` | :white_check_mark: | Resolution only |
| `did:key` | :white_check_mark: | |
| `did:peer` | :white_check_mark:| Algorithms `2`/`3` and `4` |
| `did:webvh` | :white_check_mark:| Supports both DID registration, resolution and the use of [did:webvh] for Verifiable Credentials, including the [did:webvh AnonCreds Method]. Requires the [didwebvh Plugin] for ACA-Py, and the use of a [didwebvh Server] instance. See the [didwebvh Plugin] documentation fro deployment and the equivalent of DID Indy Endorser functionality.  |
| Universal Resolver | :white_check_mark: | A [plug in](https://github.com/sicpa-dlab/acapy-resolver-universal) from [SICPA](https://www.sicpa.com/) is available that can be added to an ACA-Py installation to support a [universal resolver](https://dev.uniresolver.io/) capability, providing support for most DID methods in the [W3C DID Method Registry](https://www.w3.org/TR/did-extensions-methods/). |

[didwebvh Plugin]: https://plugins.aca-py.org/latest/webvh/
[didwebvh Server]: https://github.com/decentralized-identity/didwebvh-server-py
[did:webvh]: https://identity.foundation/didwebvh/
[did:webvh AnonCreds Method]: https://identity.foundation/didwebvh/anoncreds-method/

## Secure Storage Types

| Secure Storage Types | Supported | Notes |
| --- | :--: | -- |
| [Askar] | :white_check_mark: | Askar provides secure storage and cryptography support, replacing the former "indy-wallet" component. When using Askar (via the `--wallet-type askar` startup parameter), credential handling functionality is by [CredX](https://github.com/hyperledger/indy-shared-rs) (AnonCreds) and [Indy VDR](https://github.com/hyperledger/indy-vdr) (Indy ledger interactions). |
| [Askar]-AnonCreds | :white_check_mark: | Recommended - When using Askar/AnonCreds (via the `--wallet-type askar-anoncreds` startup parameter), AnonCreds credential handling functionality is by [AnonCreds RS](https://github.com/hyperledger/anoncreds-rs). All key management and ACA-Py storage is managed by Askar.|
| [Kanon]-AnonCreds | :white_check_mark: | Recommended - When using Kanon/AnonCreds (via the `--wallet-type kanon-anoncreds` startup parameter), AnonCreds credential handling functionality is by [AnonCreds RS](https://github.com/hyperledger/anoncreds-rs). All key management is handled by Askar, and all other ACA-Py storage is managed by [Kanon] and the selected database management system. With [Kanon], data is encrypted at rest using the database management system's handling.|
| [Indy SDK](https://github.com/hyperledger/indy-sdk/tree/main/docs/design/003-wallet-storage) | :x: | **Removed in ACA-Py Release 1.0.0rc5** |

> Existing deployments using the [Indy SDK] **MUST** transition to [Askar] and related components as soon as possible. See the [Indy SDK to Askar Migration Guide] for guidance.

[Askar]: https://github.com/openwallet-foundation/askar
[Kanon]: https://aca-py.org/latest/features/KanonStorage/
[Indy SDK]: https://github.com/hyperledger/indy-sdk/tree/main/docs/design/003-wallet-storage

## Miscellaneous Features

| Feature | Supported | Notes |
| --- | :--: | -- |
| ACA-Py Plugins | :white_check_mark:  | The [ACA-Py Plugins] are a growing set of plugins that are maintained and (mostly) tested against new releases of ACA-Py. |
| Multi use invitations            | :white_check_mark:  |         |
| Invitations using public did     | :white_check_mark:        |         |
| Invitations using peer dids supporting connection reuse     | :white_check_mark:        |         |
| Implicit pickup of messages in role of mediator | :white_check_mark:        |         |
| [Revocable AnonCreds Credentials](https://github.com/hyperledger/indy-hipe/tree/main/text/0011-cred-revocation) | :white_check_mark:        |         |
| Multi-Tenancy      | :white_check_mark:        | [Multi-tenant Documentation] |
| Multi-Tenant Management | :white_check_mark: | The [Traction] open source project from BC Gov is a layer on top of ACA-Py that enables the easy management of ACA-Py tenants, with an Administrative UI ("The Innkeeper") and a Tenant UI for using ACA-Py in a web UI (setting up, issuing, holding and verifying credentials) |
| Connection-less (non OOB protocol / AIP 1.0)               | :white_check_mark:        | Only for issue credential and present proof          |
| Connection-less (OOB protocol / AIP 2.0)               | :white_check_mark:        | Only for present proof          |
| Signed Attachments               | :white_check_mark:        | Used for OOB         |
| Multi Indy ledger support (with automatic detection) | :white_check_mark: | Support added in the 0.7.3 Release.   |
| Persistence of mediated messages | :white_check_mark:        | Plugins in the [ACA-Py Plugins] repository are available for persistent queue support using Redis and Kafka. Without persistent queue support, messages are stored in an in-memory queue and so are subject to loss in the case of a sudden termination of an ACA-Py process. The in-memory queue is properly handled in the case of a graceful shutdown of an ACA-Py process (e.g. processing of the queue completes and no new messages are accepted).  |
| Storage Import & Export           | :warning:        | Supported by directly interacting with the Askar (e.g., no Admin API endpoint available for wallet import & export). Askar support includes the ability to import storage exported from the Indy SDK's "indy-wallet" component. Documentation for migrating from Indy SDK storage to Askar can be found in the [Indy SDK to Askar Migration Guide].|
| SD-JWTs | :white_check_mark: | Signing and verifying SD-JWTs is supported |

[Multi-tenant Documentation]: ./Multitenancy.md
[ACA-Py Plugins]: https://plugins.aca-py.org
[Indy SDK to Askar Migration Guide]: ../deploying/IndySDKtoAskarMigration.md
[Traction]: https://github.com/bcgov/traction

## Supported RFCs

### AIP 1.0

While the RFCs listed in [AIP
1.0](https://identity.foundation/aries-rfcs/latest/concepts/0302-aries-interop-profile/#aries-interop-profile-version-10)
are fully supported using ACA-Py, the primary protocols have been deprecated,
removed from the core, and are now only available as plugins. The following
table provides notes about the implementation of specific RFCs.

| RFC | Supported | Notes |
| --- | :--: | -- |
| [0025-didcomm-transports](https://github.com/decentralized-identity/aries-rfcs/tree/b490ebe492985e1be9804fc0763119238b2e51ab/features/0025-didcomm-transports)      | :white_check_mark:        | ACA-Py currently supports HTTP and WebSockets for both inbound and outbound messaging. Transports are pluggable and an agent instance can use multiple inbound and outbound transports.|
| [0160-connection-protocol](https://github.com/decentralized-identity/aries-rfcs/tree/9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol)    | :x:        | **MOVED TO PLUGIN** The protocol has been moved into the [ACA-Py Plugins] repository. Those upgrading to Release 1.3.0 or later and continuing to use this protocol **MUST** include the [Connections plugin](https://plugins.aca-py.org/latest/connections/) in their deployment configuration. Users **SHOULD** upgrade to the equivalent [AIP 2.0] protocols as soon as possible. |
| [0036-issue-credential-v1.0](https://github.com/decentralized-identity/aries-rfcs/tree/bb42a6c35e0d5543718fb36dd099551ab192f7b0/features/0036-issue-credential)    | :x:         | **MOVED TO PLUGIN** The protocol has been moved into the [ACA-Py Plugins] repository. Those upgrading to Release 1.3.0 or later and continuing to use this protocol **MUST** include the [Issue Credentials v1.0 plugin](https://plugins.aca-py.org/latest/issue_credential/) in their deployment configuration. Users **SHOULD** upgrade to the equivalent [AIP 2.0] protocols as soon as possible.  |
| [0037-present-proof-v1.0](https://github.com/decentralized-identity/aries-rfcs/tree/4fae574c03f9f1013db30bf2c0c676b1122f7149/features/0037-present-proof)    | :x:         | **MOVED TO PLUGIN** The protocol has been moved into the [ACA-Py Plugins] repository. Those upgrading to Release 1.3.0 or later and continuing to use this protocol **MUST** include the [Present Proof v1.0 plugin](https://plugins.aca-py.org/latest/present_proof/) in their deployment configuration. Users **SHOULD** upgrade to the equivalent [AIP 2.0] protocols as soon as possible. |

[AIP 2.0]: https://identity.foundation/aries-rfcs/latest/concepts/0302-aries-interop-profile/#aries-interop-profile-version-20

### AIP 2.0

All RFCs listed in [AIP 2.0] (including the sub-targets)
are fully supported in ACA-Py **EXCEPT** as noted in the table below.

| RFC | Supported | Notes |
| --- | :--: | -- |
| Fully Supported |  |  |

### Other Supported RFCs

| RFC | Supported | Notes |
| --- | :--: | -- |
| [0031-discover-features](https://github.com/decentralized-identity/aries-rfcs/blob/main/features/0031-discover-features/README.md)           | :white_check_mark:        | Rarely (never?) used, and in implementing the V2 version of the protocol, the V1 version was found to be incomplete and was updated as part of Release 0.7.3  |
| [0028-introduce](https://github.com/decentralized-identity/aries-rfcs/blob/main/features/0028-introduce/README.md)            | :white_check_mark:        |      |
| [00509-action-menu](https://github.com/decentralized-identity/aries-rfcs/blob/main/features/0509-action-menu/README.md)       | :white_check_mark:        |      |
