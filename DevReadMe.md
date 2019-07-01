# Developer's Read Me for Hyperledger Aries Cloud Agent - Python  <!-- omit in toc -->

See the [README](README.md) for details about this repository and information about how the Aries Cloud Agent - Python fits into the Aries project and relates to Indy.

## Table of Contents <!-- omit in toc -->

- [Introduction](#Introduction)
- [Installing](#Installing)
- [Developer Demos](#Developer-Demos)
- [Running](#Running)
- [Developing](#Developing)
  - [Prerequisites](#Prerequisites)
  - [Running Locally](#Running-Locally)
  - [Running Tests](#Running-Tests)
  - [Development Workflow](#Development-Workflow)
  - [Dynamic Injection of Services](#Dynamic-Injection-of-Services)

## Introduction

Aries Cloud Agent Python (ACA-Py) is a configurable, extensible, non-mobile Aries agent that implements an easy way for developers to build decentralized identity applications that use verifiable credentials.

The information on this page assumes you are developer with a background in decentralized identity, Indy, Aries and verifiable credentials. If you aren't familiar with those concepts and projects, please use our [Getting Started Guide](docs/gettingStartedAriesDev/README.md) to learn more.

## Installing

Instructions forthcoming. `aries_cloudagent` will be made available in the future as a python package at [pypi.org](https://pypi.org).

## Developer Demos

To put ACA-Py through its paces at the command line, checkout our [demos](docs/gettingStartedAriesDev/AriesDeveloperDemos.md) page.

## Running

After installing the PyPi package, the executable `acagent` should be available in your PATH.

Find out more about the available command line parameters by running:

```bash
acagent --help
```

Currently you must specify at least one _inbound_ and one _outbound_ transport.

For example:

```bash
acagent     --inbound-transport http 0.0.0.0 8000 \
            --inbound-transport http 0.0.0.0 8001 \
            --inbound-transport ws 0.0.0.0 8002 \
            --outbound-transport ws \
            --outbound-transport http
```

Currently, Aries Cloud Agent Python ships with both inbound and outbound transport drivers for `http` and `websockets`. More information on how to develop your own drivers will be coming soon.

## Developing

### Prerequisites

[Docker](https://www.docker.com) must be installed to run software locally and to run the test suite.

### Running Locally

To run the locally, we recommend using the provided Docker images to run the software.

```bash
./scripts/run_docker <args>
```

```bash
./scripts/run_docker --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

To enable the [ptvsd](https://github.com/Microsoft/ptvsd) Python debugger for Visual Studio/VSCode use the `debug` flag

Publish any ports you will be using from the docker container using the PORTS environment variable. For example:

```bash
PORTS="5000:5000 8000:8000 1000:1000" ./scripts/run_docker --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

Refer to [the previous section](#Running) for instructions on how to run the software.

### Running Tests

To run the test suite, use the following script:

```bash
./scripts/run_tests
```

To run the tests including [Indy SDK](https://github.com/hyperledger/indy-sdk) and related dependencies, run the script:

```bash
./scripts/run_tests_indy
```

### Development Workflow

We use [Flake8](http://flake8.pycqa.org/en/latest/) to enforce a coding style guide.

We use [Black](https://black.readthedocs.io/en/stable/) to automatically format code.

Please write tests for the work that you submit.

Tests should reside in a directory named `tests` alongside the code under test. Generally, there is one test file for each file module under test. Test files _must_ have a name starting with `test_` to be automatically picked up the test runner.

There are some good examples of various test scenarios for you to work from including mocking external imports and working with async code so take a look around!

The test suite also displays the current code coverage after each run so you can see how much of your work is covered by tests. Use your best judgement for how much coverage is sufficient.

Please also refer to the [contributing guidelines](/CONTRIBUTING.md) and [code of conduct](/CODE_OF_CONDUCT.md).

### Dynamic Injection of Services

The Agent employs a dynamic injection system whereby providers of base classes are registered with the `RequestContext` instance, currently within `conductor.py`. Message handlers and services request an instance of the selected implementation using `await context.inject(BaseClass)`; for instance the wallet instance may be injected using `wallet = await context.inject(BaseWallet)`. The `inject` method normally throws an exception if no implementation of the base class is provided, but can be called with `required=False` for optional dependencies (in which case a value of `None` may be returned).

Providers are registered with either `context.injector.bind_instance(BaseClass, instance)` for previously-constructed (singleton) object instances, or `context.injector.bind_provider(BaseClass, provider)` for dynamic providers. In some cases it may be desirable to write a custom provider which switches implementations based on configuration settings, such as the wallet provider.

The `BaseProvider` classes in the `config.provider` module include `ClassProvider`, which can perform dynamic module inclusion when given the combined module and class name as a string (for instance `aries_cloudagent.wallet.indy.IndyWallet`). `ClassProvider` accepts additional positional and keyword arguments to be passed into the class constructor. Any of these arguments may be an instance of `ClassProvider.Inject(BaseClass)`, allowing dynamic injection of dependencies when the class instance is instantiated.
