# An overview of Aries messaging

Aries Agents communicate with each other via a message mechanism called DIDComm (DID Communication). DIDComm enables secure, asynchronous, end-to-end encrypted messaging between agents, with messages (usually) routed through some configuration of intermediary agents. Aries agents use (an early instance of) the [did:peer DID method](https://identity.foundation/peer-did-method-spec), which uses DIDs that are not published to a public ledger, but only shared privately between the communicating parties - usually just two agents.

Given the underlying secure messaging layer (routing and encryption covered later in the "Deeper Dive" sections), DIDComm protocols define standard sets of messages to accomplish a task. For example:

* The "establish connection" protocol enables two agents to establish a connection through a series of messages - an invitation, a connection request and a connection response.
* The "issue credential" protocol enables an agent to issue a credential to another agent.
* The "present proof" protocol enables an agent to request and receive a proof from another agent.

Each protocol has a specification that defines the protocol's messages, one or more roles for the different participants, and a state machine that defines the state transitions triggered by the messages. For example, in the connection protocol, the messages are "invitation", "connectionRequest" and "connectionResponse", the roles are "inviter" and "invitee", and the states are "invited", "requested" and "connected". Each participant in an instance of a protocol tracks the state based on the messages they've seen.

Code for protocols are implemented as externalized modules from the core agent code so that they can be included (or not) in an agent deployment. The protocol code must include the definition of a state object for the protocol, handlers for the protocol messages, and the events and administrative messages that are available to the controller to inject business logic into the running of the protocol. Each administrative message becomes part of the REST API exposed by the agent instance.

Developers building Aries agents for a particular use case will generally focus on building controllers. They must understand the protocols that they are going to need, including the events the controller will receive, and the protocol's administrative messages exposed via the REST API. From time to time, such Aries agent developers might need to implement their own protocols.

> Back to the [Aries Developer - Getting Started Guide](README.md).
