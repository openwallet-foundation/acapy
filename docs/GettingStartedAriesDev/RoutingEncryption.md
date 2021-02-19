# Deeper Dive: DIDComm Message Routing and Encryption

Many Aries edge agents do not directly receive messages from a peer edge agent - they have agents in between that route messages to them. This is done for many reasons, such as: 

- The agent is on a mobile device that does not have a persistent connection and so uses a cloud agent.
- The person does not want to allow correlation of their agent across relationships and so they use a shared, common endpoint (e.g. https://agents-R-Us.com) that they are "hidden in a crowd".
- An enterprise wants a single gateway to the many enterprise agents they have in their organization.

Thus, when a DIDComm message is sent from one edge agent to another, it is routed per the instructions of the receiver and for the needs of the sender. For example, in the following picture, Alice might be told by Bob to send messages to his phone (agent 4) via agents 9 and 3, and Alice might always send out messages via agent 2.

![image](https://github.com/hyperledger/aries-rfcs/raw/master/features/0067-didcomm-diddoc-conventions/domains.jpg)

The following looks at how those requirements are met with mediators (for example, agents 9 and 3) and relays (agent 2).

## Inbound Routing - Mediators

To tell a sender how to get a message to it, an agent puts into the DIDDoc for that sender a service endpoint for the recipient (with an encryption key) and an ordered list (possibly empty) of routing keys (called "mediators") to use when sending the message. To send the message, the sender must:

- Prepare the message to be sent to the recipient
- Successively encrypt and wrap the message for each intermediate mediator in a "forward" message - an envelope.
- Encrypt and send the message to the first agent in the routing

Note that when an agent uses mediators, it is there responsibility to notify any mediators that need to know of the new relationship that has been formed using the connection protocol and the routing needs of that relationship - where to send messages that arrive destined for a given verkey. Mediator agents have what amounts to a routing table to know when they receive a forward message for a given verkey, where it should go.

Link: [DIDDoc conventions for inbound routing](https://github.com/hyperledger/aries-rfcs/tree/master/features/0067-didcomm-diddoc-conventions)

## Relays

Inbound routing described above covers mediators for the receiver that the sender must know about. In addition, either the sender or the receiver may also have relays they use for outbound messages. Relays are routing agents not known to other parties, but that participate in message routing. For example, an enterprise agent might send all outbound traffic to a single gateway in the organization. When sending to a relay, the sender just wraps the message in another "forward" message envelope.

Link: [Mediators and Relays](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0046-mediators-and-relays)

## Message Encryption

The DIDComm encryption handling is handling within the Aries agent, and not really something a developer building applications using an agent needs to worry about. Further, within an Aries agent, the handling of the encryption is left to libraries to handle - ultimately calling dependencies from Hyperledger Ursa. To encrypt a message, the agent code calls a `pack()` function to handle the encryption, and to decrypt a message, the agent code calls a corresponding `unpack()` function. The "wire messages" (as originally called) are described in [detail here](https://github.com/hyperledger/aries-rfcs/blob/master/features/0019-encryption-envelope/README.md), including variations for sender authenticated and anonymous encrypting. Wire messages were meant to indicate the handling of a message from one agent directly to another, versus the higher level concept of routing a message from an edge agent to a peer edge agent.

Much thought has also gone into repudiable and non-repudiable messaging, as [described here](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0049-repudiation).
