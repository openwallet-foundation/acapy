# Credential Revocation

These are the ACA-py steps and APIs involved to support credential revocation.

Run ACA-Py with tails server support enabled. You will need to have the URL of an running instance of https://github.com/bcgov/indy-tails-server.

Include the command line parameter `--tails-server-base-url <indy-tails-server url>`

0.  Publish credential definition

    Credential definition is created. All required revocation collateral is also created
    and managed including revocation registry definition, entry, and tails file.

    ```
    POST /credential-definitions
    {
      "schema_id": schema_id,
      "support_revocation": true,
      # Only needed if support_revocation is true. Defaults to 100
      "revocation_registry_size": size_int,
      "tag": cred_def_tag # Optional

    }
    Response:
    {
      "credential_definition_id": "credential_definition_id"
    }
    ```

1.  Issue credential

    This endpoint manages revocation data. If new revocation registry data is required,
    it is automatically managed in the background.

    ```
    POST /issue-credential/send-offer
    {
        "cred_def_id": credential_definition_id,
        "revoc_reg_id": revocation_registry_id
        "auto_remove": False, # We need the credential exchange record when revoking
        ...
    }
    Response
    {
        "credential_exchange_id": credential_exchange_id
    }
    ```

2.  Revoking credential

    ```
    POST /revocation/revoke
    {
        "rev_reg_id": <revocation_registry_id>
        "cred_rev_id": <credential_revocation_id>,
        "publish": <true|false>
    }
    ```

    If publish=false, you must use `​/issue-credential​/publish-revocations` to publish
    pending revocations in batches. Revocation are not written to ledger until this is called.

3.  When asking for proof, specify the timespan when the credential is NOT revoked
    ```
     POST /present-proof/send-request
     {
       "connection_id": ...,
       "proof_request": {
         "requested_attributes": [
           {
             "name": ...
             "restrictions": ...,
             ...
             "non_revoked": # Optional, override the global one when specified
             {
               "from": <seconds from Unix Epoch> # Optional, default is 0
               "to": <seconds from Unix Epoch>
             }
           },
           ...
         ],
         "requested_predicates": [
           {
             "name": ...
             ...
             "non_revoked": # Optional, override the global one when specified
             {
               "from": <seconds from Unix Epoch> # Optional, default is 0
               "to": <seconds from Unix Epoch>
             }
           },
           ...
         ],
         "non_revoked": # Optional, only check revocation if specified
         {
           "from": <seconds from Unix Epoch> # Optional, default is 0
           "to": <seconds from Unix Epoch>
         }
       }
     }
    ```

## Revocation Notification

ACA-Py supports [Revocation Notification v1.0](https://github.com/hyperledger/aries-rfcs/blob/main/features/0183-revocation-notification/README.md).

> **Note:** The optional `~please_ack` is not currently supported.


### Issuer Role

To notify connections to which credentials have been issued, during step 2
above, include the following attributes in the request body:

- `notify` - A boolean value indicating whether or not a notification should be
  sent. If the argument `--notify-revocation` is used on startup, this value
  defaults to `true`. Otherwise, it will default to `false`. This value
  overrides the `--notify-revocation` flag; the value of `notify` always takes
  precedence.
- `connection_id` - Connection ID for the connection of the credential holder.
  This is required when `notify` is `true`.
- `thread_id` - Message Thread ID of the credential exchange message that
  resulted in the credential now being revoked. This is required when `notify`
  is `true`
- `comment` - An optional comment presented to the credential holder as part of
  the revocation notification. This field might contain the reason for
  revocation or some other human readable information about the revocation.

Your request might look something like:

```
POST /revocation/revoke
{
    "rev_reg_id": <revocation_registry_id>
    "cred_rev_id": <credential_revocation_id>,
    "publish": <true|false>,
    "notify": true,
    "connection_id": <connection id>,
    "thread_id": <thread id>,
    "comment": "optional comment"
}
```

### Holder Role

On receipt of a revocation notification, an event with topic
`acapy::revocation-notification::received` and payload containing the thread ID
and comment is emitted on the event bus. This can be handled in plugins to
further customize notification handling.

If the argument `--monitor-revocation-notification` is used on startup, a
webhook with the topic `revocation-notification` and a payload containing the
thread ID and comment is emitted to registered webhook urls.
