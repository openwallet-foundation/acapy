# Aries Cloud Agent Python (ACA-py) Demo Controllers

Web controllers for [demo](https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo) cloud agents aimed primarily at business or first-time aries developers.

There are 3 flavours of controllers each with their own instructions on setup:

1. Faber is a .NET + Blazor hybrid server/client application
2. Acme is an Express.js (Node.js) server application
3. Alice is an Angular client application

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running Controllers](#running-controllers)

### Prerequesites

Controllers are dependent on their respective cloud agents. Please follow instructions for [running agents locally](https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo#running-locally) or [running agents in docker](https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo#running-in-docker) as controllers wont do anything if agents are not running. The demo also relies on running an Hyperledget Indy ledger. Is is recommended to use the `von-network` developed for these demos. Instructions for setting up the `von-network` are included in the linked agent setup documentation.

### Running Controllers

Instructions for running each controller are provided in their respecitve directories.