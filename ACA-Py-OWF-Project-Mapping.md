# OWF Project Mapping: ACA-Py<!-- omit in toc -->

> **Note to reviewers:** This document follows the [OpenWallet Foundation Project Mapping] (OPM) template. Where information already exists in the ACA-Py repository or documentation site, this document provides a short summary and links rather than duplicating content. The authoritative source is always the linked document.

[OpenWallet Foundation Project Mapping]: https://github.com/openwallet-foundation/architecture-sig/blob/main/docs/papers/architecture-whitepaper.md#openwallet-foundation-project-maps

- [OPM01: The Basics](#opm01-the-basics)
- [OPM02: What License Does Your Project Use?](#opm02-what-license-does-your-project-use)
- [OPM03: How Do You Publish Your Work?](#opm03-how-do-you-publish-your-work)
- [OPM04: Visualisation Map](#opm04-visualisation-map)
- [OPM06: Dependency Checklist](#opm06-dependency-checklist)
- [OPM07: Use Cases](#opm07-use-cases)
- [OPM08: Ecosystems](#opm08-ecosystems)
- [OPM09: Project Roadmap](#opm09-project-roadmap)
- [OPM10: How Do I Build ACA-Py on Linux?](#opm10-how-do-i-build-aca-py-on-linux)
- [OPM11: How Do I Build ACA-Py on macOS?](#opm11-how-do-i-build-aca-py-on-macos)
- [OPM12: How Do I Build ACA-Py for iOS?](#opm12-how-do-i-build-aca-py-for-ios)
- [OPM13: How Do I Build ACA-Py for Android?](#opm13-how-do-i-build-aca-py-for-android)
- [OPM14: How Do I Build ACA-Py on Windows?](#opm14-how-do-i-build-aca-py-on-windows)
- [OPM15: How Do I Run ACA-Py?](#opm15-how-do-i-run-aca-py)
- [OPM16: Component Resource Demand](#opm16-component-resource-demand)
- [OPM17: Project Interoperability](#opm17-project-interoperability)
  - [OWF Projects](#owf-projects)
  - [Other Projects and Standards Bodies](#other-projects-and-standards-bodies)
- [OPM18: What Is Missing or Out-of-Date?](#opm18-what-is-missing-or-out-of-date)
- [OPM19: Standards](#opm19-standards)
- [OPM20: Testing Strategy](#opm20-testing-strategy)
- [OPM21: Threat Modelling and Incident Handling](#opm21-threat-modelling-and-incident-handling)
- [OPM22: Security Track Record](#opm22-security-track-record)
- [OPM23: Version Control](#opm23-version-control)
- [OPM24: Release Management and Support](#opm24-release-management-and-support)
- [OPM25: Experience Layer](#opm25-experience-layer)
- [OPM26: Gaps to Fill](#opm26-gaps-to-fill)
- [OPM27: Documentation](#opm27-documentation)
- [OPM28: Issues on GitHub / Good First Tickets](#opm28-issues-on-github--good-first-tickets)
- [OPM29: Adoption Support](#opm29-adoption-support)
- [OPM30: Contributor Guide](#opm30-contributor-guide)
- [OPM31: Adoption Strategy](#opm31-adoption-strategy)
- [OPM32: Adopters Index](#opm32-adopters-index)

## OPM01: The Basics

| Item | Details |
| :--- | :--- |
| **What is your project?** | ACA-Py (Adaptive Cloud Agent – Python) is a production-ready, open-source framework for building non-mobile decentralized trust services — verifiable credential issuers, holders, and verifiers — using any language capable of sending and receiving HTTP requests. It is maintained at the OpenWallet Foundation. See the [README](https://github.com/openwallet-foundation/acapy/blob/main/README.md) for a full description. |
| **GitHub location** | [https://github.com/openwallet-foundation/acapy](https://github.com/openwallet-foundation/acapy) |
| **Documentation Site** | [https://aca-py.org](https://aca-py.org) |
| **Current version** | 1.6.0 (latest release). Active LTS branches: `1.6` and `1.3`. See [GitHub Releases](https://github.com/openwallet-foundation/acapy/releases) for release notes. |
| **Where did the project originate?** | ACA-Py began as *Aries Cloud Agent – Python*, initiated by the Government of British Columbia's Digital Trust Team, circa 2017. An initial version was developed and iterated on for approximately 18 months, after which the codebase was restarted from scratch to produce the clean, plugin-friendly architecture that forms the current core. The project was originally hosted under the Hyperledger organization (as `hyperledger/aries-cloudagent-python`). In 2024 it moved to the [OpenWallet Foundation] (OWF) as `openwallet-foundation/acapy`, with release 1.1.0 being the first release from OWF. The move is documented in the [CHANGELOG](https://github.com/openwallet-foundation/acapy/blob/main/CHANGELOG.md). |
| **How old is the project?** | The project has been in active development since approximately 2019. It joined the OpenWallet Foundation in 2024. |

[OpenWallet Foundation]: https://www.openwallet.foundation/

## OPM02: What License Does Your Project Use?

| License | Notes |
| :--- | :--- |
| [Apache License 2.0](https://github.com/openwallet-foundation/acapy/blob/main/LICENSE) | This is the license for the ACA-Py core repository, consistent with OWF standard preferences. Third-party dependencies may carry their own compatible open-source licenses; the dependency checklist maintained by the OWF Project Mapping group covers these in detail. |

## OPM03: How Do You Publish Your Work?

| Location | What is published there |
| :--- | :--- |
| [GitHub – openwallet-foundation/acapy](https://github.com/openwallet-foundation/acapy) | Source code, releases, issues, discussions, and all in-repo documentation. Published under the OWF organization. |
| [PyPI – acapy-agent](https://pypi.org/project/acapy-agent/) | Python package releases. Published under the OWF organization. |
| [GitHub Container Registry](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent) | Docker images, including LTS-tagged images (`py3.12-1.3-lts`, `py3.12-1.6-lts`). Published under the OWF organization. |
| [aca-py.org](https://aca-py.org) | Organised documentation site aggregating all markdown docs from the repo. Published as OWF. |
| [OWF Discord – #aca-py channel](https://discord.gg/openwalletfoundation) | Community support and announcements. |
| [GitHub – openwallet-foundation/acapy-plugins](https://github.com/openwallet-foundation/acapy-plugins) | Maintained plugin repository with companion documentation at [plugins.aca-py.org](https://plugins.aca-py.org). Published as OWF. |

## OPM04: Visualisation Map

*Managed by the OWF Project Mapping group. No action required from the project at this time.*

## OPM06: Dependency Checklist

*Managed by the OWF Project Mapping group. Maintainers should notify the group when a major release is made so the dependency check can be refreshed.*

## OPM07: Use Cases

ACA-Py is a general-purpose agent framework and can be used in a wide-variety of
domains. The following verticals represent some of the areas where ACA-Py has
been deployed or is being actively used:

| Use Case | Notes |
| :--- | :--- |
| Government credentials | Digital identity documents, licences, permits, and benefit entitlements issued by government agencies as verifiable credentials. |
| Education credentials | Academic transcripts, diplomas, and professional certifications issued by educational institutions. |
| Supply chain | Provenance and compliance attestations for goods and materials moving through supply chains. |
| Healthcare | Patient credentials, professional licences, and vaccination records as privacy-preserving verifiable credentials. |

## OPM08: Ecosystems

ACA-Py has been deployed across a range of jurisdictions and ecosystems. A formal `ADOPTERS.md` is in progress (see OPM32). Known deployment contexts include Canada, the European Union, the US, South Africa, and various international digital identity initiatives, but a curated, permission-cleared list is not yet available.

## OPM09: Project Roadmap

**History**

See OPM01 for the full project history. In brief: ACA-Py originated as *Aries Cloud Agent – Python* at the Government of British Columbia, went through an early prototype phase (~18 months), was restarted on the architecture that exists today, evolved for several years under Hyperledger, and moved to the OpenWallet Foundation in 2024.

**Current direction**

There is not a formal published roadmap document at this time. Current priorities are:

- **Reducing Indy coupling** — pushing Hyperledger Indy-specific functionality out of the core and into a plugin, on equal footing with other verifiable data registry integrations. This makes ACA-Py a more general-purpose framework rather than an Indy-centric one.
- **Extensibility** — continued investment in making it straightforward to adopt new technology stacks and credential formats via the plugin architecture.

**Longer term**

Ongoing alignment with emerging standards (see OPM19) and continued expansion of the plugin ecosystem to support new credential formats and exchange protocols.

## OPM10: How Do I Build ACA-Py on Linux?

See the [Developer README](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md) and the [Getting Started Guide](https://github.com/openwallet-foundation/acapy/blob/main/docs/gettingStarted/README.md) on [aca-py.org](https://aca-py.org) for full build and installation instructions on Linux, including prerequisites (Python 3.12, pip, optional Docker). The recommended approach for most developers is to use Docker, which abstracts away platform-specific differences and provides a consistent environment. For those who prefer to build from source, the Developer README includes detailed instructions for setting up a Python virtual environment and installing dependencies. AFAWK, most production deployments are also on container orchestrated Linux environments for horizontal scaling, so Docker is also the most common path to production.

## OPM11: How Do I Build ACA-Py on macOS?

The same instructions as Linux apply. See the [Developer README](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md) and [Getting Started Guide](https://github.com/openwallet-foundation/acapy/blob/main/docs/gettingStarted/README.md). macOS users should be aware of platform-specific differences in Python environment management (e.g. using `brew` or `pyenv`).

## OPM12: How Do I Build ACA-Py for iOS?

Not Applicable: ACA-Py is a server-side (non-mobile) framework and is not intended for deployment on iOS. Mobile wallet implementations that communicate with ACA-Py agents typically use purpose-built mobile frameworks (e.g. [Credo-TS](https://github.com/openwallet-foundation/credo-ts) or [Bifold Wallet](https://github.com/openwallet-foundation/bifold-wallet)).

## OPM13: How Do I Build ACA-Py for Android?

Not Applicable: ACA-Py is a server-side (non-mobile) framework and is not intended for deployment on Android. See OPM12 for notes on mobile wallet frameworks that can interact with ACA-Py.

## OPM14: How Do I Build ACA-Py on Windows?

The [Developer README](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md) covers Windows. The recommended approach for Windows users is to use Docker or WSL2 (Windows Subsystem for Linux), as the primary development platform, and the production target is typically Linux.

## OPM15: How Do I Run ACA-Py?

ACA-Py can be run as a Python package (`pip install acapy-agent`) or via Docker. Published Docker images are available on the [GitHub Container Registry](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent), including LTS-tagged images. Configuration options are plentiful (set by environment variables or command-line arguments) and are documented in the [Developer README](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md). Further, a given environment is likely to use several ACA-Py plugins, each with their own configuration options — these are documented in the [acapy-plugins](https://github.com/openwallet-foundation/acapy-plugins) repository.

Full runtime documentation — configuration options, startup arguments, multi-tenant operation, and more — is available at [aca-py.org](https://aca-py.org) and in the [Developer README](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md).

ACA-Py has been deployed on hardware ranging from Raspberry Pi devices to large-scale data-centre servers.

## OPM16: Component Resource Demand

No formal benchmarks or sizing guidelines have been published at this time. ACA-Py has demonstrated a wide deployment range — from low-power single-board computers (e.g. Raspberry Pi) to horizontally-scaled cloud deployments. Detailed benchmarking is identified as a future area of work.

## OPM17: Project Interoperability

### OWF Projects

| Project | How ACA-Py interacts |
| :--- | :--- |
| [acapy-plugins](https://github.com/openwallet-foundation/acapy-plugins) | The official OWF-maintained plugin repository. Plugins extend ACA-Py with additional credential formats, protocols, and integrations. See [plugins.aca-py.org](https://plugins.aca-py.org). |
| [acapy-vc-authn-oidc](https://github.com/openwallet-foundation/acapy-vc-authn-oidc) | An OWF project that acts as an OpenID Connect identity provider backed by ACA-Py. It allows existing OIDC-compatible applications to authenticate users via verifiable credential presentation — without those applications needing to implement VC interactions directly. The OP acts as the ACA-Py verifier, requests a credential presentation (via QR code or deep-link to a mobile identity wallet), and maps the result back to a standard OIDC ID token returned to the relying party. |
| [askar](https://github.com/openwallet-foundation/askar) | ACA-Py's default secure storage and key management backend. Askar provides encrypted-at-rest storage (backed by SQLite or PostgreSQL) and cryptographic key management. It is a Rust implementation with a Python wrapper used directly by ACA-Py, and supersedes the legacy Indy SDK wallet. Migration tooling for upgrading from Indy SDK storage to Askar is available in acapy-tools. |
| [Credo-TS](https://github.com/openwallet-foundation/credo-ts) | A TypeScript agent framework. ACA-Py and Credo-TS agents are interoperable where both implement the same credential formats (W3C VCDM, SD-JWTs, AnonCreds, mDL/mDocs) and exchange protocols (DIDComm, OpenID4VCs, mDL). |
| [Bifold Wallet](https://github.com/openwallet-foundation/bifold-wallet) | A mobile wallet built on Credo-TS that communicates with ACA-Py agents using DIDComm and standard credential protocols. |

### Other Projects and Standards Bodies

| Project / Standard | How ACA-Py interacts |
| :--- | :--- |
| [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/) | ACA-Py issues, holds, and verifies W3C VCs in core and via plugins. |
| [W3C Decentralized Identifiers (DIDs) v1.0](https://www.w3.org/TR/did-1.0/) | ACA-Py resolves and registers DIDs across multiple DID methods via its pluggable resolver and registrar interfaces. |
| [DIDComm v1](https://identity.foundation/didcomm-messaging/spec/) | ACA-Py uses DIDComm v1 as its primary agent-to-agent messaging envelope for all credential exchange protocols. Support for DIDComm v2 has started, but is incomplete. |
| [AnonCreds](https://hyperledger.github.io/anoncreds-spec/) | ACA-Py implements AnonCreds issuance, presentation, and revocation natively; this support is being migrated to a plugin to reduce core coupling. |
| [OpenID for Verifiable Credentials (OID4VC / OID4VP)](https://openid.net/sg/openid4vc/specifications/) | ACA-Py supports OID4VCI and OID4VP credential issuance and presentation flows via plugins — see [plugins.aca-py.org](https://plugins.aca-py.org). |
| [SD-JWT VC](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) | ACA-Py issues and verifies SD-JWT-based verifiable credentials via plugins. |
| [ISO/IEC 18013-5 mDL / mdoc](https://www.iso.org/standard/69084.html) | ACA-Py supports issuance and verification of ISO mdoc/mDL credentials via the `mso_mdoc` module in the `oid4vc` plugin — see [plugins.aca-py.org](https://plugins.aca-py.org). |
| [Traction](https://github.com/bcgov/traction) | A multi-tenant ACA-Py implementation with an admin UI built by the BC Government, enabling multiple controllers (e.g., business areas) to share a common ACA-Py instance. |
| [Hyperledger Indy](https://www.lfdecentralizedtrust.org/projects/hyperledger-indy) | ACA-Py currently includes native support for Indy ledgers and AnonCreds credentials. This is being progressively moved into a plugin to reduce core coupling. |
| [DIDComm AIP 2.0](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md) | ACA-Py implements the Aries Interop Profile 2.0 suite of DIDComm protocols. Full details in [SupportedRFCs.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md). |
| [Hedera / Hiero](https://plugins.aca-py.org/latest/hedera/) | ACA-Py supports the Hedera network as a Verifiable Data Registry via the `hedera` plugin in the OWF acapy-plugins repo. The plugin implements `did:hedera` resolution and registration, and AnonCreds object storage on the Hedera Consensus Service (HCS), providing an enterprise-grade alternative VDR to Hyperledger Indy. |
| [cheqd](https://docs.cheqd.io/product/sdk/aca-py) | ACA-Py supports `did:cheqd` and DID-Linked Resources via a cheqd plugin. The plugin integrates with the cheqd network for DID registration (via the Universal Registrar), AnonCreds object methods, and W3C credential workflows, enabling ACA-Py deployments to use cheqd as a VDR alongside or instead of Indy. |

## OPM18: What Is Missing or Out-of-Date?

| Item | Status |
| :--- | :--- |
| `ADOPTERS.md` | Does not yet exist. In progress — requires permission from known adopters before names can be published. |
| Formal roadmap document | Not yet published. Current direction is captured in OPM09 above. |
| Performance benchmarks | No published benchmarks. Identified as future work. |
| Indy decoupling | Partially complete. Indy-specific code is progressively being moved into a plugin as the core generalises to support multiple verifiable data registries. |

## OPM19: Standards

The following table summarises key standards relevant to ACA-Py. The [SupportedRFCs.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md) document is the authoritative reference for DIDComm protocol support. Additional standard support is delivered via the [acapy-plugins](https://github.com/openwallet-foundation/acapy-plugins) repository.

| Standard | Status |
| :--- | :--- |
| [Aries Interop Profile (AIP) 2.0](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md) | Compliant — see SupportedRFCs.md for detail |
| [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/) | Supported (via core and plugins) |
| [W3C Decentralized Identifiers (DIDs) v1.0](https://www.w3.org/TR/did-1.0/) | Supported for multiple DID methods |
| [DIDComm v1](https://identity.foundation/didcomm-messaging/spec/) | Supported |
| [AnonCreds](https://hyperledger.github.io/anoncreds-spec/) | Supported (natively; migration to plugin in progress) |
| [OpenID4VCs (OID4VC / OID4VP)](https://openid.net/sg/openid4vc/specifications/) | Supported via plugins — see [plugins.aca-py.org](https://plugins.aca-py.org) |
| [SD-JWT VC](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) | Supported via plugins |
| [ISO/IEC 18013-5 mDL / mdoc](https://www.iso.org/standard/69084.html) | Supported via the `mso_mdoc` module in the `oid4vc` plugin — see [plugins.aca-py.org](https://plugins.aca-py.org) |

## OPM20: Testing Strategy

| Area | Approach |
| :--- | :--- |
| **Unit tests** | Extensive unit test suite included in the core repository, run on every pull request via GitHub Actions. |
| **Integration tests** | Integration tests run against real or simulated ledgers and agent-to-agent scenarios. |
| **Interoperability** | ACA-Py participates in interoperability testing with other DIDComm-compatible agents via the OWF [OWL Agent Test Harness](https://github.com/openwallet-foundation/owl-agent-test-harness). |
| **Security** | Dependency scanning and vulnerability reporting via GitHub security advisories (see OPM21/22). Dependency updates are continuously raised as pull requests by Dependabot, tested via the CI pipeline, and merged by maintainers. |
| **Regression** | All PRs must pass the full CI pipeline before merging. LTS branches receive targeted regression testing for patch releases. |
| **End-to-end** | Demo scenarios (see [demo/README.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/demo/README.md)) provide end-to-end validation of common workflows. |
| **Certification** | No formal external certification at this time. |
| **Load testing** | A load testing capability is available via [OWL Akrida](https://github.com/openwallet-foundation/owl-akrida), an OWF project that uses Locust to generate DIDComm-based load against ACA-Py deployments. |

## OPM21: Threat Modelling and Incident Handling

| Item | Details |
| :--- | :--- |
| **Threat modelling** | No formal published threat model document exists at this time. |
| **Incident / vulnerability reporting** | Vulnerabilities should be reported via GitHub Security Advisories: open a new draft security advisory from the [Security Advisories tab](https://github.com/openwallet-foundation/acapy/security/advisories) of the ACA-Py repository. Full details are in [SECURITY.md](https://github.com/openwallet-foundation/acapy/blob/main/SECURITY.md). |
| **Security team** | The security team consists of at least three project Maintainers. Team composition is managed via the OWF governance repo's `access-control.yaml`. See [SECURITY.md](https://github.com/openwallet-foundation/acapy/blob/main/SECURITY.md). |
| **Recovery** | Patch releases on supported branches (including LTS) are issued to address confirmed vulnerabilities. Communication is via GitHub releases and the OWF Discord. |

## OPM22: Security Track Record

| Item | Details |
| :--- | :--- |
| **Past CVEs** | Security advisories are tracked via [GitHub Security Advisories](https://github.com/openwallet-foundation/acapy/security/advisories). |
| **Policy and process** | Documented in [SECURITY.md](https://github.com/openwallet-foundation/acapy/blob/main/SECURITY.md), which covers reporting channels, triage process, disclosure timelines, and maintainer responsibilities. |

## OPM23: Version Control

ACA-Py uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

| Version change | Meaning |
| :--- | :--- |
| MAJOR (e.g. 1.x → 2.0) | Breaking changes requiring migration steps. Migration guidance is included in the CHANGELOG. |
| MINOR (e.g. 1.5 → 1.6) | New features or significant changes, backwards compatible unless noted in the Breaking Changes section of the CHANGELOG. |
| PATCH (e.g. 1.6.0 → 1.6.1) | Bug fixes and security patches. LTS patch releases are guaranteed to deploy without an upgrade process from the prior patch release. |

## OPM24: Release Management and Support

| Item | Details |
| :--- | :--- |
| **LTS releases** | LTS branches (`1.3`, `1.6`) receive ongoing patch releases. Docker images are published with `-lts` tags that are kept current with the latest patch on each LTS branch (e.g. `py3.12-1.6-lts`). LTS patch releases are backwards compatible with no upgrade steps required. |
| **Release cadence** | No fixed schedule; releases are driven by feature readiness and community need. See the [GitHub Releases page](https://github.com/openwallet-foundation/acapy/releases) for recent history. |
| **Communication** | New releases are announced via GitHub Releases (with release notes in the CHANGELOG), and via the `#aca-py` channel on OWF Discord. |
| **Semantic versioning** | Yes — see OPM23. |

Releases are tagged in GitHub and documented in the [CHANGELOG](https://github.com/openwallet-foundation/acapy/blob/main/CHANGELOG.md). The full release publishing process — including tagging, generating release notes, publishing to PyPI, and the automatic triggering of Docker image builds to GHCR — is documented in [PUBLISHING.md](https://aca-py.org/latest/PUBLISHING/).

The [acapy-plugins](https://github.com/openwallet-foundation/acapy-plugins) repository maintains version alignment with ACA-Py core via a CI/CD release pipeline. When a new ACA-Py version is released, the pipeline automatically updates each plugin's ACA-Py dependency, runs the plugin test suites, and identifies which plugins have successfully passed against the new version. This ensures that the maintained plugins in the OWF plugin repository stay in sync with each ACA-Py release.

## OPM25: Experience Layer

ACA-Py is a backend (headless) agent framework. It exposes an HTTP Admin API that a controller application uses to drive agent behaviour. There is no bundled UI.

[Traction](https://github.com/bcgov/traction) is a well-known open-source example of a controller built on top of ACA-Py: it provides an admin UI for a multi-tenant ACA-Py deployment and was developed by the BC Government's Digital Trust Team. Traction illustrates the typical pattern for adding an experience layer on top of ACA-Py.

## OPM26: Gaps to Fill

| Gap | Notes |
| :--- | :--- |
| **Indy decoupling (self)** | Moving Indy-specific code from the core into a plugin is in progress. This is a multi-release effort. |
| **Adopters list (self)** | An `ADOPTERS.md` needs to be created and populated with permission from known adopters. |
| **Formal roadmap (self)** | A published roadmap document would help the community understand project direction. |
| **Benchmark / sizing guidance (self)** | Deployment sizing guidance would be valuable for new adopters. |
| **Broader DID method support (ecosystem)** | Continued community contributions for additional DID methods and verifiable data registries via the plugin model. |

## OPM27: Documentation

ACA-Py documentation is maintained in the repository as Markdown files and published at [aca-py.org](https://aca-py.org).

| Resource | Link |
| :--- | :--- |
| Main documentation site | [https://aca-py.org](https://aca-py.org) |
| Getting Started Guide | [docs/gettingStarted/README.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/gettingStarted/README.md) |
| Developer README | [docs/features/DevReadMe.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/DevReadMe.md) |
| Supported RFCs / Protocols | [docs/features/SupportedRFCs.md](https://github.com/openwallet-foundation/acapy/blob/main/docs/features/SupportedRFCs.md) |
| Plugin documentation | [https://plugins.aca-py.org](https://plugins.aca-py.org) |
| CHANGELOG | [CHANGELOG.md](https://github.com/openwallet-foundation/acapy/blob/main/CHANGELOG.md) |

## OPM28: Issues on GitHub / Good First Tickets

| Item | Details |
| :--- | :--- |
| **Issue tracker** | [https://github.com/openwallet-foundation/acapy/issues](https://github.com/openwallet-foundation/acapy/issues) |
| **Good First Issue label** | Issues labelled [`help wanted`](https://github.com/openwallet-foundation/acapy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) are suitable entry points for new contributors who do not yet have deep ACA-Py knowledge. |

## OPM29: Adoption Support

| Audience | Support channel |
| :--- | :--- |
| **Developers building on ACA-Py** | [OWF Discord – #aca-py](https://discord.gg/openwalletfoundation): questions, troubleshooting, and community discussion. |
| **All users** | [GitHub Discussions](https://github.com/openwallet-foundation/acapy/discussions): longer-form questions and design conversations. |
| **Bug reports / issues** | [GitHub Issues](https://github.com/openwallet-foundation/acapy/issues) |
| **Security issues** | [GitHub Security Advisories](https://github.com/openwallet-foundation/acapy/security/advisories) — do not use public issue tracker for security bugs. |

ACA-Py is designed for developers and architects building decentralised identity services. The primary audience is engineering teams deploying issuer, holder, or verifier services.

## OPM30: Contributor Guide

| Resource | Link |
| :--- | :--- |
| **Contributing guide** | [CONTRIBUTING.md](https://github.com/openwallet-foundation/acapy/blob/main/CONTRIBUTING.md) |
| **Maintainers guide** | [MAINTAINERS.md](https://github.com/openwallet-foundation/acapy/blob/main/MAINTAINERS.md) |

Contributions are welcome in all forms: bug fixes, new features, documentation improvements, plugin development, and test coverage. The maintainer community actively reviews pull requests. Contributors who make a sustained and significant impact are encouraged to become Maintainers — the path to doing so is described in [MAINTAINERS.md](https://github.com/openwallet-foundation/acapy/blob/main/MAINTAINERS.md).

## OPM31: Adoption Strategy

ACA-Py lowers the barrier to building decentralised identity services by providing:

- A stable, production-proven Python framework deployable via `pip` or Docker.
- Extensive documentation at [aca-py.org](https://aca-py.org).
- A demo environment and sample controllers that new users can run immediately.
- A plugin model so that adopters can extend ACA-Py without forking the core.
- LTS releases that give deployers a stable, long-term supported target.
- An active community on OWF Discord for peer support.

The project does not have a formal written adoption strategy document, but these mechanisms collectively reduce friction for new adopters.

## OPM32: Adopters Index

An `ADOPTERS.md` file does not yet exist in the repository. ACA-Py is known to be in production use across multiple organisations and jurisdictions globally, including government digital identity programmes in Canada and elsewhere. Populating this list requires obtaining explicit permission from each adopter. Contributions and nominations are welcome via a pull request or GitHub Discussion once the file is created.

*This document is maintained in the ACA-Py repository. For corrections or additions, please open a pull request or GitHub Issue.*