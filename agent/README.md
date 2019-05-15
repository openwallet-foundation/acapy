# Hyperledger Indy Catalyst Agent <!-- omit in toc -->

[![CircleCI](https://circleci.com/gh/bcgov/indy-catalyst.svg?style=shield)](https://circleci.com/gh/bcgov/indy-catalyst)
[![codecov](https://codecov.io/gh/bcgov/indy-catalyst/branch/master/graph/badge.svg)](https://codecov.io/gh/bcgov/indy-catalyst)
[![Known Vulnerabilities](https://snyk.io/test/github/bcgov/indy-catalyst/badge.svg?targetFile=agent%2Frequirements.txt)](https://snyk.io/test/github/bcgov/indy-catalyst?targetFile=agent%2Frequirements.txt)

![logo](/docs/assets/indy-catalyst-logo-bw.png)

# Table of Contents <!-- omit in toc -->

- [Introduction](#Introduction)
- [Installing](#Installing)
- [Running](#Running)
- [Developing](#Developing)
  - [Prerequisites](#Prerequisites)
  - [Running Locally](#Running_Locally)
    - [Caveats](#Caveats)
  - [Running Tests](#Running_Tests)
  - [Development Workflow](#Development_Workflow)

# Introduction

Indy Catalyst Agent is a configurable instance of a "Cloud Agent".

# Installing

Instructions forthcoming. `indy_catalyst_agent` will be made available in the future as a python package at [pypi.org](https://pypi.org).

# Running

After installing the package, `icatagent` should be available in your PATH.

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

```
./scripts/run_docker <args>
```

```
./scripts/run_docker --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

To enable the [ptvsd](https://github.com/Microsoft/ptvsd) Python debugger for Visual Studio/VSCode use the `debug` flag

For any ports you will be using, you can publish these ports from the docker container using the PORTS environment variable. For example:

```
PORTS="5000:5000 8000:8000 1000:1000" ./scripts/run_docker --inbound-transport http 0.0.0.0 10000 --outbound-transport http --debug --log-level DEBUG
```

Refer to [the previous section](#Running) for instructions on how to run the software.

## Running Tests

To run the test suite, use the following script:

```sh
./scripts/run_tests
```

To run the test including [Indy SDK](https://github.com/hyperledger/indy-sdk) and related dependencies, run the script:

```sh
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
