# Developer Demos and Samples of Aries Agent

Here are some demos that developers can use to get up to speed on Aries. You don't have to be a developer to use these. If you can use docker and JSON, then that's enough to give these a try.

## Open API demo

This demo uses agents (and an Indy ledger), but doesn't implement a controller at all. Instead it uses the OpenAPI (aka Swagger) user interface to let you be the controller to connect agents, issue a credential and then proof that credential.

[Collaborating Agents OpenAPI Demo](../../demo/AriesOpenAPIDemo.md)

## Python Controller demo

Run this demo to see a couple of simple Python controller implementations for Alice and Faber. Like the previous demo, this shows the agents connecting, Faber issuing a credential to Alice and then requesting a proof based on the credential. Running the demo is simple, but there's a lot for a developer to learn from the code.

[Python-based Alice/Faber Demo](../../demo/README.md)

## Web App Sample - Email Verification Service

This live service implements a real credential issuer - verifying a user's email address when connecting to an agent and then issuing a "verified email address" credential. This service is used the [IIWBook Demo](https://vonx.io/how_to/iiwbook).

[Email Verification Service](https://github.com/bcgov/indy-email-verification)
