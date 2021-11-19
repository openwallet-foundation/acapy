# What should I work on? Options for Aries/Indy Developers

Now that you know the basics of the Indy/Aries eco-system, what do you want to work on? There are many projects at different levels of the eco-system you could choose to work on, and many ways to contribute to the community.

This is an important summary for newcomers, as often the temptation is to start at a level far below where you plan to focus your attention. Too often devs coming into the community start at "the blockchain"; at `indy-node` (the Indy public ledger) or the `indy-sdk`. That is far below where the majority of developers will work and is not really that helpful if what you really want to do is build decentralized identity applications.

In the following, we go through the layers from the top of the stack to the bottom. Our expectation is that the majority of developers will work at the application level, and there will be fewer contributing developers each layer down you go. This is not to dissuade anyone from contributing at the lower levels, but rather to say if you are not going to contribute at the lower levels, you don't need to everything about it. It's much like web development - you don't need to know TCP/IP to build web apps.

## Building Decentralized Identity Applications

If you just want to build enterprise applications on top of the decentralized identity-related Hyperledger projects, you can start with building cloud-based controller apps using any language you want, and deploying your code with an instance of the code in this repository ([aries-cloudagent-python](https://github.com/hyperledger/aries-cloudagent-python)). 

If you want to build a mobile agent, there are open source options available, including [Aries-MobileAgent-Xamarin](https://github.com/hyperledger/aries-mobileagent-xamarin) (aka "Aries MAX"), which is built on [Aries Framework .NET](https://github.com/hyperledger/aries-framework-dotnet), and [Aries Mobile Agent React Native](https://github.com/hyperledger/aries-mobile-agent-react-native), which is built on [Aries Framework JavaScript](https://github.com/hyperledger/aries-framework-javascript).

As a developer building applications that use/embed Aries agents, you should join the [Aries Working Group](https://wiki.hyperledger.org/display/ARIES/Aries+Working+Group)'s weekly calls and watch the [aries-rfcs](https://github.com/hyperledger/aries-rfcs) repo to see what protocols are being added and extended. In some cases, you may need to create your own protocols to be added to this repository, and if you are looking for interoperability, you should specify those protocols in an open way, involving the community.

Note that if building apps is what you want to do, you don't need to do a deep dive into the Aries SDK, the Indy SDK or the Indy Node public ledger. You need to know the concepts, but it's not a requirement that know the code base intimately.

## Contributing to `aries-cloudagent-python`

Of course as you build applications using `aries-cloudagent-python`, you will no doubt find deficiencies in the code and features you want added. Contributions to this repo will **always** be welcome.

## Supporting Additional Ledgers

`aries-cloudagent-python` currently supports only Hyperledger Indy-based public ledgers and verifiable credentials exchange. A goal of Hyperledger Aries is to be ledger-agnostic, and to support other ledgers. We're experimenting with adding support for other ledgers, and would welcome assistance in doing that.

## Other Agent Frameworks

Although controllers for an `aries-cloudagent-python` instance can be written in any language, there is definitely a place for functionality equivalent (and better) to what is in this repo in other languages. Use the example provided by the `aries-cloudagent-python`, evolve that using a different language, and as you discover better ways to do things, discuss and share those improvements in the broader Aries community so that this and other codebases improve.

## Improving Aries SDK

This code base and other Aries agent implementations currently embed the `indy-sdk`. However, much of the code in the `indy-sdk` is being migrated into a variety of Aries language specific repositories. How this migration is to be done is still being decided, but it makes sense that the agent-type things be moved to Aries repositories. A number of [language specific Aries SDK](https://github.com/hyperledger?utf8=%E2%9C%93&q=aries+sdk&type=&language=) repos have been created and are being populated.

## Improving the Indy SDK

Dropping down a level from Aries and into Indy, the [indy-sdk](https://github.com/hyperledger/indy-sdk) needs to continue to evolve. The code base is robust, of high quality and well thought out, but it needs to continue to add new capabilities and improve existing features. The `indy-sdk` is implemented in Rust, to produce a C-callable library that can be used by client libraries built in a variety of languages.

## Improving Indy Node

If you are interested in getting into the public ledger part of Indy, particularly if you are going to be a Sovrin Steward, you should take a deep look into [indy-node](https://github.com/hyperledger/indy-node). Like the `indy-sdk`, `indy-node` is robust, of high quality and is well thought out. As the network grows, use cases change and new cryptographic primitives move into the mainstream, `indy-node` capabilities will need to evolve. `indy-node` is coded in Python.

## Working in Cryptography

Finally, at the deepest level, and core to all of the projects is the cryptography in [Hyperledger Ursa](https://github.com/hyperledger/ursa). If you are a cryptographer, that's where you want to be - and we want you there.




