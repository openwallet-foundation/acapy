# ACA-Py -- A Cloud Agent - Python  <!-- omit in toc -->

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
[![PyPI version](https://img.shields.io/pypi/v/acapy-agent)](https://pypi.org/project/acapy-agent/)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=openwallet-foundation_acapy&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=openwallet-foundation_acapy)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=openwallet-foundation_acapy&metric=coverage)](https://sonarcloud.io/summary/new_code?id=openwallet-foundation_acapy)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=openwallet-foundation_acapy&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=openwallet-foundation_acapy)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=openwallet-foundation_acapy&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=openwallet-foundation_acapy)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/openwallet-foundation/acapy/badge)](https://scorecard.dev/viewer/?uri=github.com/openwallet-foundation/acapy)

> **ACA-Py is now part of the [OpenWallet Foundation](https://openwallet.foundation/) (OWF)!**

The move of ACA-Py to the OWF is now complete. If you haven't done so already, please update your ACA-Py deployment to use:

- the [ACA-Py OWF repository](https://github.com/openwallet-foundation/acapy),
- the new [acapy-agent in PyPi](https://pypi.org/project/acapy-agent/), and
- the container images for ACA-Py hosted by the OpenWallet Foundation GitHub organization within the GitHub Container Repository (GHCR).

___

ACA-Py is an easy to use enterprise SSI agent for building decentralized trust services using any language that supports sending/receiving HTTP requests.

Full access to an organized set of all of the ACA-Py documents is available at [https://aca-py.org](https://aca-py.org).
Check it out! It's much easier to navigate than the ACA-Py GitHub repo for reading the documentation.

:new: ACA-Py Plugins have their own store! Visit [https://plugins.aca-py.org](https://plugins.aca-py.org) to find ready-to-use functionality to add to your ACA-Py deployment, and to learn how to build your own plugins.

## Overview

ACA-Py is a foundation for building Verifiable Credential (VC) ecosystems. It operates in the second and third layers of the [Trust Over IP framework (PDF)](https://trustoverip.org/wp-content/uploads/2020/05/toip_050520_primer.pdf) using a variety of verifiable credential formats and protocols. ACA-Py runs on servers (cloud, enterprise, IoT devices, and so forth), and is not designed to run on mobile devices.

ACA-Py includes support for the concepts and features that make up [Aries Interop Profile (AIP) 2.0](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-20). [ACA-Py’s supported features](./docs/features/SupportedRFCs.md) include, most importantly, protocols for issuing, verifying, and holding verifiable credentials using both [Hyperledger AnonCreds] verifiable credential format, and the [W3C Standard Verifiable Credential Data Model] format using JSON-LD with LD-Signatures and BBS+ Signatures. Coming soon -- issuing and presenting [Hyperledger AnonCreds] verifiable credentials using the [W3C Standard Verifiable Credential Data Model] format.

[Hyperledger AnonCreds]: https://www.hyperledger.org/use/anoncreds
[W3C Standard Verifiable Credential Data Model]: https://www.w3.org/TR/vc-data-model/

To use ACA-Py you create a business logic "controller" that talks to an ACA-Py instance (sending HTTP requests and receiving webhook notifications), and ACA-Py handles the various protocols and related functionality. Your controller can be built in any language that supports making and receiving HTTP requests; knowledge of Python is not needed. Together, this means you can focus on building VC solutions using familiar web development technologies, instead of having to learn the nuts and bolts of low-level cryptography and Trust over IP-type protocols.

This [checklist-style overview document](./docs/features/SupportedRFCs.md) provides a full list of the features in ACA-Py.
The following is a list of some of the core features needed for a production deployment, with a link to detailed information about the capability.

## LTS Releases

The ACA-Py community provides periodic releases with new features and
improvements. Certain releases are designated by the ACA-Py maintainers as
long-term support (LTS) releases and listed in this document. Critical bugs and
important (as determined by the ACA-Py Maintainers) fixes are backported to
the active LTS releases. Each LTS release will be supported with patches for **9
months** following the designation of the **next** LTS Release. For more details see
the [LTS strategy](./LTS-Strategy.md).

Current LTS releases:

- Release [1.2](https://github.com/openwallet-foundation/acapy/releases/tag/1.2.4) **Current LTS Release**
- Release [0.12](https://github.com/openwallet-foundation/acapy/releases/tag/0.12.6) **End of Life: October 2025**

Past LTS releases:

- Release [0.11](https://github.com/openwallet-foundation/acapy/releases/tag/0.11.3) **End of Life: January 2025**

Unless specified in the **Breaking Changes** section of the ACA-Py
[CHANGELOG](./CHANGELOG.md), all LTS patch releases will be able to be deployed
**without** an upgrade process from its prior release. Minor/Major release upgrades
steps (if any) of ACA-Py are tested and documented in the ACA-Py
[CHANGELOG](./CHANGELOG.md) per release and in the project documents published
at [https://aca-py.org](https://aca-py.org) from the markdown files in this
repository.

ACA-Py releases and release notes can be found on the [GitHub releases
page](https://github.com/openwallet-foundation/acapy/releases).

### Multi-Tenant

ACA-Py supports "multi-tenant" scenarios. In these scenarios, one (scalable) instance of ACA-Py uses one database instance, and are together capable of managing separate secure storage (for private keys, DIDs, credentials, etc.) for many different actors. This enables (for example) an "issuer-as-a-service", where an enterprise may have many VC issuers, each with different identifiers, using the same instance of ACA-Py to interact with VC holders as required. Likewise, an ACA-Py instance could be a "cloud wallet" for many holders (e.g. people or organizations) that, for whatever reason, cannot use a mobile device for a wallet. Learn more about multi-tenant deployments [here](./docs/features/Multitenancy.md).

### Mediator Service

Startup options allow the use of an ACA-Py as a DIDComm [mediator](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0046-mediators-and-relays#summary) using core DIDComm protocols to coordinate its mediation role. Such an ACA-Py instance receives, stores and forwards messages to DIDComm agents that (for example) lack an addressable endpoint on the Internet such as a mobile wallet. A live instance of a public mediator based on ACA-Py is available [here](https://indicio-tech.github.io/mediator/) from [Indicio, PBC](https://indicio.tech). Learn more about deploying a mediator [here](./docs/features/Mediation.md). See the [Aries Mediator Service](https://github.com/hyperledger/aries-mediator-service) for a "best practices" configuration of an Aries mediator.

### Indy Transaction Endorsing

ACA-Py supports a Transaction Endorsement protocol, for agents that don't have write access to an Indy ledger.  Endorser support is documented [here](./docs/features/Endorser.md).

### Scaled Deployments

ACA-Py supports deployments in scaled environments such as in Kubernetes environments where ACA-Py and its storage components can be horizontally scaled as needed to handle the load.

### VC-API Endpoints

A set of endpoints conforming to the vc-api specification are included to manage w3c credentials and presentations. They are documented [here](./docs/features/JsonLdCredentials.md#vc-api) and a postman demo is available [here](./docs/features/JsonLdCredentials.md#vc-api).

## Example Uses

The business logic you use with ACA-Py is limited only by your imagination. Possible applications include:

- An interface to a legacy system to issue verifiable credentials
- An authentication service based on the presentation of verifiable credential proofs
- An enterprise wallet to hold and present verifiable credentials about that enterprise
- A user interface for a person to use a wallet not stored on a mobile device
- An application embedded in an IoT device, capable of issuing verifiable credentials about collected data
- A persistent connection to other agents that enables secure messaging and notifications
- Custom code to implement a new service.

## Getting Started

For those new to SSI, Wallets, and ACA-Py, there are a couple of Linux Foundation edX courses that provide a good starting point.

- [Identity in Hyperledger: Indy, Aries and Ursa](https://www.edx.org/course/identity-in-hyperledger-aries-indy-and-ursa)
- [Becoming a Hyperledger Aries Developer](https://www.edx.org/course/becoming-a-hyperledger-aries-developer)

The latter is the most useful for developers wanting to get a solid basis in using ACA-Py and other Aries Frameworks.

Also included here is a much more concise (but less maintained) [Getting Started Guide](./docs/gettingStarted/README.md) that will take you from knowing next to nothing about decentralized identity to developing Aries-based business apps and services. You’ll run an Indy ledger (with no ramp-up time), ACA-Py apps and developer-oriented demos. The guide has a table of contents so you can skip the parts you already know.

### Understanding the Architecture

There is an [architectural deep dive webinar](https://www.youtube.com/watch?v=FXTQEtB4fto&feature=youtu.be) presented by the ACA-Py team, and [slides from the webinar](https://docs.google.com/presentation/d/1K7qiQkVi4n-lpJ3nUZY27OniUEM0c8HAIk4imCWCx5Q/edit#slide=id.g5d43fe05cc_0_77) are also available. The picture below gives a quick overview of the architecture, showing an instance of ACA-Py, a controller and the interfaces between the controller and ACA-Py, and the external paths to other agents and public ledgers on the Internet.

![drawing](./aca-py_architecture.png)

You can extend ACA-Py using plug-ins, which can be loaded at runtime.  Plug-ins are mentioned in the [webinar](https://docs.google.com/presentation/d/1K7qiQkVi4n-lpJ3nUZY27OniUEM0c8HAIk4imCWCx5Q/edit#slide=id.g5d43fe05cc_0_145) and are [described in more detail here](./docs/features/PlugIns.md). An ever-expanding set of ACA-Py plugins can be found
in the [ACA-Py Plugins repository]. Check them out -- it might already have the very plugin you need!

[ACA-Py Plugins repository]: https://plugins.aca-py.org

### Installation and Usage

Use the ["install and go" page for developers](./docs/features/DevReadMe.md) if you are comfortable with decentralized trust concepts. ACA-Py can be run with Docker without installation (highly recommended), or can be installed [from PyPi](https://pypi.org/project/acapy-agent/). In the repository `/demo` folder there is a full set of demos for developers to use in getting up to speed quickly. Start with the [Traction Workshop] to go through a complete ACA-Py-based Issuer-Holder-Verifier flow in about 20 minutes. Next, the [Alice-Faber Demo](./docs/demo/README.md) is a great way for developers try a zero-install example of how to use the ACA-Py API to operate a couple of Agents. The [Read the Docs](https://aries-cloud-agent-python.readthedocs.io/en/latest/) overview is also a way to understand the internal modules and APIs that make up an ACA-Py instance.

If you would like to develop on ACA-Py locally note that we use Poetry for dependency management and packaging. If you are unfamiliar with poetry please see our [cheat sheet](./docs/deploying/Poetry.md)

[Traction Workshop]: ./docs/demo/ACA-Py-Workshop.md

## About the ACA-Py Admin API

The [overview of ACA-Py’s API](./docs/features/AdminAPI.md) is a great starting place for learning about the ACA-Py API when you are starting to build your own controller.

An ACA-Py instance puts together an OpenAPI-documented REST interface based on the protocols that are loaded. This is used by a controller application (written in any language) to manage the behavior of the agent. The controller can initiate actions (e.g. issuing a credential) and can respond to agent events (e.g. sending a presentation request after a connection is accepted). Agent events are delivered to the controller as webhooks to a configured URL.

Technical note: the administrative API exposed by the agent for the controller to use must be protected with an API key (using the --admin-api-key command line arg) or deliberately left unsecured using the --admin-insecure-mode command line arg. The latter should not be used other than in development if the API is not otherwise secured.

## Troubleshooting

There are a number of resources for getting help with ACA-Py and troubleshooting
any problems you might run into. The
[Troubleshooting](./docs/testing/Troubleshooting.md) document contains some
guidance about issues that have been experienced in the past. Feel free to
submit PRs to supplement the troubleshooting document! Searching the [ACA-Py
GitHub issues](https://github.com/openwallet-foundation/acapy/issues)
may uncovers challenges you are having that others have experienced, often
with solutions. As well, there is the "aca-py"
channel on the OpenWallet Foundation Discord chat server ([invitation
here](https://discord.gg/openwalletfoundation)).

## Credit

The initial implementation of ACA-Py was developed by the Government of British Columbia’s Digital Trust Team in Canada. To learn more about what’s happening with decentralized identity and digital trust in British Columbia, checkout the [BC Digital Trust] website.

[BC Digital Trust]: https://digital.gov.bc.ca/digital-trust/

See the [MAINTAINERS.md](./MAINTAINERS.md) file for how to find a list of the current ACA-Py
maintainers, and guidelines for becoming a Maintainer. We'd love to have you
join the team if you are willing and able to carry out the [duties of a Maintainer](./MAINTAINERS.md#the-duties-of-a-maintainer).

## Contributing

Pull requests are welcome! Please read our [contributions guide](./CONTRIBUTING.md) and submit your PRs. We enforce [developer certificate of origin](https://developercertificate.org/) (DCO) commit signing — [guidance](https://github.com/apps/dco) on this is available. We also welcome issues submitted about problems you encounter in using ACA-Py.

## License

[Apache License Version 2.0](https://github.com/openwallet-foundation/acapy/blob/main/LICENSE)
