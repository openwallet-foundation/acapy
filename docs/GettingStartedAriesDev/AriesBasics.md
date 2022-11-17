# What is Aries?

[Hyperledger Aries](https://www.hyperledger.org/projects/aries) provides a shared, reusable, interoperable tool kit designed for initiatives and solutions focused on creating, transmitting and storing verifiable digital credentials. It is infrastructure for blockchain-rooted, peer-to-peer interactions. It includes a shared cryptographic wallet for blockchain clients as well as a communications protocol for allowing off-ledger interaction between those clients.  

A Hyperledger Aries agent (such as the one in this repository):

* enables establishing connections with other DIDComm-based agents (using DIDComm encryption envelopes),
* exchanges messages between connected agents to execute message protocols (using DIDComm protocols)
* sends notifications about protocol events to a controller, and
* exposes an API for responses from the controller with direction in handling protocol events.

The concepts and features that make up the Aries project are documented in the [aries-rfcs](https://github.com/hyperledger/aries-rfcs) - but **don't** dive in there yet! We'll get to the features and concepts to be found there with a guided tour of the key RFCs. The [Aries Working Group](https://wiki.hyperledger.org/display/ARIES/Aries+Working+Group) meets weekly to expand the design and components of Aries.

The Aries Cloud Agent Python currently only supports Hyperledger Indy-based verifiable credentials and public ledger. Longer term (as we'll see later in this guide) protocols will be extended or added to support other verifiable credential implementations and public ledgers.

> Back to the [Aries Developer - Getting Started Guide](README.md).