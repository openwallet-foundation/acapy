# Hyperledger Indy Catalyst Agent <!-- omit in toc -->

![logo](/docs/assets/indy-catalyst-logo-bw.png)

# Table of Contents <!-- omit in toc -->

- [Introduction](#introduction)

# Introduction

Placeholder README for forthcoming Indy Catalyst Agent software.

# Running the software locally

The software is made available as a [Python "Egg"](https://wiki.python.org/moin/egg).
Currently the best way to run the software locally is to install the egg directly using `pip`.
Python 3.6 or greater is required.

```sh
pip3 install --upgrade -e .
```

```sh
icatagent --help
```

# Running tests

For testing in a self-contained [Docker](https://www.docker.com/) environment, make sure
you have Docker installed and run:

```sh
test/docker.sh
```

To execute the test suite locally without using Docker, install the `pytest` Python package
and run:

```sh
pytest
```