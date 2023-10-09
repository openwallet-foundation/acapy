# `please_ack` decorator support in ACA-Py


- [List of protocols that include `please_ack` decorator](#list-of-protocols-that-include-please_ack-decorator)
- [Possible options to hande the `please_ack` decorator](#possible-options-to-hande-the-please_ack-decorator)
  - [Option 1: common handler](#option-1-common-handler)
    - [Problems](#problems)
      - [The common handler doesn't exist yet](#the-common-handler-doesnt-exist-yet)
      - [`ack` message type](#ack-message-type)
      - [`OUTCOME` acknowledge is protocol-specific](#outcome-acknowledge-is-protocol-specific)
      - [There are more than one point of decision whether to send `ack` or not](#there-are-more-than-one-point-of-decision-whether-to-send-ack-or-not)
      - [Possibility to send an `ack` when it is not allowed by the protocol](#possibility-to-send-an-ack-when-it-is-not-allowed-by-the-protocol)
  - [Option 2: support for `please_ack` in each protocol separately](#option-2-support-for-please_ack-in-each-protocol-separately)
  - [Option 3: common handler ('RECEIPT') + support in each protocol ('OUTCOME')](#option-3-common-handler-receipt--support-in-each-protocol-outcome)
- [Conclusions](#conclusions)
- [Open questions](#open-questions)
  - [List of protocols](#list-of-protocols)
  - [Unexpected `please_ack`](#unexpected-please_ack)
  - [Compatibility between different versions of ACA-py agents](#compatibility-between-different-versions-of-aca-py-agents)
  - [`0454-present-proof-v2` protocol issue](#0454-present-proof-v2-protocol-issue)


## List of protocols that include `please_ack` decorator

There is a [list of protocols](https://github.com/search?q=repo%3Ahyperledger%2Faries-rfcs+please&type=code) whos documentation mentions a `please_ack` decorator:

- [0030-sync-connection/abandon-connection-protocol](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0030-sync-connection/abandon-connection-protocol/README.md)
- [0721-revocation-notification-v2](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0721-revocation-notification-v2/README.md)
- [0193-coin-flip](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0193-coin-flip/README.md)
- [0453-issue-credential-v2](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0453-issue-credential-v2/README.md)
- [0454-present-proof-v2](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0454-present-proof-v2/README.md)
- [0183-revocation-notification](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0183-revocation-notification/README.md)
- [0028-introduce](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0028-introduce/README.md)
- [0035-report-problem](https://github.com/hyperledger/aries-rfcs/blob/097053c6e91f16d4dad18b5367cf338721423dc7/features/0035-report-problem/README.md)


## Possible options to hande the `please_ack` decorator

There are, at least, three possible ways to implement support of `please_ack` decorator:

1. to create a common code (outside the code of protocols) as a handler to response with an `ack` to message which contains the `please_ack` decorator
2. to implement such code in each protocol (in fact, message handler) where it is required
3. to implement both common code and protocol-specific code for different options specified in `please_ack` (`RECEIPT`/`OUTCOME`)


### Option 1: common handler

The common handler can be implemented, for example, as functions that are called before and/or after the message-specific handler call.

**Advantages:**
- `please_ack(on=['RECEIPT'])` decorator handler is implemented once for all protocols


**Disadvantages:**
- current design of `ACA-py` doesn't support that, so the code of `Dispatcher` class has to be changed
- it's difficult (or impossible) to find an appropriate `ack` message type from the code implemented outside of the specific protocol
- it's impossible to change state of the protocol (in case it is required according to the protocol specification) since sending of the `ack` message is done by common code outside the protocol message handlers
- a handler for `please_ack(on=['OUTCOME'])` is protocol-specific. It's difficult (or even impossible) to implement it as a common code for all protocols
- there are conflicts with current protocol implementations (that already send `ack`), protocols have to be changed (for example, `0453-issue-credential-v2`)
- message-specific handler implementations imply sending `ack` messages from the common code. It makes the code less obvious
- possible duplication of `ack` messages (from both the common handler and specific message handler)


#### Problems

##### The common handler doesn't exist yet

Currently the `ACA-py` code doesn't have a common handler for all message types. Each message is processed in a message-specific handler which is implemented as a part of the protocol.
To make the `please_ack` processing a common feature for all protocols the `dispatcher.py` (or the `base_handler.py`) should be changed to add support for the common handler to process all messages before/after a message-specific handler is called. It would change the current design where each message is processed only by a single message-specific handler implemented as a part of particilar protocol. Message processing code would be scattered across several files (common handler and message-specific handler).

##### `ack` message type

The `ack` message type depends on particular protocol being processed.
For example, `0454-present-proof-v2` protocol includes a specific type for `ack` messages. The `V20PresAck` message type extends the common `V10Ack` type defined by notification protocol with the new field `verification_result`.
If the `please_ack` decorator is handled by some common handler it is impossible to send `ack` of specific type.


##### `OUTCOME` acknowledge is protocol-specific

It seems hard (or even impossible) to handle `please_ack` decorator with `on=['OUTCOME']` in the common handler since the handler doesn't have any information about result of message processing done by the message-specific protocol handler.
For example, if the issued credentials is not accepted by holder, message-specific handler sends a `problem_report` message. Depending on the result of processing in the message-specific handler common hanler must either send `status=OK` or send nothing. But the common handler doesn't have result of processing (unless special code is implemented for that purpose).

Assume the common handler "knows" the result produced by the message-specific handler. In that case an `ack (STATUS=OK)` message is sent by the common handler. But the `problem_report` (in case of any problems) is sent by the message-specific handler. It seems to be bad design of code. It is better when both `ack` and `problem_report` are sent from the same layer of the code.


##### There are more than one point of decision whether to send `ack` or not

Some protocols may define more than a single condition to decide whether to send an `ack` message or not.
For example, the `0454-present-proof-v2` protocol defines the following conditions to send an `ack`:

- the `will_confirm` field in the `request-presentation` message is set to true
- the `please_ack` decorator is included into the `presentation` message

This example shows that message-specific handler must take into account such cases in order to prevent duplication of `ack` messages. It requires protocol implementations (at least, `0454-present-proof-v2`) to be changed. It is not a good idea since it requires additional effort to change the code of handlers and, even worse, creates implicit dependencies between the common handler and the message-specific handlers in such cases.


##### Possibility to send an `ack` when it is not allowed by the protocol

When the message is being processed only by single message-specific handler any corrupted messages can be detected.
On the other hand, in case when the common handler doesn't take into account the current state of the protocol being processed it becomes possible to add the `please_ack` decorator in the message that must not have the `please_ack` according to the protocol. In this case the common handler may send an `ack` message in response to some message with the `please_ack` decorator even if it is not allowed by the protocol. Then this corrupted message will be processed by the message-specific protocol.


### Option 2: support for `please_ack` in each protocol separately

It seems easier to implement the `please_ack` support in all message-specific handlers that should have it. 

**Advantages:**
- it is not neccessary to change base logic of `ACA-py` code (for example, `core/dispatcher.py`).
- there is no implicit dependencies (it is not neccessary to keep in mind any logic that is executed outside the message handlers implemented in the protocol)
- it is possible to add the `please_ack` support step-by-step (first protocol, second one, etc.)

**Disadvantages:**
- each protocol should implement the `please_ack` support seperately
- only message handlers that implement it explicitly are able to react on the `please_ack` decorator

In fact, it seems there are not many disadvantages of this approach. None of them looks so serious. In the same time amount of the additional code to handle the `please_ack` decorator is expected to be quite small.

### Option 3: common handler ('RECEIPT') + support in each protocol ('OUTCOME')

The idea is to consider different kinds of `please_ack` separately and process them seperately as well.

`please_ack(on=['RECEIPT'])` is a decorator that requests "please let me know you have received this message". There should be the same behaviour in all protocols (to send an `ack` message and call the message-specific handler). It seems the code for the `please_ack(on=['RECEIPT'])` decorator processing can be implemented as a common handler outside the code of protocols. The common handler doesn't depend on message-specific handler and can be called before it.

On the other hand an `please_ack(on=['OUTCOME'])` is a decorator that requests "please let me know that the processing result is successful". Unlike the `please_ack(on=['RECEIPT'])` processing of the `please_ack(on=['OUTCOME'])` is protocol-specific:
- protocol-specific type of an `ack` message
- result (in terms of success/failure) depends on the protocol and behaviour (to send an `ack` or `problem_report`) depends on the protocol as well.

That means that it is a good idea to implement support for the `OUTCOME` decorator as a part of code of each protocol where it is expected.

The `RECEIPT` option is processed by the common handler. If there is only `RECEIPT` option in `please_ack` the common handler returns the `ack (status=OK)`. If both `RECEIPT` and `OUTCOME` are specified the common handler returns the `ack (status=PENDING)`.

The `OUTCOME` is processed by the message-specific handler.

**Advantages:**
- no code duplication - `please_ack(on=['RECEIPT'])` decorator handler is implemented once for all protocols
- the `please_ack(on=['RECEIPT'])` support is implemented for all protocols and all message types, not limited by only ones where it is explicitly expected by the protocol

**Disadvantages:**
- current design of `ACA-py` doesn't support that, so the code of `Dispatcher` class has to be changed
- it is required to adopt `ack` message type in each protocol in order to be able to send an adopted type of `ack` message in response to `please_ack(on=['RECEIPT'])`
- implicit dependency between the common handler and the message-specific handler - developers who implement new protocols should keep in mind that message handler must ignore `please_ack(on=['RECEIPT'])` decorator


## Conclusions

- Option 1 doesn't seem like a good choice due to implementation problems
- Option 2 seems easy to implement, but the `please_ack` decorator is only handled when it is expected by the protocol message handlers implementation (unexpected `please_ack` will be ignored)
- Option 3 allows to answer with an `ack` message to any messages that include the `please_ack(on=['RECEIPT'])` decorator. It allows the initiator to know if the message was received by the other side or not. Although it seems like the best option it requires some changes of code design.

The final decision depends on the answer to the question "do we need to support the `please_ack` in all messages?". If yes, the option 3 is only possible. If not, the option 2 can be implemented.

According to the [please_ack documentation](https://github.com/hyperledger/aries-rfcs/tree/main/features/0317-please-ack#requesting-an-ack-please_ack) we should support the `please_ack` in all messages:

> Suppose Alice likes to bid at online auctions. Normally she may submit a bid and be willing to wait for the auction to unfold organically to see the effect. But if she's bidding on a high-value item and is about to put her phone in airplane mode because her plane's ready to take off, she may want an immediate ACK that the bid was accepted.


## Open questions

### List of protocols

There is a list of protocols above where the `please_ack` is mentioned explicitly.

**Is there any better approach to find the full list of protocols to implement the `please_ack` decorator support?**

### Unexpected `please_ack`

**Should an ACA-py agent ignore the `please_ack` decorator if it is not expected according to the protocol?**

This questions determines the possible implementation as mentioned above.
In case of option 2 the `please_ack` will be just ignored in all messages where it is not expected explicitly. Will it be correct?


### Compatibility between different versions of ACA-py agents

According to [0453-issue-credential-v2 protocol documentation](https://github.com/hyperledger/aries-rfcs/tree/main/features/0453-issue-credential-v2) states of the protocol (for both `holder` and `issuer`) depend on the `please_ack` decorator presence:

If the `please_ack` is set an `issuer` moves through the states `REQUEST_RECEIVED` -> `STATE_ISSUED` -> `DONE`.

If the `please_ack` is not set an `issuer` moves through the states `REQUEST_RECEIVED` -> `DONE`.

Current ACA-py implementation doesn't support the `please_ack` therefore an `issuer` always moves through `STATE_ISSUED` state. An `issuer` in this state expects an `ack` from a `holder` that will not be sent in case if the `holder's` agent is based on the new version of code.
It means that agents based on different versions of `ACA-py` (current and new one that support the `please_ack`) will be incompatible.


### `0454-present-proof-v2` protocol issue

According to the [0454-present-proof-v2 protocol documentation](https://github.com/hyperledger/aries-rfcs/tree/main/features/0454-present-proof-v2#choreography-diagram) a `verifier` must validate received `present-proof` and send a `problem_report` in case the `present-proof` is not valid.

But the `ACA-py` implementation sends an `ack` (with `verification_result=False`) when validation fails:

```
    async def verify_pres(
        self, pres_ex_record: V20PresExRecord, responder: Optional[BaseResponder] = None
    ):
...
        for format in input_formats:
            pres_exch_format = V20PresFormat.Format.get(format.format)

            if pres_exch_format:
                pres_ex_record = await pres_exch_format.handler(
                    self._profile
                ).verify_pres(
                    pres_ex_record,
                )
                if pres_ex_record.verified == "false":
                    break

        pres_ex_record.state = V20PresExRecord.STATE_DONE

        async with self._profile.session() as session:
            await pres_ex_record.save(session, reason="verify v2.0 presentation")

        if pres_request_msg.will_confirm:
            await self.send_pres_ack(pres_ex_record, responder)

        return pres_ex_record


    async def send_pres_ack(
        self, pres_ex_record: V20PresExRecord, responder: Optional[BaseResponder] = None
    ):
...
        if responder:
            pres_ack_message = V20PresAck(verification_result=pres_ex_record.verified)
            pres_ack_message._thread = {"thid": pres_ex_record.thread_id}
            pres_ack_message.assign_trace_decorator(
                self._profile.settings, pres_ex_record.trace
            )

            await responder.send_reply(
                pres_ack_message,
                # connection_id can be none in case of connectionless
                connection_id=pres_ex_record.connection_id,
            )
...
```

It looks like the `ACA-py` code doesn't behave correctly in case of failed `present-proof` validation.

