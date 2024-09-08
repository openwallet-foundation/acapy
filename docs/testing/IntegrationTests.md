# Integration Test Plan

Integration testing in ACA-Py consists of 3 different levels or types.

1. Interop profile (AATH) BDD tests.
2. ACA-Py specific BDD tests.
3. Scenario testing.

## Interop profile (AATH) BDD tests

Interoperability is extremely important in the aries community. When implementing or changing features that are included in the [aries interop profile](https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0302-aries-interop-profile/README.md) the developer should try to add tests to this test suite.

These tests are contained in a separate repo [AATH](https://github.com/hyperledger/aries-agent-test-harness). They use the gherkin syntax and a http back channel. Changes to the tests need to be added and merged into this repo before they will be reflected in the automatic testing workflows. There has been a lot of work to make developing and debugging tests easier. See (AATH Dev Containers)[https://github.com/hyperledger/aries-agent-test-harness/blob/main/AATH_DEV_CONTAINERS.md#dev-containers-in-aath].

The tests will then be ran for PR's and scheduled workflows for ACA-Py <--> ACA-Py agents. These tests are important because having them allows the AATH project to more easily test credo-ts <--> ACA-Py scenarios and ensure interoperability with mobile agents interacting with python agents.

## ACA-Py specific BDD tests

These tests leverage the [demo agent](../demo/README.md) and also use gherkin syntax and a back channel. See [README](./BDDTests.md).

These tests are another tool for leveraging the demo agent and the gherkin syntax. They should not be used to test features that involve the interop profile, as they can not be used to test against other frameworks. None of the tests that are covered by the AATH tests will be ran automatically. They are here because some developers may prefer the testing strategy and can be useful for explicit testing steps and protocols not included in the interop profile.  

## Scenario testing

These tests utilize the minimal example [agent](https://github.com/Indicio-tech/acapy-minimal-example) produced by Indicio. They exist in the `scenarios` directory. They are very useful for running specific test plans and checking webhooks.
