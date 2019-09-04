# Developer's Read Me for Hyperledger Aries Cloud Agent - Python <!-- omit in toc -->

See the [README](README.md) for details about this repository and information about how the Aries Cloud Agent - Python fits into the Aries project and relates to Indy.

## Table of Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Developer Demos](#developer-demos)
- [Running](#running)
  - [Configuring ACA-PY: Command Line Parameters](#configuring-aca-py-command-line-parameters)
  - [Docker](#docker)
  - [Locally Installed](#locally-installed)
  - [About ACA-Py Command Line Parameters](#about-aca-py-command-line-parameters)
  - [Provisioning a Wallet](#provisioning-a-wallet)
- [Developing](#developing)
  - [Prerequisites](#prerequisites)
  - [Running Locally](#running-locally)
  - [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Publishing Releases](#publishing-releases)
- [Dynamic Injection of Services](#dynamic-injection-of-services)

## Introduction

Aries Cloud Agent Python (ACA-Py) is a configurable, extensible, non-mobile Aries agent that implements an easy way for developers to build decentralized identity services that use verifiable credentials.

The information on this page assumes you are developer with a background in decentralized identity, Indy, Aries and verifiable credentials. If you aren't familiar with those concepts and projects, please use our [Getting Started Guide](docs/GettingStartedAriesDev/README.md) to learn more.

## Developer Demos

To put ACA-Py through its paces at the command line, checkout our [demos](docs/GettingStartedAriesDev/AriesDeveloperDemos.md) page.

## Running

### Configuring ACA-PY: Command Line Parameters

ACA-Py agent instances are configured through the use of command line parameters. Use the `--help` option
to discover the available command line parameters.

### Docker

To run a docker container based on the code in the current repo, use the following commands from the root folder of the repository to check the version, list the available modes of operation, and see all of the command line parameters:

```bash
scripts/run_docker --version
scripts/run_docker --help
scripts/run_docker provision --help
scripts/run_docker start --help
```

### Locally Installed

If you installed the PyPi package, the executable `aca-py` should be available on your PATH.

Use the following commands from the root folder of the repository to check the version, list the available modes of operation, and see all of the command line parameters:

```bash
aca-py --version
aca-py --help
aca-py provision --help
aca-py start --help
```

### About ACA-Py Command Line Parameters

ACA-Py invocations are separated into two types - initially provisioning an agent (`provision`) and starting a new agent process (`start`). This separation enables not having to pass in some encryption-related parameters required for provisioning when starting an agent instance. This improves security in production deployments.

When starting an agent instance, at least one _inbound_ and one _outbound_ transport MUST be specified.

For example:

```bash
aca-py start    --inbound-transport http 0.0.0.0 8000 \
                --outbound-transport http
```

or

```bash
aca-py start    --inbound-transport http 0.0.0.0 8000 \
                --inbound-transport ws 0.0.0.0 8001 \
                --outbound-transport ws \
                --outbound-transport http
```

ACA-Py ships with both inbound and outbound transport drivers for `http` and `ws` (websockets). Additional transport drivers can be added as pluggable implementations. See the existing implementations in the [transports module](aries_cloudagent/transport) for getting starting on adding a new transport.

Most configuration parameters are provided to the the agent at startup. Refer to the `Running` sections above for details on listing the available command line parameters.

### Provisioning a Wallet

It is possible to provision an Indy wallet before running an agent to avoid passing in the wallet seed on every invocation of an agent (e.g. on every `aca-py start ...`).

```bash
aca-py provision --wallet-type indy --seed $SEED
```

For additional `provision` options, execute `aca-py provision --help`.

## Developing

### Prerequisites

[Docker](https://www.docker.com) must be installed to run software locally and to run the test suite.

### Running Locally

For local development, we recommend using the provided Docker scripts to run the ACA-Py software.

```bash
./scripts/run_docker start <args>
```

For example:

```bash
./scripts/run_docker start --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

To enable the [ptvsd](https://github.com/Microsoft/ptvsd) Python debugger for Visual Studio/VSCode use the `--debug` command line parameter.

Any ports you will be using from the docker container should be published using the `PORTS` environment variable. For example:

```bash
PORTS="5000:5000 8000:8000 1000:1000" ./scripts/run_docker start --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

Refer to [the previous section](#Running) for instructions on how to run the software.

### Running Tests

To run the ACA-Py test suite, use the following script:

```bash
./scripts/run_tests
```

To run the tests including [Indy SDK](https://github.com/hyperledger/indy-sdk) and related dependencies, run the script:

```bash
./scripts/run_tests_indy
```

## Development Workflow

We use [Flake8](http://flake8.pycqa.org/en/latest/) to enforce a coding style guide.

We use [Black](https://black.readthedocs.io/en/stable/) to automatically format code.

Please write tests for the work that you submit.

Tests should reside in a directory named `tests` alongside the code under test. Generally, there is one test file for each file module under test. Test files _must_ have a name starting with `test_` to be automatically picked up the test runner.

There are some good examples of various test scenarios for you to work from including mocking external imports and working with async code so take a look around!

The test suite also displays the current code coverage after each run so you can see how much of your work is covered by tests. Use your best judgement for how much coverage is sufficient.

Please also refer to the [contributing guidelines](/CONTRIBUTING.md) and [code of conduct](/CODE_OF_CONDUCT.md).

## Publishing Releases

The [publishing](https://github.com/hyperledger/aries-cloudagent-python/blob/master/PUBLISHING.md) document provides information on tagging a release and publishing the release artifacts to PyPi.

## Dynamic Injection of Services

The Agent employs a dynamic injection system whereby providers of base classes are registered with the `RequestContext` instance, currently within `conductor.py`. Message handlers and services request an instance of the selected implementation using `await context.inject(BaseClass)`; for instance the wallet instance may be injected using `wallet = await context.inject(BaseWallet)`. The `inject` method normally throws an exception if no implementation of the base class is provided, but can be called with `required=False` for optional dependencies (in which case a value of `None` may be returned).

Providers are registered with either `context.injector.bind_instance(BaseClass, instance)` for previously-constructed (singleton) object instances, or `context.injector.bind_provider(BaseClass, provider)` for dynamic providers. In some cases it may be desirable to write a custom provider which switches implementations based on configuration settings, such as the wallet provider.

The `BaseProvider` classes in the `config.provider` module include `ClassProvider`, which can perform dynamic module inclusion when given the combined module and class name as a string (for instance `aries_cloudagent.wallet.indy.IndyWallet`). `ClassProvider` accepts additional positional and keyword arguments to be passed into the class constructor. Any of these arguments may be an instance of `ClassProvider.Inject(BaseClass)`, allowing dynamic injection of dependencies when the class instance is instantiated.
