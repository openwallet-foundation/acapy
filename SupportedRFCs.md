# Aries RFCs Supported in aries-cloudagent-python

`aries-cloudagent-python` implements the specifications and protocols that are documented primarily in the [aries-rfcs](https://github.com/hyperledger/aries-rfcs). The following is a curated and generally up to date list of the RFCs that are supported by `aries-cloudagent-python`. We try to keep this list up to date, but if you have any questions, please contact us on the #aries channel on [Hyperledger Rocketchat](https://chat.hyperledger.org) or through an issue in this repo. The list is divided into the same two sections as the Aries RFCs-concepts and features. A third section describes some features of the agent that are not yet captured by RFCs, or that are described by [Indy HIPEs](https://github.com/hyperledger/indy-hipe).

## Aries RFC Concepts

- [0003-protocols](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0003-protocols)
- [0004-agents](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0004-agents)
- [0005-didcomm](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0005-didcomm)
- [0008-message-id-and-threading](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0008-message-id-and-threading)
- [0011-decorators](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0011-decorators)
- [0017-attachments](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0017-attachments)
- [0020-message-types](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0020-message-types)
- [0046-mediators-and-relays](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0046-mediators-and-relays)
- [0047-json-LD-compatibility](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0047-json-ld-compatibility)
- [0050-wallets](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0050-wallets)
- [0094-cross-domain messaging](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0094-cross-domain-messaging)

## Aries RFC Features

- [0019-encryption-envelope](https://github.com/hyperledger/aries-rfcs/tree/master/features/0019-encryption-envelope)
- [0160-connection-protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0160-connection-protocol)
  - The agent supports Connection/DID exchange initiated from both plaintext invitations and public DIDs that enable bypassing the invitation message.
  - Note that the [did:peer DID Method](https://github.com/openssi/peer-did-method-spec) is not yet supported. We are currently exploring the specification and considering the impact of how the agent will support the specification.
  - The [0030-sync-connection](https://github.com/hyperledger/aries-rfcs/tree/master/features/0030-sync-connection) protocol is also not yet supported, meaning that a pairwise DID, once exchanged, cannot be updated.
- [0035-didcomm-transports](https://github.com/hyperledger/aries-rfcs/tree/master/features/0025-didcomm-transports)
  - The agent currently supports HTTP and WebSockets for both inbound and outbound messaging. Transports are pluggable and an agent instance can use multiple inbound and outbound transports.
- [0031-discover-features](https://github.com/hyperledger/aries-rfcs/tree/master/features/0031-discover-features)
- [0032-message-timing](https://github.com/hyperledger/aries-rfcs/tree/master/features/0032-message-timing)
- [0035-report-problem](https://github.com/hyperledger/aries-rfcs/tree/master/features/0035-report-problem)
  - Claiming support for this protocol is tricky. The intention of this protocol is that it define a standard mechanism for handling errors in executing a protocol. However, the error handling is in the context of each protocol. Thus, while this protocol is technically supported in the agent, it is adopted by each protocol and thus it's handling is specific to each protocol.
- [0036-issue-credential](https://github.com/hyperledger/aries-rfcs/tree/master/features/0036-issue-credential) - see [PR #60](https://github.com/hyperledger/aries-cloudagent-python/pull/60)
  - This agent (along with a number of other agents in the community) also has deprecated support for [Version 0.1](https://hackmd.io/s/HkklVzww4) of the issue credential protocol.
- [0037-present-proof](https://github.com/hyperledger/aries-rfcs/tree/master/features/0037-present-proof)
  - This agent (along with a number of other agents in the community) also has deprecated support for [Version 0.1](https://hackmd.io/s/HkklVzww4) of the present proof protocol.
- [0048-trust-ping](https://github.com/hyperledger/aries-rfcs/tree/master/features/0048-trust-ping)
- [0067-didcomm-diddoc-conventions](https://github.com/hyperledger/aries-rfcs/tree/master/features/0067-didcomm-diddoc-conventions)
- [0092-transport-return-route](https://github.com/hyperledger/aries-rfcs/tree/master/features/0092-transport-return-route)
  - Support for this RFC makes ACA-Py a great candidate to be the persistent endpoint cloud agent for a mobile agent.
- [0095-basic-message](https://github.com/hyperledger/aries-rfcs/tree/master/features/0095-basic-message)

## Other Capabilities

- An Adminstrative API is core to the functionality of the ACA-Py implementation. The Administrative API is extended by each protocol deployed in an instance of ACA-Py. Each protocol provides a set of HTTP JSON requests to control the use of the protocol. With the Adminstrative API, a controller application can initiate instances of protocols (for example, issuing a credential) and can respond to events triggered by protocols started by other agents and protocols that are in flight. See the [Admin API documentation](AdminAPI.md) for more details.
- Protocol events are triggered as messages are received from other agents. The events are sent using a webhook mechanism to a controller for the ACA-Py agent instance. The controller is expected to handle the event, potentially responding by sending a request to the Administrative API. See the [Admin API documentation](AdminAPI.md) for more details.
- [Action Menu](https://hackmd.io/s/HkpyhdGtV) is a protocol to enable a simple request/response mechanism between agents. We anticipate using the mechanism to enable (for example) an enterprise agent to send a list of actions to a connected agent used by a person. From the menu, the person can select an action (possibly with a text parameter), triggering the enterprise agent to take some action. Think of it like an Interactive Voice Response (IVR) system used in automated call handling system. Just not as annoying.
  - An Aries RFC for Action Menu will be introduced Real Soon Now.
