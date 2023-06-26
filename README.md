# Hyperledger Aries Cloud Agent - Python  <!-- omit in toc -->

[![pypi releases](https://img.shields.io/pypi/v/aries_cloudagent)](https://pypi.org/project/aries-cloudagent/)
[![codecov](https://codecov.io/gh/hyperledger/aries-cloudagent-python/branch/main/graph/badge.svg)](https://codecov.io/gh/hyperledger/aries-cloudagent-python)

<!-- ![logo](/doc/assets/aries-cloudagent-python-logo-bw.png) -->

> An easy to use Aries agent for building SSI services using any language that supports sending/receiving HTTP requests.

Full access to an organized set of all of the ACA-Py documents is available at [https://aca-py.org](https://aca-py.org).
Check it out! It's much easier to navigate then finding all the documentation here.

## Overview

Hyperledger Aries Cloud Agent Python (ACA-Py) is a foundation for building Verifiable Credential (VC) ecosystems. It operates in the second and third layers of the [Trust Over IP framework (PDF)](https://trustoverip.org/wp-content/uploads/2020/05/toip_050520_primer.pdf) using [DIDComm messaging](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0005-didcomm) and [Hyperledger Aries](https://www.hyperledger.org/use/aries) protocols. The "cloud" in the name means that ACA-Py runs on servers (cloud, enterprise, IoT devices, and so forth), and is not designed to run on mobile devices.

ACA-Py is built on the Aries concepts and features that make up [Aries Interop Profile (AIP) 1.0](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-10), and most of the features in [AIP 2.0](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-20). [ACA-Py’s supported Aries protocols](https://github.com/hyperledger/aries-cloudagent-python/blob/main/SupportedRFCs.md) include, most importantly, protocols for issuing, verifying, and holding verifiable credentials using both [Hyperledger AnonCreds](https://www.hyperledger.org/use/anoncreds) verifiable credential format, and the [W3C Standard Verifiable Credential](https://www.w3.org/TR/vc-data-model/) format using JSON-LD with LD-Signatures and BBS+ Signatures.

To use ACA-Py you create a business logic controller that "talks to" ACA-Py (sending HTTP requests and receiving webhook notifications), and ACA-Py handles the Aries and DIDComm functionality. That controller can be built in any language that supports making and receiving HTTP requests; knowledge of Python is not needed. Together, this means you can focus on building VC solutions using familiar web development technologies, instead of having to learn the nuts and bolts of low-level cryptography and Trust over IP-type Aries protocols.

This [checklist-style overview document](./SupportedRFCs.md) provides a full list of the features in ACA-Py.
The following is a list of some of the core features needed for a production deployment, with a link to detailed information about the capability.

### Multi-Tenant

ACA-Py supports "multi-tenant" scenarios. In these scenarios, one (scalable) instance of ACA-Py uses one database instance, and are together capable of managing separate secure storage (for private keys, DIDs, credentials, etc.) for many different actors. This enables (for example) an "issuer-as-a-service", where an enterprise may have many VC issuers, each with different identifiers, using the same instance of ACA-Py to interact with VC holders as required. Likewise, an ACA-Py instance could be a "cloud wallet" for many holders (e.g. people or organizations) that, for whatever reason, cannot use a mobile device for a wallet. Learn more about multi-tenant deployments [here](./Multitenancy.md).

### Mediator Service

Startup options allow the use of an ACA-Py as an Aries [mediator](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0046-mediators-and-relays#summary) using core Aries protocols to coordinate its mediation role. Such an ACA-Py instance receives, stores and forwards messages to Aries  agents that (for example) lack an addressable endpoint on the Internet such as a mobile wallet. A live instance of a public mediator based on ACA-Py is available [here](https://indicio-tech.github.io/mediator/) from Indicio Technologies. Learn more about deploying a mediator [here](./Mediation.md). See the [Aries Mediator Service](https://github.com/hyperledger/aries-mediator-service) for a "best practices" configuration of an Aries mediator.

### Indy Transaction Endorsing

ACA-Py supports a Transaction Endorsement protocol, for agents that don't have write access to an Indy ledger.  Endorser support is documented [here](Endorser.md).

### Scaled Deployments

ACA-Py supports deployments in scaled environments such as in Kubernetes environments where ACA-Py and its storage components can be horizontally scaled as needed to handle the load.

## Example Uses

The business logic you use with ACA-Py is limited only by your imagination. Possible applications include:

* An interface to a legacy system to issue verifiable credentials
* An authentication service based on the presentation of verifiable credential proofs
* An enterprise wallet to hold and present verifiable credentials about that enterprise
* A user interface for a person to use a wallet not stored on a mobile device
* An application embedded in an IoT device, capable of issuing verifiable credentials about collected data
* A persistent connection to other agents that enables secure messaging and notifications
* Custom code to implement a new service.

## Getting Started

For those new to SSI, Aries and ACA-Py, there are a couple of Linux Foundation edX courses that provide a good starting point.

* [Identity in Hyperledger: Indy, Aries and Ursa](https://www.edx.org/course/identity-in-hyperledger-aries-indy-and-ursa)
* [Becoming a Hyperledger Aries Developer](https://www.edx.org/course/becoming-a-hyperledger-aries-developer)

The latter is the most useful for developers wanting to get a solid basis in using ACA-Py and other Aries Frameworks.

Also included here is a much more concise (but less maintained) [Getting Started Guide](/docs/GettingStartedAriesDev/README.md) that will take you from knowing next to nothing about decentralized identity to developing Aries-based business apps and services. You’ll run some Indy apps, ACA-Py apps and developer-oriented demos. The guide has a table of contents so you can skip the parts you already know.

### Understanding the Architecture

There is an [architectural deep dive webinar](https://www.youtube.com/watch?v=FXTQEtB4fto&feature=youtu.be) presented by the ACA-Py team, and [slides from the webinar](https://docs.google.com/presentation/d/1K7qiQkVi4n-lpJ3nUZY27OniUEM0c8HAIk4imCWCx5Q/edit#slide=id.g5d43fe05cc_0_77) are also available. The picture below gives a quick overview of the architecture, showing an instance of ACA-Py, a controller and the interfaces between the controller and ACA-Py, and the external paths to other agents and public ledgers on the Internet.

![drawing](./aca-py_architecture.png)

You can extend Aca-Py using plug-ins, which can be loaded at runtime.  Plug-ins are mentioned in the [webinar](https://docs.google.com/presentation/d/1K7qiQkVi4n-lpJ3nUZY27OniUEM0c8HAIk4imCWCx5Q/edit#slide=id.g5d43fe05cc_0_145) and are [described in more detail here](/docs/GettingStartedAriesDev/PlugIns.md).

### Installation and Usage

An ["install and go" page for developers](https://github.com/hyperledger/aries-cloudagent-python/blob/main/DevReadMe.md) is available if you are comfortable with Trust over IP and Aries concepts. ACA-Py can be run with Docker without installation (highly recommended), or can be installed [from PyPi](https://pypi.org/project/aries-cloudagent/). In the [/demo directory](/demo) there is a full set of demos for developers to use in getting started, and the [demo read me](/demo/README.md) is a great starting point for developers to use an "in-browser" approach to run a zero-install example. The [Read the Docs](https://aries-cloud-agent-python.readthedocs.io/en/latest/) overview is also a way to reference the modules and APIs that make up an ACA-Py instance.

## About the ACA-Py Admin API

The [overview of ACA-Py’s API](https://github.com/hyperledger/aries-cloudagent-python/blob/main/AdminAPI.md) is a great starting place for learning about the ACA-Py API when you are starting to build your own controller.

An ACA-Py instance puts together an OpenAPI-documented REST interface based on the protocols that are loaded. This is used by a controller application (written in any language) to manage the behaviour of the agent. The controller can initiate actions (e.g. issuing a credential) and can respond to agent events (e.g. sending a presentation request after a connection is accepted). Agent events are delivered to the controller as webhooks to a configured URL.

Technical note: the administrative API exposed by the agent for the controller to use must be protected with an API key (using the --admin-api-key command line arg) or deliberately left unsecured using the --admin-insecure-mode command line arg. The latter should not be used other than in development if the API is not otherwise secured.

## Troubleshooting

There are a number of resources for getting help with ACA-Py and troubleshooting
any problems you might run into. The [Troubleshooting](Troubleshooting.md)
document contains some guidance about issues that have been experienced in the
past. Feel free to submit PRs to supplement the troubleshooting document!
Searching the [ACA-Py GitHub
issues](https://github.com/hyperledger/aries-cloudagent-python/issues) will
often uncover challenges that others have experienced, often with answers to
solving those challenges. As well, there is the "aries-cloudagent-python"
channel on the Hyperledger Discord chat server ([invitation
here](https://discord.gg/hyperledger)).

## Credit

The initial implementation of ACA-Py was developed by the Government of British Columbia’s Digital Trust Team in Canada. To learn more about what’s happening with decentralized identity and digital trust in British Columbia, checkout the [BC Digital Trust] website.

[BC Digital Trust]: https://digital.gov.bc.ca/digital-trust/

See the [MAINTAINERS.md](/Maintainers.md) file for a list of the current ACA-Py
maintainers, and the guidelines for becoming a Maintainer. We'd love to have you
join the team if you are willing and able to carry out the [duties of a
Maintainer](/MAINTAINERS.md#the-duties-of-a-maintainer).

## Contributing

Pull requests are welcome! Please read our [contributions guide](https://github.com/hyperledger/aries-cloudagent-python/blob/main/CONTRIBUTING.md) and submit your PRs. We enforce [developer certificate of origin](https://developercertificate.org/) (DCO) commit signing — [guidance](https://github.com/apps/dco) on this is available. We also welcome issues submitted about problems you encounter in using ACA-Py.

## License

[Apache License Version 2.0](https://github.com/hyperledger/aries-cloudagent-python/blob/main/LICENSE)
