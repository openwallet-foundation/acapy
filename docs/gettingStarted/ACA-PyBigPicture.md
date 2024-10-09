# ACA-Py Agents in context: The Big Picture

ACA-Py agents can be used in a lot of places. This classic Indy Architecture picture shows five agents - the four around the outside (on a phone, a tablet, a laptop and an enterprise server) are referred to as "edge agents", and many cloud agents in the blue circle.

![image](https://cryptocalibur.com/wp-content/uploads/2018/06/sovrin-ico-3-600x402.png)

The agents in the picture shares many attributes:

- They have some sort of storage for keys and other data related to their role as an agent
- They interact with other agents using secure, peer-to-peer messaging protocols
- They have some associated mechanism to provide "business rules" to control the behavior of the agent
  - That is often a person for phone, tablet, laptop, etc. based agents
  - That is often backend enterprise systems for enterprise agents
  - Business rules for cloud agents are often about the routing of messages to and from edge agents

While there can be many other agent setups, the picture above shows the most common ones - mobile wallets for people, edge agents for organizations and cloud agents for routing messages (although cloud agents could be edge agents. Sigh...). A significant emerging use case missing from that picture are agents embedded within/associated with IoT devices. In the common IoT case, IoT device agents are just variants of other edge agents, connected to the rest of the ecosystem through a cloud agent. All the same principles apply.

Misleading in the picture is that (almost) all agents connect directly to the verifiable data repository. In this picture it's the Sovrin ledger, but that could be any ledger (e.g. set of nodes running ledger software) or non-ledger based verifiable data repositories -- such as web servers. That implies most agents embed a verifiable data registry client (usually, a DID Resolver) that makes calls to one or more types of verifiable data registries. Thus, unlike what is implied in the picture, edge agents (commonly) do not call a cloud agent to interact with the verifiable data registry - they do it directly. Super small IoT devices might be an exception to that - lacking compute/storage resources and/or connectivity, they might communicate with a cloud agent that would communicate with the verifiable data registry.

The three most common purposes of cloud agents are verifiable credential issuers, verifiers and "mediators" -- agents that route messages to mobile wallets that lack a persistent endpoint. For the latter, rather than messages going directly to mobile wallet (which is often impossible - for example sending to a mobile wallet), messages intended for the agent are routed through a mediator who hold the messages until the agent picks up its messages.

We also recommend **not** digging into all the layers described here. Just as you don't have to know how TCP/IP works to write a web app, you don't need to know how ledgers or the various protocols work to be able to build your first ACA-Py-based application. Later in this guide we'll covering the starting point you do need to know.

> Back to the [ACA-Py Developer - Getting Started Guide](./README.md).
