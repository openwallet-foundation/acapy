# Aries Postman Demo <!-- omit in toc -->

In these demos we will use Postman as our controller client.

## Contents <!-- omit in toc -->

- [Getting Started](#getting-started)
  - [Installing Postman](#installing-postman)
  - [Creating a workspace](#creating-a-workspace)
  - [Importing the environment](#importing-the-environment)
  - [Importing the collections](#importing-the-collections)
  - [Postman basics](#postman-basics)
- [Experimenting with the vc-api endpoints](#experimenting-with-the-vc-api-endpoints)
  - [Register new dids](#register-new-dids)
  - [Issue credentials](#issue-credentials)
  - [Store and retrieve credentials](#store-and-retrieve-credentials)
  - [Verify credentials](#verify-credentials)
  - [Prove a presentation](#prove-a-presentation)
  - [Verify a presentation](#verify-a-presentation)

## Getting Started

Welcome to the Postman demo. This is an addition to the available OpenAPI demo, providing a set of collections to test and demonstrate various aca-py functionalities.

### Installing Postman

Download, install and launch [postman](https://www.postman.com/downloads/).

### Creating a workspace

Create a new postman workspace labeled "acapy-demo".

### Importing the environment

In the environment tab from the left, click the import button. You can paste this [link](https://raw.githubusercontent.com/hyperledger/aries-cloudagent-python/main/demo/postman/environment.json) which is the [environment file](https://github.com/hyperledger/aries-cloudagent-python/blob/main/demo/postman/environment.json) in the ACA-Py repository.

Make sure you have the environment set as your active environment.

### Importing the collections

In the collections tab from the left, click the import button.

The following collections are available:

- [vc-api](https://raw.githubusercontent.com/hyperledger/aries-cloudagent-python/main/demo/postman/collections/vc-api.json)

### Postman basics

Once you are setup, you will be ready to run postman requests. The order of the request is important, since some values are saved dynamically as environment variables for subsequent calls.

You have your environment where you define variables to be accessed by your collections.

Each collection consists of a series of requests which can be configured independently.

## Experimenting with the vc-api endpoints

Make sure you have a demo agent available. You can use the following command to deploy one:

```bash
LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --bg
```

When running for the first time, please allow some time for the images to build.

### Register new dids

The first 2 requests for this collection will create 2 did:keys. We will use those in subsequent calls to issue `Ed25519Signature2020` and `BbsBlsSignature2020` credentials.
Run the 2 did creation requests. These requests will use the `/wallet/did/create` endpoint.

### Issue credentials

For issuing, you must input a [w3c compliant json-ld credential](https://www.w3.org/TR/vc-data-model/) and [issuance options](https://w3c-ccg.github.io/vc-api/#issue-credential) in your request body. The issuer field must be a registered did from the agent's wallet. The suite will be derived from the did method.

```json
{
    "credential":   { 
        "@context": [
            "https://www.w3.org/2018/credentials/v1"
        ],
        "type": [
            "VerifiableCredential"
        ],
        "issuer": "did:example:123",
        "issuanceDate": "2022-05-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123"
        }
    },
    "options": {}
}
```

Some examples have been pre-configured in the collection. Run the requests and inspect the results. Experiment with different credentials.

### Store and retrieve credentials

Your last issued credential will be stored as an environment variable for subsequent calls, such as storing, verifying and including in a presentation.

Try running the store credential request, then retrieve the credential with the list and fetch requests. Try going back and forth between the issuance endpoints and the storage endpoints to store multiple different credentials.

### Verify credentials

You can verify your last issued credential with this endpoint or any issued credential you provide to it.

### Prove a presentation

Proving a presentation is an action where a holder will prove ownership of a credential by signing or demonstrating authority over the document.

### Verify a presentation

The final request is to verify a presentation.
