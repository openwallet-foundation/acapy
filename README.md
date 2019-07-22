# Hyperledger Aries Cloud Agent - Python  <!-- omit in toc -->

[![CircleCI](https://circleci.com/gh/hyperledger/aries-cloudagent-python.svg?style=shield)](https://circleci.com/gh/hyperledger/aries-cloudagent-python)
[![codecov](https://codecov.io/gh/hyperledger/aries-cloudagent-python/branch/master/graph/badge.svg)](https://codecov.io/gh/hyperledger/aries-cloudagent-python)
[![Known Vulnerabilities](https://snyk.io/test/github/hyperledger/aries-cloudagent-python/badge.svg)](https://snyk.io/test/github/hyperledger/aries-cloudagent-python?targetFile=requirements.txt)

<!-- ![logo](/docs/assets/aries-cloudagent-python-logo-bw.png) -->

## Table of Contents <!-- omit in toc -->

- [Introduction](#Introduction)
- [Resources](#Resources)

## Introduction

Hyperledger Aries Cloud Agent Python (ACA-Py) is a foundation for building decentralized identity applications and services running in non-mobile environments using DIDcomm messaging, the did:peer method, and verifiable credentials. With ACA-Py, Hyperledger Indy and Aries developers can focus on building applications using familiar web development technologies instead of trying to learn the nuts and bolts of low-level SDKs. ACA-Py is built on the Aries concepts and features defined in the [Aries RFC](https://github.com/hyperledger/aries-rfcs) repository. [This document](SupportedRFCs.md) contains a (reasonably up to date) list of supported Aries RFCs by the current ACA-Py implementation.

The ACA-Py development model is pretty straight forward for those familiar with web development. An ACA-Py instance is always deployed with a paired "controller" application that provides the business logic for that Aries agent. The controller receives webhook event notifications from its instance of ACA-Py and uses an HTTP API exposed by the ACA-Py instance to provide direction on how to respond to those events. The source of the business logic is left to your imagination. An interface to a legacy system? A user interface for a person? Custom code to implement a new service? You can build your controller in any language that supports making and receiving HTTP requests. Wait...that's every language!

ACA-Py currently supports "only" Hyperledger Indy's verifiable credentials scheme (which is pretty powerful). We are experimenting with adding support to ACA-Py for other DID Ledgers and verifiable credential schemes.

As we create ACA-Py, we're building resources so that developers with a wide-range of backgrounds can get productive with ACA-Py in a hurry. Scan the resources below and jump in.

## Resources

If you are experienced decentralized identity developer that knows Indy, is already familiar with the concepts behind Aries, and want to play with the code and perhaps start contributing, a traditional "install and go" page for developers can be found [here](DevReadMe.md).

For everyone else, we've created a [Getting Started Guide](docs/GettingStartedAriesDev/README.md) that will take you from knowing next to nothing about decentralized identity to developing Aries-based business apps and services in a hurry. Along the way, you'll run some early Indy apps, apps built on ACA-Py and developer-oriented demos for interacting with ACA-Py. The guide has a good table of contents so that you can skip the parts you already know.

We'll soon have a ReadTheDocs site published with docstrings extracted from the ACA-Py code.

Not sure where your focus should be? Building apps? Aries? Indy? Indy's Blockchain? Ursa? Here is a [document](docs/GettingStartedAriesDev/IndyAriesDevOptions.md) that goes through the technical stack to show how it the projects fit together, so you can decide where you want to focus your efforts.

The initial implementation of ACA-Py was developed by the Verifiable Organizations Network (VON) team based at the Province of British Columbia. To learn more about VON and what's happening with decentralized identity in British Columbia, please go to [https://vonx.io](https://vonx.io).

