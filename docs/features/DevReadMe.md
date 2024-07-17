# Developer's Read Me for Hyperledger Aries Cloud Agent - Python <!-- omit in toc -->

See the [README](../../README.md) for details about this repository and information about how the Aries Cloud Agent - Python fits into the Aries project and relates to Indy.

## Table of Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Developer Demos](#developer-demos)
- [Running](#running)
  - [Configuring ACA-PY: Environment Variables](#configuring-aca-py-environment-variables)
  - [Configuring ACA-PY: Command Line Parameters](#configuring-aca-py-command-line-parameters)
  - [Docker](#docker)
  - [Locally Installed](#locally-installed)
  - [About ACA-Py Command Line Parameters](#about-aca-py-command-line-parameters)
  - [Provisioning Secure Storage](#provisioning-secure-storage)
  - [Mediation](#mediation)
  - [Multi-tenancy](#multi-tenancy)
  - [JSON-LD Credentials](#json-ld-credentials)
- [Developing](#developing)
  - [Prerequisites](#prerequisites)
  - [Running In A Dev Container](#running-in-a-dev-container)
  - [Running Locally](#running-locally)
  - [Logging](#logging)
  - [Running Tests](#running-tests)
  - [Running Aries Agent Test Harness Tests](#running-aries-agent-test-harness-tests)
- [Development Workflow](#development-workflow)
- [Publishing Releases](#publishing-releases)
- [Dynamic Injection of Services](#dynamic-injection-of-services)

## Introduction

Aries Cloud Agent Python (ACA-Py) is a configurable, extensible, non-mobile Aries agent that implements an easy way for developers to build decentralized identity services that use verifiable credentials.

The information on this page assumes you are developer with a background in
decentralized identity, Aries, DID Methods, and verifiable credentials,
especially AnonCreds. If you aren't familiar with those concepts and projects,
please use our [Getting Started Guide](../gettingStarted/README.md)
to learn more.

## Developer Demos

To put ACA-Py through its paces at the command line, checkout our [demos](../demo/README.md) page.

## Running

### Configuring ACA-PY: Environment Variables

All CLI parameters in ACA-PY have equivalent environment variables. To convert a CLI argument to an environment
variable:

1. **Basic Conversion**: Convert the CLI argument to uppercase and prefix it with `ACAPY_`. For example, `--admin`
   becomes `ACAPY_ADMIN`.

2. **Multiple Parameters**: Arguments that take multiple parameters, such as `--admin 0.0.0.0 11000`, should be wrapped
   in an array. For example, `ACAPY_ADMIN="[0.0.0.0, 11000]"`
3. **Repeat Parameters**: Arguments like `-it <module> <host> <port>`, which can be repeated, must be wrapped inside
   another array and string escaped. For example, instead of: `-it http 0.0.0.0 11000 ws 0.0.0.0 8023`
   use: `ACAPY_INBOUND_TRANSPORT=[[\"http\",\"0.0.0.0\",\"11000\"],[\"ws\",\"0.0.0.0\",\"8023\"]]`

For a comprehensive list of all arguments, argument groups, CLI args, and their environment variable equivalents, please
see
the [argparse.py](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/config/argparse.py)
file.


### Configuring ACA-PY: Command Line Parameters

ACA-Py agent instances are configured through the use of command line
parameters, environment variables and/or YAML files. All of the configurations
settings can be managed using any combination of the three methods (command line
parameters override environment variables override YAML). Use the `--help`
option to discover the available command line parameters. There are a lot of
them--for good and bad.

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

If you get an error about a missing module `indy` (e.g. `ModuleNotFoundError: No module named 'indy'`) when running `aca-py`, you will need to install the Indy libraries from the command line:

```bash
pip install python3_indy
```

Once that completes successfully, you should be able to run `aca-py --version` and the other examples above.

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

ACA-Py ships with both inbound and outbound transport drivers for `http` and `ws` (websockets). Additional transport drivers can be added as pluggable implementations. See the existing implementations in the [transports module](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent/transport) for getting started on adding a new transport.

Most configuration parameters are provided to the agent at startup. Refer to the `Running` sections above for details on listing the available command line parameters.

### Provisioning Secure Storage

It is possible to provision a secure storage (sometimes called a wallet--but not
the same as a mobile wallet app) before running an agent to avoid passing in the
secure storage seed on every invocation of an agent (e.g. on every `aca-py start ...`).

```bash
aca-py provision --wallet-type askar --seed $SEED
```

For additional `provision` options, execute `aca-py provision --help`.

Additional information about secure storage options and configuration settings can be found [here](../deploying/Databases.md).

### Mediation

ACA-Py can also run in mediator mode - ACA-Py can be run _as_ a mediator (it can mediate connections for other agents), or it can connect to an external mediator to mediate its own connections.  See the [docs on mediation](./Mediation.md) for more info.

### Multi-tenancy

ACA-Py can also be started in multi-tenant mode. This allows the agent to serve multiple tenants, that each have their own wallet. See the [docs on multi-tenancy](./Multitenancy.md) for more info.

### JSON-LD Credentials

ACA-Py can issue W3C Verifiable Credentials using Linked Data Proofs. See the [docs on JSON-LD Credentials](./JsonLdCredentials.md) for more info.

## Developing

### Prerequisites

[Docker](https://www.docker.com) must be installed to run software locally and to run the test suite.

### Running In A Dev Container

The dev container environment is a great way to deploy agents quickly with code changes and an interactive debug session. Detailed information can be found in the [Docs On Devcontainers](./devcontainer.md). It is specific for vscode, so if you prefer another code editor or IDE you will need to figure it out on your own, but it is highly recommended to give this a try.

One thing to be aware of is, unlike the demo, none of the steps are automated. You will need to create public dids, connections and all the other steps yourself. Using the demo and studying the flow and then copying them with your dev container debug session is a great way to learn how everything works.

### Running Locally

Another way to develop locally is by using the provided Docker scripts to run the ACA-Py software.

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
PORTS="5000:5000 8000:8000 10000:10000" ./scripts/run_docker start --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

Refer to [the previous section](#running) for instructions on how to run ACA-Py.

### Logging

You can find more details about logging and log levels [here](../testing/Logging.md).

### Running Tests

To run the ACA-Py test suite, use the following script:

```bash
./scripts/run_tests
```

To run the ACA-Py test suite with ptvsd debugger enabled:

```bash
./scripts/run_tests --debug
```

To run specific tests pass parameters as defined by [pytest](https://docs.pytest.org/en/stable/usage.html#specifying-tests-selecting-tests):

```bash
./scripts/run_tests aries_cloudagent/protocols/connections
```

To run the tests including [Indy SDK](https://github.com/hyperledger/indy-sdk) and related dependencies, run the script:

```bash
./scripts/run_tests_indy
```

### Running Aries Agent Test Harness Tests

You can run a full suite of integration tests using the [Aries Agent Test Harness (AATH)](https://github.com/hyperledger/aries-agent-test-harness).

Check out and run AATH tests as follows (this tests the aca-py `main` branch):

```bash
git clone https://github.com/hyperledger/aries-agent-test-harness.git
cd aries-agent-test-harness
./manage build -a acapy-main
./manage run -d acapy-main -t @AcceptanceTest -t ~@wip
```

The `manage` script is described in detail [here](https://github.com/hyperledger/aries-agent-test-harness#the-manage-bash-script), including how to modify the AATH code to run the tests against your aca-py repo/branch.

## Development Workflow

We use [Ruff](https://github.com/astral-sh/ruff) to enforce a coding style guide.

Please write tests for the work that you submit.

Tests should reside in a directory named `tests` alongside the code under test. Generally, there is one test file for each file module under test. Test files _must_ have a name starting with `test_` to be automatically picked up the test runner.

There are some good examples of various test scenarios for you to work from including mocking external imports and working with async code so take a look around!

The test suite also displays the current code coverage after each run so you can see how much of your work is covered by tests. Use your best judgement for how much coverage is sufficient.

Please also refer to the [contributing guidelines](../../CONTRIBUTING.md) and [code of conduct](../../CODE_OF_CONDUCT.md).

## Publishing Releases

The [publishing](https://github.com/hyperledger/aries-cloudagent-python/blob/main/PUBLISHING.md) document provides information on tagging a release and publishing the release artifacts to PyPi.

## Dynamic Injection of Services

The Agent employs a dynamic injection system whereby providers of base classes are registered with the `RequestContext` instance, currently within `conductor.py`. Message handlers and services request an instance of the selected implementation using `context.inject(BaseClass)`; for instance the wallet instance may be injected using `wallet = context.inject(BaseWallet)`. The `inject` method normally throws an exception if no implementation of the base class is provided, but can be called with `required=False` for optional dependencies (in which case a value of `None` may be returned).

Providers are registered with either `context.injector.bind_instance(BaseClass, instance)` for previously-constructed (singleton) object instances, or `context.injector.bind_provider(BaseClass, provider)` for dynamic providers. In some cases it may be desirable to write a custom provider which switches implementations based on configuration settings, such as the wallet provider.

The `BaseProvider` classes in the `config.provider` module include `ClassProvider`, which can perform dynamic module inclusion when given the combined module and class name as a string (for instance `aries_cloudagent.wallet.indy.IndyWallet`). `ClassProvider` accepts additional positional and keyword arguments to be passed into the class constructor. Any of these arguments may be an instance of `ClassProvider.Inject(BaseClass)`, allowing dynamic injection of dependencies when the class instance is instantiated.
