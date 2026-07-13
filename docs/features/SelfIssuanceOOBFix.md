# Self-Issuance / Self-Connection OOB and DID Exchange Fixes

## Issue

[openwallet-foundation/acapy#3300](https://github.com/openwallet-foundation/acapy/issues/3300)

When an agent creates an out-of-band (OOB) invitation and receives that same
invitation back into its own wallet — the "self-issuance" pattern, where an
agent issues a credential to itself, or more generally any self-connection —
two distinct errors could occur.

### Bug 1: `StorageDuplicateError` (no prior handshake)

Reproduction: create an OOB invitation with an attached credential offer (no
`handshake_protocols`), then receive that invitation on the same wallet.

```
aries_cloudagent.storage.error.StorageDuplicateError: Multiple OobRecord
records located for {'invi_msg_id': '...'}
```

**Cause:** `OobMessageProcessor.find_oob_record_for_inbound_message`
(`acapy_agent/core/oob_processor.py`) looked up the `OobRecord` for an inbound
message using only `invi_msg_id`:

```python
oob_record = await OobRecord.retrieve_by_tag_filter(
    session,
    {"invi_msg_id": context.message_receipt.parent_thread_id},
)
```

In a self-connection, creating and then receiving the same invitation
produces **two** `OobRecord`s that share the same `invi_msg_id`: one with
`role=sender` (from `create-invitation`) and one with `role=receiver` (from
`receive-invitation`). `retrieve_by_tag_filter` requires a unique match, so
it raised `StorageDuplicateError` instead of returning either record.

**Fix:** on `StorageDuplicateError`, disambiguate by message type. Some
message types (a did-exchange `request`, or an RFC 0434 handshake-reuse
message) are always sent by the *receiver* of an invitation back to the
*sender*, and must be matched against the `role=sender` record. All other
message types (e.g. an attached credential offer or presentation request)
are sent by the sender to the receiver, and must be matched against the
`role=receiver` record.

### Bug 2: `DIDXManagerError` ("No corresponding connection request found")

Reproduction: create an OOB invitation with `handshake_protocols` *and* an
attached credential offer, then receive it back into the same wallet
(the true self-issuance flow: establish a connection and deliver a
credential offer in one invitation).

```
aries_cloudagent.protocols.didexchange.v1_0.manager.DIDXManagerError:
No corresponding connection request found
```

**Cause:** in a self-connection, ACA-Py creates **two `ConnRecord`s in the
same wallet** — one per did-exchange role (the wallet plays both the
inviter/responder and the invitee/requester side of the same invitation).
When the attached credential offer is processed,
`find_oob_record_for_inbound_message`'s "connection reuse" cleanup logic
(designed for the legitimate RFC 0434 case where an existing connection is
reused instead of a stale, abandoned handshake attempt) saw that the
inviter-side `ConnRecord`'s `connection_id` didn't match the inbound
message's `connection_id`, assumed the inviter-side record was stale, and
**deleted it**:

```python
LOGGER.debug(f"Removing stale connection {oob_record.connection_id} due to connection reuse")
if oob_record.connection_id:
    async with context.profile.session() as session:
        old_conn_record = await ConnRecord.retrieve_by_id(session, oob_record.connection_id)
        await old_conn_record.delete_record(session)
```

That record was not stale — it was the wallet's own other-role `ConnRecord`,
still waiting for its own `DIDXComplete` message. Once deleted, the inbound
`DIDXComplete` had no record to attach to, producing the error.

**Fix:** before deleting, check whether the "old" and "new" connection
records have **reciprocal DIDs** (`old.my_did == new.their_did` and
`old.their_did == new.my_did`). This pattern only occurs when one wallet is
playing both roles of the same connection (self-connection); two genuinely
distinct parties' connections never end up with swapped-matching DIDs. When
detected, skip the deletion — the genuine stale-connection cleanup path
(distinct parties, non-reciprocal DIDs) is unchanged.

### Supporting fix: redundant state saves

`DIDXManager.receive_invitation` and `DIDXRequestHandler.handle` re-saved
`ConnRecord.state` immediately after sending a request/response. In a
self-connection, delivering that message can synchronously drive the rest of
the handshake to completion (via `send_reply`/`send`) before the redundant
save runs, regressing an already-completed connection back to an earlier
state. `create_request`/`create_response` already persist the correct state
before sending, so these extra saves were removed.

## Verification

Regression tests were added, parametrized across the `askar` and
`askar-anoncreds` wallet backends (the fix has no wallet-backend-specific
logic, and applies identically to `kanon-anoncreds`):

- `acapy_agent/core/tests/test_oob_processor.py`
  - `test_self_issuance_oob_attachment_without_connection` — bug 1
  - `test_self_issuance_connectionless_full_round_trip` — full connectionless
    self-issuance round trip
  - `test_find_oob_record_for_inbound_message_self_connection_not_deleted` —
    bug 2's actual root cause (reuse-cleanup misfire)
  - `test_find_oob_record_for_inbound_message_sender_connection_id_no_match` —
    pre-existing test confirming the genuine connection-reuse cleanup path
    (distinct parties) is unaffected
- `acapy_agent/protocols/didexchange/v1_0/tests/test_manager.py`
  - `test_self_connection_didx_handshake_to_completion` — full self-connection
    did-exchange handshake reaches `completed` for both of the wallet's own
    `ConnRecord`s
  - `test_two_party_didx_handshake_no_regression` — normal two-party
    did-exchange handshake is unaffected

Confirmed against a live self-issuance reproduction (OOB invitation with
`handshake_protocols` + an attached credential offer, received into the same
wallet) that previously produced the exact `DIDXManagerError` traceback from
issue #3300; the error no longer occurs after this fix.
