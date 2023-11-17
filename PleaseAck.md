# The `please_ack` decorator support in ACA-Py


- [Why is it required?](#why-is-it-required)
- [Proposed solution](#proposed-solution)
  - [The `RECEIPT` option processing](#the-receipt-option-processing)
  - [The `OUTCOME` option processing](#the-outcome-option-processing)
- [Open questions](#open-questions)
  - [Open questions in context of RECEIPT option](#open-questions-in-context-of-receipt-option)
    - [Should we adopt ACK message type in each protocol to handle `RECEIPT`-decorated messages?](#should-we-adopt-ack-message-type-in-each-protocol-to-handle-receipt-decorated-messages)
    - [How to process the ACKs received in response to the `RECEIPT`-decorated messages?](#how-to-process-the-acks-received-in-response-to-the-receipt-decorated-messages)
  - [Open questions in context of OUTCOME option](#open-questions-in-context-of-outcome-option)
    - [When is the outcome is known?](#when-is-the-outcome-is-known)
    - [How to handle an OUTCOME-decorated message if the outcome is not expected?](#how-to-handle-an-outcome-decorated-message-if-the-outcome-is-not-expected)
    - [Compatibility between different versions of ACA-py agents](#compatibility-between-different-versions-of-aca-py-agents)
  - [Open questions in context of both RECEIPT and OUTCOME options](#open-questions-in-context-of-both-receipt-and-outcome-options)
    - [Should the ACK be sent in case response is immediately generated and sent?](#should-the-ack-be-sent-in-case-response-is-immediately-generated-and-sent)
    - [Extending the protocol lifetime](#extending-the-protocol-lifetime)


## Why is it required?

The `please_ack` decorator support is required to meet  the [AIP 2.0 requirements](https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#base-requirements).


## Proposed solution

The `please_ack` decorator supports two options: `RECEIPT` and `OUTCOME`. Although both are parts of the same decorator, they serve different purposes.

The `RECEIPT` option requests "please let me know you have received this message", whereas an `OUTCOME` option requests "please let me know that the processing result is successful".

The main idea is to consider different kinds of `please_ack` separately and process them separately as well.

### The `RECEIPT` option processing

According to the [please-ack RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0317-please-ack) the Aries agent receiving the `RECEIPT` option in the `please_ack` decorator should answer with an ACK message and continue processing according to the particular protocol.

It seems the code for the `please_ack(RECEIPT)` decorator processing can be implemented as a common handler outside the code of protocols.
The common handler doesn't depend on the message-specific handler and can be called before it as a first phase of message processing.


### The `OUTCOME` option processing

Unlike the `RECEIPT` processing of the `OUTCOME` option is protocol-specific. Result itself (in terms of success/failure) and time when it appears depend on the protocol purpose and data being processed.

That means that the `OUTCOME` handler should be a part of the protocol code.


## Open questions

### Open questions in context of RECEIPT option

#### Should we adopt ACK message type in each protocol to handle `RECEIPT`-decorated messages?

The [please-ack RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0317-please-ack) does not define what type of ACK message should be used in responses to `RECEIPT`-decorated messages. As a result it is not possible to implement the common handler until the RFC defines what ACK message type must be used.

There are several options:

1. To use the original `notification/1.0/ack` ACK message type.

  **Advantages:**
  - The common handler doesn't require any specific code to find the particular ACK message type to send in response to the `RECEIPT`-decorated message. It just sends the same `notification/1.0/ack` always.
  - It is not necessary to adopt the ACK message type in each protocol.

  **Disadvantages:**
  - Some protocols (for example, `credential-issue-v2` and `present-proof-v2`) have already adopted ACK for their purposes. Using both the original and adopted ACK message types in the same protocol may be considered inconsistent.
  - It may require many changes of the other ACA-Py code. The ACK message that sent in response to `please_ack` should be processed by the controller's webhook call, for example. The handler (which is the same for all protocols) of `notification/1.0/ack` message type should be able to find the particular protocol manager class (and the `ExchangeRecord` instance for the protocol being executed) using the `~thread` decorator specified in the message. Currently ACA-py uses only `~type` for this purpose. It seems to be non-trivial task.


2. To adopt the `notification/1.0/ack` type in each protocol

  **Disadvantages:**
  - Code duplication. It requires to adopt the ACK message type in each protocol.
  - It requires to change the code of ACK message handlers for the protocols that have already adopted ACK messages since the same message can be received in different protocol states (not only when the protocol is waiting for the final ACK from the other side to terminate the protocol being executed).

3. To use adopted ACK messages if there is an adopted message type in the protocol, to use original ACK message otherwise

  **Advantages:**
  - It is not necessary to adopt the ACK message type in each protocol.
  - If the protocol has already adopted the ACK message the adopted type will be used. There is no unexpected inconsistency (using both the original and adopted ACK message types in the same protocol).

  **Disadvantages:**
  - As it has been already mentioned, it may require many changes of the other ACA-Py code to implement the handler for `notification/1.0/ack` message type.
  - Some additional code is required to find appropriate ACK message type to send as a response.
  - It requires to change the code of ACK message handlers for the protocols that have already adopted ACK messages since the same message can be received in different protocol states (not only when the protocol is waiting for the final ACK from the other side to terminate the protocol being executed).


#### How to process the ACKs received in response to the `RECEIPT`-decorated messages?

There are possible options:

- To put message to logs.
- To call the controller's webhook.


### Open questions in context of OUTCOME option

#### When is the outcome is known?

It may be not easy to determine what is the "outcome" and when it appears for each protocol.

For example, the `credential-issue-v2` protocol. Should the ACK message be sent when the protocol "completes" or after the controller/business process decides to keep the credential?

Another example is the `present-proof-v2` protocol. Should the ACK message be sent when the presentation proof is cryptographically verified, or when the controller/business process decides the proof satisfies the business need?

#### How to handle an OUTCOME-decorated message if the outcome is not expected?

Usually "outcome" in context of the protocol (for example, credentials/proof/etc) is generated by the final step of the protocol. It means that `please_ack(OUTCOME)` is useful to decorate the final message of the particular protocol.

At the same time any message (not only final one) can be decorated with the `please_ack(OUTCOME)` decorator. It is not defined in the [please-ack RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0317-please-ack) how to handle the `please_ack` decorator when the "outcome" is not expected.

Some possible options:

- To ignore the `please_ack(OUTCOME)` if the "outcome" is not expected in the current state of the protocol being executed.
- To consider any message as having some "outcome" and send the ACK in response to it.
- To "remember" that the ACK is requested (via setting some flag in the protocol state instance) and send the ACK in response to final message of the protocol. It is, probably, the worst option since the `please_ack` decorator requests the ACK message in response to the decorated message (according to the [please-ack RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0317-please-ack)).

#### Compatibility between different versions of ACA-py agents

Current ACA-Py code doesn't support the `please_ack`. However some protocols send the ACK message once the interaction is done.

For example, the [0453-issue-credential-v2](https://github.com/hyperledger/aries-rfcs/tree/main/features/0453-issue-credential-v2) protocol implemented in such a way that the `holder` sends the ACK message once credentials are received and verified. In this case the ACK is send unconditionally, no matter if the `please_ack` decorates the message or not. The `issuer` always is waiting for the ACK message before transition to the `DONE` state.

According to [0453-issue-credential-v2 protocol documentation](https://github.com/hyperledger/aries-rfcs/tree/main/features/0453-issue-credential-v2) behavior (for both `holder` and `issuer`) depends on the `please_ack` decorator presence.
The `issuer` must be waiting for the ACK message if the `please_ack (OUTCOME)` decorator is set, otherwise the the `issuer` must transit to the `DONE` state immediately.

What is the problem?

ACA-Py agent acting as the `issuer` is always waiting for the ACK message, no matter if the `please_ack(OUTCOME)` is sent or not.

Let's assume an `issuer` agent is based on current version of code while a `holder` agent is based on new version of code (where `please_ack` is supported).

The `issuer` sends credentials and waits for the ACK. But the `holder`, according to the protocol RFC, doesn't send the ACK message because the `please_ack(OUTCOME)` is not attached by the `issuer`. As a result the `issuer` can't reach the `DONE` state.

The possible option to resolve the issue could be the `0557-discover-features-v2` protocol. The idea is to use `0557-discover-features-v2` protocol to check if the other side supports the `please_ack` decorator or not and behave taking it into account.

For example, the `0557-discover-features-v2` protocol may be executed automatically once a connection between agents is established. The first agent may ask second one if the `please_ack` is supported or not.


### Open questions in context of both RECEIPT and OUTCOME options

#### Should the ACK be sent in case response is immediately generated and sent?

In many protocols a response is immediately generated and sent. What help is sending another message in parallel?

#### Extending the protocol lifetime

The `please_ack` decorator could (in theory) be used to enable "received" and "read" notifications of basic messages, but the "read" notification would extend the protocol lifetime from when the controller received the message, to when an event happened inside the controller.
