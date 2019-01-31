# Hyperledger Indy Catalyst Agent <!-- omit in toc -->

![logo](/docs/assets/indy-catalyst-logo-bw.png)

# Table of Contents <!-- omit in toc -->

- [Introduction](#introduction)

# Introduction

Indy Catalyst Agent is a configurable instance of a Hyperledger Indy "Cloud Agent".

# Installing

Instructions forthcoming. `indy_catalyst_agent` will be made available as a python package at [pypi.org](https://pypi.org).

# Running

After install the package, `icatagent` should be available in your PATH.

Find out more about the available command line parameters by running:

```bash
icatagent --help
```

Currently you must specify at least one _inbound_ and one _outbound_ transport.

For example:

```bash
icatagent   --inbound-transport http 0.0.0.0 8000 \
            --inbound-transport http 0.0.0.0 8001 \
            --inbound-transport ws 0.0.0.0 8002 \
            --outbound-transport ws \
            --outbound-transport http
```

Currently, Indy Catalyst Agent ships with both inbound and outbound transport drivers for `http` and `websockets`. More information on how to develop your own drivers will be coming soon.

# Developing

## Prerequisites

[Docker](https://www.docker.com) must be installed to run software locally and to run the test suite.

## Running Locally

To run the locally, we recommend using the provided Docker images to run the software.

```bash
./scripts/run_docker <args>
```

Refer to [the previous section](#Running) for instructions on how to run the software.

## Running Tests

To run the test suite, use the following script:

```sh
.scripts/run_tests
```

To run the test including [Indy SDK](https://github.com/hyperledger/indy-sdk) and related dependencies, run the script:

```sh
.scripts/run_tests_indy
```

## Development Workflow

Please write tests for the work that you submit. 

Tests should reside in a directory named `tests` alongside the code under test. Generally, there is one test file for each file module under test. Test files _must_ have a name starting with `test_` to be automatically picked up the test runner.

There are some good examples of various test scenarios for you to work from including mocking external imports and working with async code so take a look around!

The test suite also displays the current code coverage after each run so you can see how much of your work is covered by tests. Use your best judgement for how much coverage is sufficient.

Please also refer to the [contributing guidelines](/CONTRIBUTING.md) and [code of conduct](/CODE_OF_CONDUCT.md).