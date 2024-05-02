# Credential Revocation in ACA-Py

## Overview

Revocation is perhaps the most difficult aspect of verifiable credentials to
manage. This is true in AnonCreds, particularly in the management of AnonCreds
revocation registries (RevRegs). Through experience in deploying use cases with
ACA-Py we have found that it is very difficult for the controller (the
application code) to manage revocation registries, and as such, we have changed
the implementation in ACA-Py to ensure that it is handling almost all the work
in revoking credentials. The only thing the controller writer has to do is track
the minimum things necessary to the business rules around revocation, such as
whose credentials should be revoked, and how close to real-time should
revocations be published?

Here is a summary of all of the AnonCreds revocation activities performed
by issuers. After this, we'll provide a (much shorter) list of what an ACA-Py
issuer controller has to do. For those interested, there is a more
[complete overview of AnonCreds revocation], including all of the roles, and some details
of the cryptography behind the approach:

- Issuers indicate that a credential will support revocation when creating the
  credential definition (CredDef).
- Issuers create a Revocation Registry definition object of a given size
  (MaxSize -- the number of credentials that can use the RevReg) and publish it
  to the ledger (or more precisely, the verifiable data registry). In doing
  that, a Tails file is also created and published somewhere on the Internet,
  accessible to all Holders.
- Issuers create and publish an initial Revocation Registry Entry that defines
  the state of all credentials within the RevReg, either all active or all
  revoked. It's a really bad idea to create a RevReg starting with "all
  revoked", so don't do that.
- Issuers issue credentials and note the "revocation ID" of each credential. The
  "revocation Id" is a compound key consisting of the RevRegId from which the
  credential was issued, and the index within that registry of that credential.
  An index (from 1 to Max Size of the registry -- or perhaps 0 to Max Size - 1)
  can only be associated with one issued credential.
- At some point, a RevReg is all used up (full), and the Issuer must create another
  one. Ideally, this does not cause an extra delay in the process of issuing credentials.
- At some point, the Issuer revokes the credential of a holder, using the
  revocation Id of the relevant credential.
- At some point, either in conjunction with each revocation, or for a batch of
  revocations, the Issuer publishes the RevReg(s) associated with a CredDef to
  the ledger. If there are multiple revocations spread across multiple RevRegs,
  there may be multiple writes to the ledger.

[complete overview of AnonCreds revocation]: https://github.com/hyperledger/indy-hipe/blob/main/text/0011-cred-revocation/README.md

Since managing RevRegs is really hard for an ACA-Py controller, we have tried to
minimize what an ACA-Py Issuer controller has to do, leaving everything else to be
handled by ACA-Py. Of the items in the previous list, here is what an ACA-Py
issuer controller does:

- Issuers flag that revocation will be used when creating the CredDef and the
  desired size of the RevReg. ACA-Py takes case of creating the initial
  RevReg(s) without further action by the controller.
  - Two RevRegs are initially created, so there is no delay when one fills up,
    and another is needed. In ongoing operations, when one RevReg fills up, the
    other active RevReg is used, and a new RevReg is created.
  - On creation of each RevReg, its corresponding tails file is published by
    ACA-Py.
- On Issuance, the controller receives the logical “revocation ID" (combination
  of RevRegId+Index) of the issued credential to track.
- On Revocation, the controller passes in the logical “revocation ID" of the
  credential to be revoked, including a “notify holder” flag. ACA-Py records the
  revocation as pending and, if asked, sends a notification to the holder using
  a DIDComm message ([Aries RFC 0183: Revocation Notification]).
- The Issuer requests that the revocations for a CredDefId be published. ACA-Py
  figures out what RevRegs contain pending revocation and so need to be
  published, and publishes each.

That is the minimum amount of tracking the controller must do while still being
able to execute the business rules around revoking credentials.

[Aries RFC 0183: Revocation Notification]: https://github.com/hyperledger/aries-rfcs/blob/main/features/0183-revocation-notification/README.md

From experience, we’ve added to two extra features to deal with unexpected
conditions:

- When using an Indy (or similar) ledger, if the local copy of a RevReg gets out
  of sync with the ledger copy (perhaps due to a failed ledger write), the
  Framework can create an update transaction to “fix” the issue. This is needed
  for a revocation state using deltas-type solution (like Indy), but not for a
  ledger that publishes revocation states containing the entire state of each
  credential.
