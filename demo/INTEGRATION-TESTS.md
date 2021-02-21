# Integration Tests for Aca-py using Behave

Integration tests for aca-py are implemented using Behave functional tests to drive aca-py agents based on the alice/faber demo framework.

To run the aca-py Behave tests, open a bash shell run the following:

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
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
./run_bdd
```

Note that an Indy ledger and tails server are both required (these can also be specified using environment variables).

## Aca-py Integration Tests vs Aries Agent Test Harness (AATH)

Aca-py Behave tests are based on the interoperability tests that are implemented in the [Aries Agent Test Harness (AATH)](https://github.com/hyperledger/aries-agent-test-harness).  Both use [Behave (Gherkin)](https://behave.readthedocs.io/en/stable/) to execute tests against a running aca-py agent (or in the case of AATH, against any compatible Aries agent), however the aca-py integration tests focus on aca-py specific features.

AATH:

- Main purpose is to test interoperability between Aries agents
- Implements detailed tests based on [Aries RFC's](https://github.com/hyperledger/aries-rfcs)
- Runs Aries agents using Docker images (agents run fot he duration of the tests)
- Uses a standard "backchannel" to support integration of any Aries agent

Aca-py integration tests:

- Main purpose is to test aca-py
- Implements tests based on Aries RFC's, but not to the level of detail as AATH (mostly happy path)
- Tests aca-py specific configurations and features
- Starts and stops agents for each tests to test different aca-py configurations
- Uses the same Python framework as used for the interactive Alice/Faber demo

## Configuration-driven Tests

Aca-py integration tests use the same configuration approach as AATH, documented [here](https://github.com/hyperledger/aries-agent-test-harness/blob/master/CONFIGURE-CRED-TYPES.md).

In addition to support for external schemas, credential data etc, the aca-py integration tests support configuration of the aca-py agents that are used to run the test.  For example:

```
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

## Global Configuration for All Aca-py Agents Under Test

You can specify parameters that are applied to all aca-py agents using the `ACAPY_ARG_FILE` environment variable:

```bash
ACAPY_ARG_FILE=postgres-indy-args.yml ./run_bdd
```

... will apply the parameters in the `postgres-indy-args.yml` file (which just happens to configure a postgres wallet) to *all* agents under test.

Any aca-py arguement can be included in the yml file, and order-of-precidence applies (see [https://pypi.org/project/ConfigArgParse/](https://pypi.org/project/ConfigArgParse/)).

## Specifying Command-line Parameters when Running Integration Tests

Aca-py integration tests support the following environment-driven configuration:

- `LEDGER_URL` - specify the ledger url
- `TAILS_NETWORK` - specify the docker network the tailer server is running on
- `PUBLIC_TAILS_URL` - specify the public url of the tails server
- `ACAPY_ARG_FILE` - specify global aca-py parameters (see above)

Behave tests are tagged using the same [standard tags as used in AATH](https://github.com/hyperledger/aries-agent-test-harness#test-tags).

To run a specific set of Aca-py integration tests (or exclude specific tests):

TBD the `-t` parameters need to be implemented ...

```bash
./run_bdd -t tag1 -t ~tag2
```

