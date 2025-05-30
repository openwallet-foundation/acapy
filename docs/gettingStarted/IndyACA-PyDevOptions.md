# What should I work on? Options for ACA-Py/Indy Developers

Now that you know the basics of the ACA-Py/Indy eco-system, what do you want to work on? There are many projects at different levels of the eco-system you could choose to work on, and many ways to contribute to the community.

This is an important summary for newcomers, as often the temptation is to start at a level far below where you plan to focus your attention. Too often devs coming into the community start at "the blockchain"; at `indy-node` (the Indy public ledger) or the `indy-sdk`. That is far below where the majority of developers will work and is not really that helpful if what you really want to do is build decentralized identity applications.

In the following, we go through the layers from the top of the stack to the bottom. Our expectation is that the majority of developers will work at the application level, and there will be fewer contributing developers each layer down you go. This is not to dissuade anyone from contributing at the lower levels, but rather to say if you are not going to contribute at the lower levels, you don't need to everything about it. It's much like web development - you don't need to know TCP/IP to build web apps.

## Building Decentralized Identity Applications

If you just want to build enterprise applications on top of the decentralized identity-related Hyperledger projects, you can start with building cloud-based controller apps using any language you want, and deploying your code with an instance of the code in the [ACA-Py repository](https://github.com/openwallet-foundation/acapy).

If you want to build a mobile agent, there are open source options available, including [Bifold Wallet](https://github.com/openwallet-foundation/bifold-wallet), which is built on [Credo-TS](https://github.com/openwallet-foundation/credo-ts). Both are OpenWallet Projects.

As a developer building applications that use/embed ACA-Py agents, you should join the [ACA-Py Users Group (ACA-Pug)](https://lf-openwallet-foundation.atlassian.net/wiki/spaces/ACAPy/pages/36831233/ACA-PUG)'s bi-weekly calls and watch the [aries-rfcs](https://github.com/decentralized-identity/aries-rfcs) repo to see what protocols are being added and extended. In some cases, you may need to create your own protocols to be added to this repository, and if you are looking for interoperability, you should specify those protocols in an open way, involving the community.

Note that if building apps is what you want to do, you don't need to do a deep dive into the inner workings of ACA-Py, ledgers or mobile wallets. You need to know the concepts, but it's not a requirement that you know the code base intimately.

## Contributing to ACA-Py

Of course as you build applications using ACA-Py, you will no doubt find deficiencies in the code and features you want added. Contributions to this repo will **always** be welcome.

## Supporting Additional Ledgers

ACA-Py currently supports a handful of public verifiable data registries and verifiable credentials exchange. A project goals to be "ledger"-agnostic, and to support a range of verifiable data registries. We're making it easier and easier to support other verifiable data registries, and would welcome assistance in adding new ones.

## Other Agent Frameworks

Although controllers for an ACA-Py instance can be written in any language, there is definitely a place for functionality equivalent (and better) to what is in this repo in other languages. Use the example provided by the ACA-Py demo, evolve that using a different language, and as you discover better ways to do things, discuss and share those improvements in the broader ACA-Py community so that this and other code bases improve.

## Working at the Cryptographic Layer

Finally, at the deepest level, and core to all of the projects is the cryptography underpinning ACA-Py. If you are a cryptographer, that's where you want to be - and we want you there.