- From time to time there may be a need to [“rotate” a
  RevReg](#revocation-registry-rotation) — to mark existing, active RevRegs as
  “decommissioned”, and create new ones in their place. We’ve added an endpoint
  (api call) for that.

## Using ACA-Py Revocation

The following are the ACA-Py steps and APIs involved in handling credential revocation.

To try these out, use the ACA-Py Alice/Faber demo with tails server support
enabled. You will need to have the URL of an running instance of
[https://github.com/bcgov/indy-tails-server](https://github.com/bcgov/indy-tails-server).

Include the command line parameter `--tails-server-base-url <indy-tails-server url>`

0. Publish credential definition

    Credential definition is created. All required revocation collateral is also created
    and managed including revocation registry definition, entry, and tails file.

    ```json
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

1. Issue credential

    This endpoint manages revocation data. If new revocation registry data is required,
    it is automatically managed in the background.

    ```json
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

2. Revoking credential

    ```json
    POST /revocation/revoke
    {
        "rev_reg_id": <revocation_registry_id>
        "cred_rev_id": <credential_revocation_id>,
        "publish": <true|false>
    }
    ```

    If publish=false, you must use `​/issue-credential​/publish-revocations` to publish
    pending revocations in batches. Revocation are not written to ledger until this is called.

3. When asking for proof, specify the time span when the credential is NOT revoked

    ```json
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

```json
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

## Manually Creating Revocation Registries

> NOTE: This capability is deprecated and will likely be removed entirely in an upcoming release of ACA-Py.

The process for creating revocation registries is completely automated - when you create a Credential Definition with revocation enabled, a revocation registry is automatically created (in fact 2 registries are created), and when a registry fills up, a new one is automatically created.

However the ACA-Py admin api supports endpoints to explicitly create a new revocation registry, if you desire.

There are several endpoints that must be called, and they must be called in this order:

1. Create revoc registry `POST /revocation/create-registry`

   - you need to provide the credential definition id and the size of the registry

2. Fix the tails file URI `PATCH /revocation/registry/{rev_reg_id}`

   - here you need to provide the full URI that will be written to the ledger, for example:

```json
{
  "tails_public_uri": "http://host.docker.internal:6543/VDKEEMMSRTEqK4m7iiq5ZL:4:VDKEEMMSRTEqK4m7iiq5ZL:3:CL:8:faber.agent.degree_schema:CL_ACCUM:3cb5c439-928c-483c-a9a8-629c307e6b2d"
}
```

3. Post the revoc def to the ledger `POST /revocation/registry/{rev_reg_id}/definition`

   - if you are an author (i.e. have a DID with restricted ledger write access) then this transaction may need to go through an endorser

4. Write the tails file `PUT /revocation/registry/{rev_reg_id}/tails-file`

   - the tails server will check that the registry definition is already written to the ledger

5. Post the initial accumulator value to the ledger `POST /revocation/registry/{rev_reg_id}/entry`

   - if you are an author (i.e. have a DID with restricted ledger write access) then this transaction may need to go through an endorser
   - this operation **MUST** be performed on the the new revoc registry def **BEFORE** any revocation operations are performed

## Revocation Registry Rotation

From time to time an Issuer may want to issue credentials from a new Revocation Registry. That can be done by changing the Credential Definition, but that could impact verifiers.
Revocation Registries go through a series of state changes: `init`, `generated`, `posted`, `active`, `full`, `decommissioned`. When issuing revocable credentials, the work is done with the `active` registry record. There are always 2 `active` registry records: one for tracking revocation until it is full, and the second to act as a "hot swap" in case issuance is done when the primary is full and being replaced. This ensures that there is always an `active` registry. When rotating, all registry records (except records in `init` state) are `decommissioned` and a new pair of `active` registry records are created.

Issuers can rotate their Credential Definition Revocation Registry records with a simple call: `POST /revocation/active-registry/{cred_def_id}/rotate`

It is advised that Issuers ensure the active registry is ready by calling `GET /revocation/active-registry/{cred_def_id}` after rotation and before issuance (if possible).
