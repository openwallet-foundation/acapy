# Hyperledger Indy Catalyst <!-- omit in toc -->

![logo](/docs/assets/indy-catalyst-logo-bw.png)

# Table of Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Decentralized Identity / Self-Sovereign Identity](#decentralized-identity--self-sovereign-identity)
  - [Open Standards](#open-standards)
    - [Decentralized Identifiers (DID)](#decentralized-identifiers-did)
    - [Verifiable Credentials](#verifiable-credentials)
    - [Links to Emerging DID and Verifiable Credentials Standards](#links-to-emerging-did-and-verifiable-credentials-standards)
      - [DID Standards](#did-standards)
      - [Verifiable Credentials Standards](#verifiable-credentials-standards)
  - [General Model](#general-model)
  - [Technology](#technology)
    - [Distributed Ledger Technology / Blockchain](#distributed-ledger-technology--blockchain)
    - [Decentralized Key Management Systems](#decentralized-key-management-systems)
    - [Zero Knowledge Proofs](#zero-knowledge-proofs)
  - [Summary: Decentralized Identity / Self-Sovereign Identity Architecture](#summary-decentralized-identity--self-sovereign-identity-architecture)
- [Hyperledger Indy](#hyperledger-indy)
  - [Overview](#overview)
  - [Technical information for Hyperledger Indy](#technical-information-for-hyperledger-indy)
- [Hyperledger Indy Catalyst](#hyperledger-indy-catalyst)
  - [Motivation](#motivation)
  - [Who is Indy Catalyst For](#who-is-indy-catalyst-for)
  - [Key Technical Elements](#key-technical-elements)
    - [Credential Registry](#credential-registry)
    - [Agent](#agent)
    - [Agent Driver](#agent-driver)
    - [Starter Kits](#starter-kits)
      - [Credential Registry Holder-Prover](#credential-registry-holder-prover)
      - [Agent Issuer-Verifier](#agent-issuer-verifier)
- [Endnotes](#endnotes)

# Introduction

**Hyperledger Indy Catalyst** is a set of application level software components designed to accelerate the adoption of trustworthy entity to entity<sup id="a1">[1](#f1)</sup> communications based on Decentralized Identity / Self-Sovereign Identity technology and architecture. Indy Catalyst is builds upon globally available open standards and open source software. At present, Indy Catalyst builds upon [Hyperledger Indy](https://www.hyperledger.org/projects), common enterprise open source software, frameworks and patterns such as PostgreSQL, Python, Angular and RESTful APIs. Efforts will be taken to design the software to facilitate the incorporation of evolving open standards and technology. The impetus for Indy Catalyst came from the Verifiable Organizations Network (VON) project. More information about VON can be found at [vonx.io](https://vonx.io)

In order to understand the goals and context of Hyperledger Indy Catalyst, it is advisable to become familiar with the model of decentralized identity or self-sovereign identity which enables trustworthy entity to entity communications. The open standards and technologies enabling this new this model are presented below and annotated with references.

# Decentralized Identity / Self-Sovereign Identity

Self-Sovereign Identity is a term coined by [Christoper Allen in 2016](http://www.lifewithalacrity.com/2016/04/the-path-to-self-soverereign-identity.html) to describe a new generation of digital identity systems. One which "requires that users be the rulers of their own identity." In order to truly understand the intent of this statement, which at first may sound rather radical, it is important to reflect upon the design of current identity systems and contrast that to the emerging design of decentralized identity systems.

The excellent paper, ["Self-sovereign Identity: A position paper on blockchain enabled identity and the road ahead"](https://www.bundesblock.de/wp-content/uploads/2018/10/ssi-paper.pdf), published in October 2018 by the [German Blockchain Association](https://www.bundesblock.de) highlights the key differentiators between current digital identity systems and emerging self-sovereign identity systems.

The key differentiator pertains to the means by which current centralized identity systems keep track of individual entities in their databases. Centralized identity systems create and assign an identifer for each individual entity and associate data about that individual entity to that identifier. This is a familiar idea to most of us. In the analog world these identifiers have names such as drivers licence number, credit card number, bank account number, social insurance number, etc. The identity system owner creates and is in control of the _identifiers_ and associated data for individual entities and not the individual entities themselves. Identity system operators have the ability to unilaterally make changes to these identifiers are associated data.

In contrast, the design of a decentralized or "self-sovereign" identity system is to put individual entities in control of the _identifiers_ used to keep track of them as well as the holding and disclosure of the data associated to these new identifiers. These new identifiers, described below, are called ["Decentralized Identifiers" (DID)](#decentralized-identifiers-did). The data associated to these identifiers is encoded into a new format called a [Verifiable Credential](#verifiable-credentials). These Verifiable Credentials are issued to and held by individual entities.

Using this new approach to identity systems design means a person would be in full control of data issued to them by third parties. People would be in control of disclosing of their personally identifiable data as issued by themselves (e.g. personal preferences, messages, etc) or issued to them by third parties. These third parties may include authoritative issuers such as governments (e.g. identity documents, licences) or they could be issuers such as a local sports club (e.g. membership). Critically, "self-sovereign" is not intended to suggest a "digital self-declaration" of ones identity in opposition to or as a substitute for authoritative and officially issued identity attributes from a government. Rather, that one is both "in control" of the relationship (the decentralized identifier) and the data (verifiable credential) issued to them. Therefore, once one is holding this officially issued data, one can choose when and what one would like to disclose to third parties. The details of how this can be technically achieved are described briefly in the following sections along with appropriate references for further study.

It is important to note that while these emerging standards and technologies are being designed to tackle the very difficult challenges of secure and privacy respecting digital identity for people, they are not limited to the narrow context of personal identity. This new model can be applied to a broader set of use cases beyond those involving personally identifiable information. The model offers a generalized capability enabling highly secure entity to entity communications and it is this generalized capability that has led to the creation of Hyperledger Indy Catalyst. Indy Catalyst components enable enterprises to issue, hold and verify data about entities.

## Open Standards

There are two emerging open standards aimed at enabling interoperable secure and privacy respecting entity to entity data exchange.

### Decentralized Identifiers (DID)

A DID is a globally unique and resolvable identifier created by a entity. A entity could be any sort of real world actor such as an individual person, a legal entity, a government authority, a thing. DIDs are created and issued by software under the control of a entity. DIDs are bound with the necessary information to allow a entity to demonstrate cryptographic control over the DID and to enable secure communications with that entity. With these basic primitives, secure and privacy respecting entity to entity data exchange becomes possible. DIDs do not require any centralized issuing or resolution authority.

### Verifiable Credentials

A verifiable credential is data issued to, and held by an entity. Verifiable indicates the credential is rendered tamper-evident and in a manner whereby the issuer can be cryptographically verified.<sup id="a2">[2](#f2)</sup> Data contained in a verifiable credential is organized into individual claims. Claims within a credential can be about different subjects (e.g entities) and may be verifiable individually.

### Links to Emerging DID and Verifiable Credentials Standards

The DID and Verifiable Credential emerging open standards are being incubated within the [W3C Credentials Community Group](https://www.w3.org/community/credentials/)

#### DID Standards

- [W3C DID Primer](https://w3c-ccg.github.io/did-primer/)
- [W3C DID Spec](https://w3c-ccg.github.io/did-spec/)

#### Verifiable Credentials Standards

- [W3C Verifiable Claims Working Group](https://www.w3.org/2017/vc/WG/)
- [W3C Verifiable Credentials Data Model 1.0](https://w3c.github.io/vc-data-model/)

## General Model

Stemming from the work in the Verifiable Credentials is a general model for describing the roles of the main actors in a Decentralized Identity / Self-Sovereign Identity ecosystem.

The roles and information flows are described in the [W3C Verifiable Credentials Data Model 1.0](https://w3c.github.io/vc-data-model/#dfn-verifiable-data-registries). The roles are:

1. Issuer
2. Holder (also known as the Prover at verification time)
3. Verifier
4. A [Verifiable Data Registry](https://w3c.github.io/vc-data-model/#dfn-verifiable-data-registries) - commonly a decentralized ledger which serves as a system "mediating the creation and verification of issuer identifiers, keys and other relevant data like verifiable credential schemas and revocation registries".

![verifiable credential general model](/docs/assets/verifiable-credential-model-ForWhiteBK.png)

These roles can be fulfilled by a number of "real world" actors including people, legal entities,or things.

## Technology

The technologies described in this document provide the core functionality required to implement and complement the emerging open standards described above. Together this suite of open standards and technologies create a fundamentally new approach for privacy respecting and secure entity to entity communication.

### Distributed Ledger Technology / Blockchain

The high integrity and global availability of a public blockchain combined with the concept of a DID creates a new decentralized root of trust capability. This new capability tackles a long standing problem with centralized identity systems, in particular those based on Public Key Infrastructure (PKI) models. The following sections provide links to in-depth explorations of these new approaches.

### Decentralized Key Management Systems

As stated in a the [Decentralized Key Management Systems](https://github.com/hyperledger/indy-sdk/blob/677a0439487a1b7ce64c2e62671ed3e0079cc11f/doc/design/005-dkms/DKMS%20Design%20and%20Architecture%20V3.md) research paper for the Department of Homeland Security.

> `"DKMS inverts a core assumption of conventional PKI (public key infrastructure) architecture, namely that public key certificates will be issued by centralized or federated certificate authorities (CAs)."` (DKMS = Decentralized Key Management System)

This paper provides an in-depth on the benefits of DMKS and its design.

### Zero Knowledge Proofs

A [Zero Knowledge Proof](https://medium.com/coinmonks/introduction-to-zero-knowledge-proof-the-protocol-of-next-generation-blockchain-305b2fc7f8e5) protocol is an optional but useful complimentary capability for decentralized identity systems.

Hyperledger Indy does include an implementation of zero knowledge proofs. The implementation is described in this GitHub repository -> [indy-anoncreds](https://github.com/hyperledger/indy-anoncreds)

Zero Knowledge Proofs allow the holder to prove that some or all of the data in a set of claims is true without revealing any additional information, including the identity of the holder. During these interactions the holder is referred to as a "Prover" as they are offering a proof of knowledge rather than transfering the claim directly to the verifier. This is a powerful capability enabling the holder to selectively disclose (e.g. prove "I am over 25" or "I am holding a valid drivers licence") without revealing to the verifier any other facts about themselves.

## Summary: Decentralized Identity / Self-Sovereign Identity Architecture

Decentralized Identity / Self-Sovereign Identity systems make use of DIDs, Verifiable Credentials, and a Verifiable Data Registry (Decentralized Key Management System). Such an architecture is one where the holder of verifiable credentials (a set of verifiable claims) is in complete control of their identifier, where their verifiable credentials are stored, and how they are used.

# Hyperledger Indy

{to be completed}
Based on [indy-node](https://github.com/hyperledger/indy-node) providing the root of trust for [Decentralized Identifiers (DID)](https://w3c-ccg.github.io/did-spec/) and other artifacts to enable a decentralized (or self-sovereign) identity network.

## Overview

[Hyperledger Indy](https://www.hyperledger.org/projects) is open source software providing:

> `"tools, libraries, and reusable components for providing digital identities rooted on blockchains or other distributed ledgers so that they are interoperable across administrative domains, applications, and any other silo."`

More broadly, Hyperledger Indy based networks create the technical conditions for highly secure entity to entity data exchange without the involvement of a central authority. The techniques made available by Hyperledger Indy mitigate the security and privacy problems stemming from current approaches to data exchange over the Internet. These problems are particularily evident when it comes to the exchange of highly senstive forms of data such as personally identifiable information (e.g. identity attributes).

The technical means by which this is accomplished include a number of new open emerging standards and technologies.

## Technical information for Hyperledger Indy

- [Technical information for Hyperledger Indy](https://indy.readthedocs.io/en/latest/)

# Hyperledger Indy Catalyst

{to be completed}

## Motivation

Indy Catalyst components are designed for several enterprise scenarios:

1. join an existing Hyperledger Indy based network as a entity that can engage in entity to entity communication
2. establish a credential registry

Networks require a strategy to get them started. This is due to the challenge of creating network effects. There are several excellent resources describing what network effect are, why they are important, and techniques to go about creating them. Several excellent summaries describing techniques for creating network effects can be found in this [Andreessen Horowitz article](https://a16z.com/2016/03/07/all-about-network-effects/)and in this [NfX article](https://www.nfx.com/post/network-effects-manual). Sometimes this problem is referred to as the ["Chicken and Egg Bootstraping problem"](https://blog.creandum.com/the-chicken-and-the-egg-bootstrapping-a-network-b1165b3a5c47).

## Who is Indy Catalyst For

Indy Catalyst components:

- use standard enterprise and Internet technologies;
- implement common integration patterns to minimize effort to adopt; and,
- minimize the learning needed to get started.

## Key Technical Elements

### Credential Registry

### Agent

### Agent Driver

### Starter Kits

#### Credential Registry Holder-Prover

#### Agent Issuer-Verifier

# Endnotes

<b id="f1">1:</b> A thing with distinct and independent existence such as a person, organization, concept, or device. Source: [Verifiable Claims Data Model and Representations 1.0](https://www.w3.org/2017/05/vc-data-model/CGFR/2017-05-01/#dfn-entity). [↩](#a1)

<b id="f2">2:</b> A verifiable credential is a tamper-evident credential that has authorship that can be cryptographically verified. Source: [W3C
Verifiable Credentials Data Model 1.0](https://w3c.github.io/vc-data-model/#dfn-credential) [↩](#a2)
