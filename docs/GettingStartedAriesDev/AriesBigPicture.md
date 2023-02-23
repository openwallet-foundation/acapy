# Aries Agents in context: The Big Picture

Aries agents can be used in a lot of places. This classic Indy Architecture picture shows five agents - the four around the outside (on a phone, a tablet, a laptop and an enterprise server) are referred to as "edge agents", and many cloud agents in the blue circle.

![image](https://cryptocalibur.com/wp-content/uploads/2018/06/sovrin-ico-3-600x402.png)

The agents in the picture shares many attributes:

- They have some sort of storage for keys and other data related to their role as an agent
- They interact with other agents using secure. peer-to-peer messaging protocols
- They have some associated mechanism to provide "business rules" to control the behaviour of the agent
  - That is often a person for phone, tablet, laptop, etc. based agents
  - That is often backend enterprise systems for enterprise agents
  - Business rules for cloud agents are often about the routing of messages to and from edge agents

While there can be many other agent setups, the picture above shows the most common ones - edge agents for people, edge agents for organizations and cloud agents for routing messages (although cloud agents could be edge agents. Sigh...). A significant emerging use case missing from that picture are agents embedded within/associated with IoT devices. In the common IoT case, IoT device agents are just variants of other edge agents, connected to the rest of the ecosystem through a cloud agent. All the same principles apply.

Misleading in the picture is that (almost) all agents connect directly to the Ledger network. In this picture it's the Sovrin ledger, but that could be any Indy network (e.g. set of nodes running indy-node software) and in future, ledgers from other providers. That implies most agents embed the ledger SDK (e.g. indy-sdk) and makes calls to the ledger SDK to interact with the ledger and other SDK controlled resources (e.g. secure storage). Thus, unlike what is implied in the picture, edge agents (commonly) do not call a cloud agent to interact with the ledger - they do it directly. Super small IoT devices are an instance of an exception to that - lacking compute/storage resources and/or connectivity, they might communicate with a cloud agent that would communicate with the ledger.

While current Aries agents currently only support Indy-based ledgers, the intention is to add support for other ledgers.

The (most common) purpose of cloud agents is to enable secure and privacy preserving routing of messages between edge agents. Rather than messages going directly from edge agent to edge agent (which is often impossible - for example sending to a mobile agent), messages sent from edge agent to edge agent are routed through a sequence of cloud agents. Some of those cloud agents might be controlled by the sender, some by the receiver and others might be gateways owned by agent vendors (called "Agencies"). In all cases, an edge agent tells routing agents "here's how to send messages to me", so a routing agent sending a message only has to know how to send a peer-to-peer message. While quite complicated, the protocols used by the agents largely take care of this complexity, and most developers don't have to know much about it.

Note the many caveats in this section - "most common", "commonly", etc. There are many small building blocks available in Aries and underlying components that can be combined in infinite ways. We recommend not worrying about the alternate use cases for now. Focus on understanding the common use cases while remembering that other configurations are possible.

We also recommend **not** digging into all the layers described here. Just as you don't have to know how TCP/IP works to write a web app, you don't need to know how indy-node or indy-sdk work to be able to build your first Aries-based application. Later in this guide we'll covering the starting point you do need to know.

> Back to the [Aries Developer - Getting Started Guide](README.md).
