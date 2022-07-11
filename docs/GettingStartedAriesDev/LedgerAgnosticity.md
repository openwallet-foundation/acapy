# Ledger Agnosticity

An Aries agent is in charge of communicating with the ledger in order to save, read and update all the public information necessary for issuance, verification and revocation of digital credentials. Given the range of different ledgers available outside, the Aries agent should be open to extension in order to give the developers the possibility to easily implement new adapters for new ledgers. We call this agent property as **ledger agnosticity** and we present here our updates on the codebase to make it possible together with a quick guide for developers to build new adapters for ledgers which are not supported yet.

## Table of contents

- [Ledger agnosticity before our work](#ledger-agnosticity-before-our-work)
  - [Profiles](#profiles)
- [Ledger agnosticity after our work](#ledger-agnosticity-after-our-work)
  - [How to add an adapter for a new ledger in aries-cloudagent-python](#How to add an adapter for a new ledger in aries-cloudagent-python)
  - [Ledger agnosticity in indy-tails-server](#ledger-agnosticity-in-indy-tails-server)
  - [How to add an adapter for a new ledger in indy-tails-server](#how-to-add-an-adapter-for-a-new-ledger-in-indy-tails-server)
- [Demo: CentralizedSdkLedger](#demo-centralizedsdkledger)
  - [Setup the tails server](#setup-the-tails-server)
  - [Setup the centralized ledger](#setup-the-centralized-ledger)
  - [Run the demo with the centralized ledger](#run-the-demo-with-the-centralized-ledger)

## Ledger agnosticity before our work

Before our work, the Aries agent codebase already defined the abstract class `aries_cloudagent.ledger.base.BaseLedger` to use as superclass for the ledger adapter implementation.

### Profiles

The choice of the ledger to use with the agent was tightly linked to the chosen wallet type through *profiles*.

A *profile* is an implementation of the base class `aries_cloudagent.core.profile.Profile`. The specific profile to use within the agent is chosen according to the `--wallet-type` command-line parameter indicated at start time. One of the goals of the profile is to inject the right classes to use at a later stage into the app context. This operation is performed also for the ledger class, hardcoded in the profile implementation. 

This code choice makes the ledger choice dependent on the chosen wallet type. For instance, let's have a look at the code snippet below which has been taken from the Indy profile implementation `aries_cloudagent.indy.sdk.profile.IndySdkProfile` (used for the wallet of type `indy`):

```python
# from aries_cloudagent.indy.sdk.profile.IndySdkProfile.bind_providers
injector.bind_provider(
    BaseLedger, ClassProvider(IndySdkLedger, self.ledger_pool, ref(self))
)
```

As shown by the snippet, the ledger class `IndySdkLedger` is hardcoded inside the `IndySdkProfile` implementation as the `BaseLedger` implementation to use throughout the agent code. This means that whenever we start our agent with the cli option `--wallet-type indy` we have no power in choosing which ledger to use. With this approach the developer needs to create a new profile every time he needs to support a new ledger, also when only the ledger implementation of a specific profile has to be changed, leaving all the remaining context population unchanged. Such constraints can lead to code duplication and complexity inside the aries codebase.

## Ledger agnosticity after our work

To decouple profiles from hardcoded ledgers we implemented the class `aries_cloudagent.ledger.provider.LedgerProvider` and added the command-line option `--wallet-ledger` to decide what specific ledger to use in combination with the specified wallet type. With this approach the ledger implementation to use is not coupled with the wallet type anymore and it does not need to be hardcoded into the profile implementation. 

On the contrary, the new class called `LedgerProvider` is in charge of choosing the correct ledger adapter implementation according to the command line parameters passed to the agent.

The code snippet indicated in the section [Profiles](#profiles) becomes as follows:

```python
# from aries_cloudagent.indy.sdk.profile.IndySdkProfile.bind_providers
ledger_provider = self.inject(LedgerProvider)
injector.bind_provider(
    BaseLedger, ClassProvider(ledger_provider.get_ledger(), self.ledger_pool, ref(self))
)
```

There is no *hardcoded* ledger anymore and in this way a single profile can handle more ledger implementations. As a consequence the developer can now specify a new ledger adapter which works fine with a wallet type without writing an entire new profile, but only by adding the new ledger class implementation to the wallet pool of supported ledgers. 

### How to add an adapter for a new ledger in aries-cloudagent-python

The ledger adapter class must always extend the abstract class `aries_cloudagent.ledger.base.BaseLedger`. Once implemented all the required methods, the ledger adapter must be added to the pool of ledger implementations in `aries_cloudagent.ledger.provider.LedgerProvider`, which looks as follows:

```python
# from aries_cloudagent.ledger.provider.LedgerProvider
WALLET_SUPPORTED_LEDGERS = {
    "askar": {
        "default": IndyVdrLedger,
        IndyVdrLedger.BACKEND_NAME: IndyVdrLedger
    },
    "indy": {
        "default": IndySdkLedger,
        IndySdkLedger.BACKEND_NAME: IndySdkLedger,
        CentralizedSdkLedger.BACKEND_NAME: CentralizedSdkLedger
    },
}
```

The ledger adapter must be added to each wallet it will support. The `BACKEND_NAME` of the ledger must not be one already in use by other existing ledgers.

The `"default"` ledger indicates the ledger adapter which is going to be used in case no `--wallet-ledger` option is specified from the command line.

### Ledger agnosticity in indy-tails-server

Being *credential agnostic* and *ledger agnostic* at same time requires the agent's capability to make the choice of the credential type to use independently of the ledger (and vice-versa). This property was not satisfied when using *anonCreds* credentials which require a running **tails-server** to let revocation working. The tails-server requires access to the ledger in order to retrieve the **revocation registry definition**, but what we found out was that the tails-server implementation was able to connect to the **Indy ledger** only, making it an obstacle for achieving the ledger agnosticity.

### How to add an adapter for a new ledger in indy-tails-server

We updated the indy-tails-server repository by adding the ledger agnosticity concept using the same pattern indicated in the section [How to add an adapter for a new ledger in aries-cloudagent-python](#how-to-add-an-adapter-for-a-new-ledger-in-aries-cloudagent-python). The new code can be downloaded from this [repository](https://github.ibm.com/Pasquale-Convertini/indy-tails-server).

The ledger adapter class must always extend the abstract class `tails_server.ledger.base.BaseLedger`. Once implemented all the required methods, the ledger adapter must be added to the pool of ledger implementations in `tails_server.ledger_provider.LedgerProvider`, which looks as follows:

```python
TAILS_SERVER_SUPPORTED_LEDGERS = {
    IndySdkLedger.BACKEND_NAME: IndySdkLedger,
    CentralizedSdkLedger.BACKEND_NAME: CentralizedSdkLedger
}
```

Therefore, if a developer wants to develop a ledger adapter compatible with *anonCreds* which supports revocation, then it needs to write the ledger adapter for both the `aries-cloudagent-python` and the `indy-tails-server` following the guidelines indicated above. 

## Demo: CentralizedSdkLedger

We developed an example ledger adapter named as `CentralizedSdkLedger` which shows how, with our work, the Aries agent could use a simple h2 database as ledger. The communication between the agent and the database is based on RESTful APIs and it is implemented inside the class `aries_cloudagent.ledger.centralized.CentralizedSdkLedger`. This demo will use *anonCreds* as credentials, but you can use also other credential types.

### Run the tails server

The tails server needs to be run if you plan to use the revocation capabilities of the Aries agent for *anonCreds*. If so, you must download the source code from this [repository](https://github.ibm.com/Pasquale-Convertini/indy-tails-server). Follow the README to start the tails server by using docker.

### Run the centralized ledger

To test locally such implementation it is necessary to start and run the centralized ledger instance on your local machine. You can download the source code from this [repository](https://github.ibm.com/research-ssi/ssi-centralized-ledger/tree/aca-py). Follow the guide to locally build and run the centralized ledger.

### Run the demo with the centralized ledger

Once the tails server and the centralized ledger instance are up and running on your local machine, you can play around with the `CentralizedSdkLedger` running different instances of the Aries agent and let them communicate. Go in the `demo/` folder under the root folder of this project and run the following commands.

To start the Faber instance (issuer) run:

```bash
$ PUBLIC_TAILS_URL=http://host.docker.internal:6543 LEDGER_URL=http://host.docker.internal:8080 ./run_demo faber --events --no-auto --revocation --wallet-type indy --wallet-ledger centralized
```

To start the Alice instance (holder) run:

```bash
$ LEDGER_URL=http://host.docker.internal:8080 ./run_demo alice --events --no-auto --wallet-type indy --wallet-ledger centralized
```

To start the Acme instance (verifier) run:

```bash
$ LEDGER_URL=http://host.docker.internal:8080 ./run_demo acme --events --no-auto --wallet-type indy --wallet-ledger centralized
```

Now you can play with these agent instances by issuing credentials, requesting proofs and sending messages between the agents themselves by either using the Swagger interface or by using the command line interaction interface.