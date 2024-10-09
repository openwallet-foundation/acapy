# Integration Tests for ACA-Py using Behave

Integration tests for ACA-Py are implemented using Behave functional tests to drive ACA-Py agents based on the alice/faber demo framework.

If you are new to the ACA-Py integration test suite, this [video](https://youtu.be/AbuPg4J8Pd4) from ACA-Py Maintainer [@ianco](https://github.com/ianco) describes
the Integration Tests in ACA-Py, how to run them and how to add more tests. See also the video at the end of this document about running
[Aries Agent Test Harness](https://github.com/hyperledger/aries-agent-test-harness) (AATH) tests before you submit your pull requests. Note
that the relevant AATH tests are now run as part of the tests run when submitting a code PR for ACA-Py.

## Getting Started

To run the ACA-Py Behave tests, open a bash shell run the following:

```bash
git clone https://github.com/bcgov/von-network
cd von-network
./manage build
./manage start
cd ..
git clone https://github.com/bcgov/indy-tails-server.git
cd indy-tails-server/docker
./manage build
./manage start
cd ../..
git clone "https://github.com/openwallet-foundation/acapy"
cd acapy/demo
./run_bdd -t ~@taa_required
```

Note that an Indy ledger and tails server are both required (these can also be specified using environment variables).

Note also that some tests require a ledger with Indy the "TAA" (Transaction
Author Agreement) concept enabled, how to run these tests will be described
later.

By default the test suite runs using a default (SQLite) wallet, to run the tests
using postgres run the following:

```bash
# run the above commands, up to cd acapy/demo
docker run --name some-postgres -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres:10
ACAPY_ARG_FILE=postgres-indy-args.yml ./run_bdd
```

To run the tests against the back-end `askar` libraries (as opposed to indy-sdk) run the following:

```bash
BDD_EXTRA_AGENT_ARGS="{\"wallet-type\":\"askar\"}" ./run_bdd -t ~@taa_required
```

(Note that `wallet-type` is currently the only extra argument supported.)

You can run individual tests by specifying the tag(s):

```bash
./run_bdd -t @T001-AIP10-RFC0037
```

## Running Integration Tests which require TAA

To run a local von-network with TAA enabled,run the following:

```bash
git clone https://github.com/bcgov/von-network
cd von-network
./manage build
./manage start --taa-sample --logs
```

You can then run the TAA-enabled tests as follows:

```bash
./run_bdd -t @taa_required
```

or:

```bash
BDD_EXTRA_AGENT_ARGS="{\"wallet-type\":\"askar\"}" ./run_bdd -t @taa_required
```

The agents run on a pre-defined set of ports, however occasionally your local system may already be using one of these ports.  (For example MacOS recently decided to use 8021 for the ftp proxy service.)

To override the default port settings:

```bash
AGENT_PORT_OVERRIDE=8030 ./run_bdd -t <some tag>
```

(Note that since the test run multiple agents you require up to 60 available ports.)

### Note on BBS Signatures

ACA-Py does not come installed with the `bbs` library by default therefore integration tests involving BBS signatures (tagged with @BBS) will fail unless excluded.

You can exclude BBS tests from running with the tag `~@BBS`:

```bash
   run_bdd -t ~@BBS
```

If you want to run all tests including BBS tests you should include the `--all-extras` flag:

```bash
   run_bdd --all-extras
```

Note: The `bbs` library may not install on ARM (i.e. aarch64 or  arm64) architecture therefore YMMV with testing BBS Signatures on ARM based devices.

## ACA-Py Integration Tests vs Aries Agent Test Harness (AATH)

ACA-Py Behave tests are based on the interoperability tests that are implemented in the [Aries Agent Test Harness (AATH)](https://github.com/hyperledger/aries-agent-test-harness).  Both use [Behave (Gherkin)](https://behave.readthedocs.io/en/stable/) to execute tests against a running ACA-Py agent (or in the case of AATH, against any compatible Aries agent), however the ACA-Py integration tests focus on ACA-Py specific features.

AATH:

- Main purpose is to test interoperability between Aries agents
- Implements detailed tests based on [Aries RFC's](https://github.com/hyperledger/aries-rfcs) (runs different scenarios, tests exception paths, etc.)
- Runs Aries agents using Docker images (agents run for the duration of the tests)
- Uses a standard "backchannel" to support integration of any Aries agent

As of around the publication of ACA-Py 1.0.0 (Summer 2024), the ACA-Py CI/CD Pipeline for code PRs includes running a useful subset of AATH tests.

ACA-Py integration tests:

- Main purpose is to test ACA-Py
- Implements tests based on Aries RFC's, but not to the level of detail as AATH (runs (mostly) happy path scenarios against multiple agent configurations)
- Tests ACA-Py specific configurations and features that go beyond Aries.
- Starts and stops agents for each tests to test different ACA-Py configurations
- Uses the same Python framework as used for the interactive Alice/Faber demo

## Configuration-driven Tests

ACA-Py integration tests use the same configuration approach as AATH, documented [here](https://github.com/hyperledger/aries-agent-test-harness/blob/master/CONFIGURE-CRED-TYPES.md).

In addition to support for external schemas, credential data etc, the ACA-Py integration tests support configuration of the ACA-Py agents that are used to run the test.  For example:

```behave
Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
  Given "3" agents
     | name  | role     | capabilities        |
     | Acme  | issuer   | <Acme_capabilities> |
     | Faber | verifier | <Acme_capabilities> |
     | Bob   | prover   | <Bob_capabilities>  |
  And "<issuer>" and "Bob" have an existing connection
  And "Bob" has an issued <Schema_name> credential <Credential_data> from <issuer>
  ...

  Examples:
     | issuer | Acme_capabilities        | Bob_capabilities | Schema_name    | Credential_data          | Proof_request  |
     | Acme   | --public-did             |                  | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
     | Faber  | --public-did  --mediator | --mediator       | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
```

In the above example, the test will run twice using the parameters specified in the "Examples" section.  The Acme, Faber and Bob agents will be started for the test and then shut down when the test is completed.

The agent's "capabilities" are specified using the same command-line parameters that are supported for the Alice/Faber demo agents.

## Global Configuration for All ACA-Py Agents Under Test

You can specify parameters that are applied to all ACA-Py agents using the `ACAPY_ARG_FILE` environment variable, for example:

```bash
ACAPY_ARG_FILE=postgres-indy-args.yml ./run_bdd
```

... will apply the parameters in the `postgres-indy-args.yml` file (which just happens to configure a postgres wallet) to *all* agents under test.

Or the following:

```bash
ACAPY_ARG_FILE=askar-indy-args.yml ./run_bdd
```

... will run all the tests against an askar wallet (the new shared components, which replace indy-sdk).

Any ACA-Py argument can be included in the yml file, and order-of-precedence applies (see [https://pypi.org/project/ConfigArgParse/](https://pypi.org/project/ConfigArgParse/)).

## Specifying Environment Parameters when Running Integration Tests

ACA-Py integration tests support the following environment-driven configuration:

- `LEDGER_URL` - specify the ledger url
- `TAILS_NETWORK` - specify the docker network the tails server is running on
- `PUBLIC_TAILS_URL` - specify the public url of the tails server
- `ACAPY_ARG_FILE` - specify global ACA-Py parameters (see above)

## Running specific test scenarios

Behave tests are tagged using the same [standard tags as used in AATH](https://github.com/hyperledger/aries-agent-test-harness#test-tags).

To run a specific set of ACA-Py integration tests (or exclude specific tests):

```bash
./run_bdd -t tag1 -t ~tag2
```

(All command line parameters are passed to the `behave` command, so [all parameters supported by behave](https://behave.readthedocs.io/en/stable/behave.html) can be used.)

## Aries Agent Test Harness ACA-Py Tests

This [video](https://youtu.be/1dwyEBxQqWI) is a presentation by ACA-Py developer [@ianco](https://github.com/ianco) about using the Aries Agent Test Harness for local pre-release testing of ACA-Py. Have a big change that you want to test with other Aries Frameworks? Following this guidance to run AATH tests with your under-development branch of ACA-Py.
