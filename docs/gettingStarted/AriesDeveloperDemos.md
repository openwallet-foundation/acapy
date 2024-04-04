# Developer Demos and Samples of Aries Agent

Here are some demos that developers can use to get up to speed on Aries. You don't have to be a developer to use these. If you can use docker and JSON, then that's enough to give these a try.

## Open API demo

This demo uses agents (and an Indy ledger), but doesn't implement a controller at all. Instead it uses the OpenAPI (aka Swagger) user interface to let you be the controller to connect agents, issue a credential and then proof that credential.

[Collaborating Agents OpenAPI Demo](../demo/AriesOpenAPIDemo.md)

## Python Controller demo

Run this demo to see a couple of simple Python controller implementations for Alice and Faber. Like the previous demo, this shows the agents connecting, Faber issuing a credential to Alice and then requesting a proof based on the credential. Running the demo is simple, but there's a lot for a developer to learn from the code.

[Python-based Alice/Faber Demo](../demo/README.md)

## Mobile App and Web Sample - BC Gov Showcase

Try out the [BC Gov Showcase] to download a production Wallet for holding Verifiable Credentials,
and then use your new wallet to get and present credentials in some sample scenarios. The end-to-end
verifiable credential experience in 30 minutes or less.

[BC Gov Showcase]: https://digital.gov.bc.ca/digital-trust/showcase/

## Indicio Developer Demo

Minimal Aca-Py demo that can be used by developers to isolat and test features:

- Minimal Setup (everything runs in containers)
- Quickly reproduce an issue or demonstrate a feature by writing one simple script or pytest tests.

[Indicio Aca-Py Minimal Example](https://github.com/Indicio-tech/acapy-minimal-example)
