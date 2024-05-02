# Reusing a Connection

The Aries [RFC 0434 Out of Band] protocol enables the concept of reusing a
connection such that when using [RFC 0023 DID Exchange] to establish a
connection with an agent with which you already have a connection, you can reuse
the existing connection instead of creating a new one. This is something you
couldn't do a with the older [RFC 0160 Connection Protocol] that we used in the
early days of Aries. It was a pain, and made for a lousy user experience, as on
every visit to an existing contact, the invitee got a new connection.

The requirements on your invitations (such as in the example below) are:

- The invitation `services` item **MUST** be a resolvable DID.
  - Or alternatively, the invitation `services` item **MUST NOT** be an `inline` service.
- The DID in the invitation `services` item is the same one in every invitation.

Example invitation:

```jsonc
{
    "@type": "https://didcomm.org/out-of-band/1.1/invitation",
    "@id": "77489d63-caff-41fe-a4c1-ec7e2ff00695",
    "label": "faber.agent",
    "handshake_protocols": [
        "https://didcomm.org/didexchange/1.0"
    ],
    "services": [
        "did:sov:4JiUsoK85pVkkB1bAPzFaP"
    ]
}
```

[RFC 0434 Out of Band]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0434-outofband
[RFC 0023 DID Exchange]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0023-did-exchange
[RFC 0160 Connection Protocol]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0160-connection-protocol
[RFC 0434 Out of Band invitation]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0434-outofband#invitation-httpsdidcommorgout-of-bandverinvitation
[RFC 0023 DID Exchange request]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0023-did-exchange#1-exchange-request
[RFC 0434 Out of Band reuse]: https://github.com/hyperledger/aries-rfcs/tree/main/features/0434-outofband#reuse-messages

Here's the flow that demonstrates where reuse helps. For simplicity, we'll use the terms "Issuer"
and "Wallet" in this example, but it applies to any connection between any two
agents (the inviter and the invitee) that establish connections with one another.

- The Wallet user is using a browser on the Issuers website and gets to the
  point where they are going to be offered a credential. As part of that flow,
  they are presented with a QR code that they scan with their wallet app.
- The QR contains an [RFC 0434 Out of Band invitation] to connect that the
  Wallet processes as the *invitee*.
- The Wallet uses the information in the invitation to send an [RFC 0023 DID Exchange request]
  DIDComm message back to the Issuer to initiate establishing a connection.
- The Issuer responds back to the `request` with a `response` message, and the
  connection is established.
- Later, the Wallet user returns to the Issuer's website, and does something
  (perhaps starts the process to get another credential) that results in the
  same QR code being displayed, and again the users scans the QR code with their
  Wallet app.
- The Wallet recognizes (based on the DID in the `services` item in the
  invitation -- see example below) that it already has a connection to the
  Issuer, so instead of sending a DID Exchange `request` message back to the
  Issuer, they send an [RFC 0434 Out of Band reuse] DIDComm message, and both
  parties know to use the existing connection.
  - Had the Wallet used the DID Exchange `request` message, a new connection
    would have been established.

The [RFC 0434 Out of Band] protocol requirement enables `reuse` message by the
invitee (the Wallet in the flow above) is that the `service` in the invitation
**MUST** be a resolvable DID that is the same in all of the invitations. In the
example invitation above, the DID is a `did:sov` DID that is resolvable on a public
Hyperledger Indy network. The DID could also be a [Peer DID] of types 2 or 4,
which encode the entire DIDDoc contents into the DID identifier (thus they are
"resolvable DIDs"). What cannot be used is either the old "unqualified" DIDs
that were commonly used in Aries prior to 2024, and [Peer DID] type 1. Both of
those have DID types include both an identifier and a DIDDoc in the `services`
item of the Out of Band invitation. As noted in the Out of Band specification,
`reuse` cannot be used with such DID types even if the contents are the same.

[Peer DID]: https://identity.foundation/peer-did-method-spec/

Example invitation:

```jsonc
{
    "@type": "https://didcomm.org/out-of-band/1.1/invitation",
    "@id": "77489d63-caff-41fe-a4c1-ec7e2ff00695",
    "label": "faber.agent",
    "handshake_protocols": [
        "https://didcomm.org/didexchange/1.0"
    ],
    "services": [
        "did:sov:4JiUsoK85pVkkB1bAPzFaP"
    ]
}
```

The use of connection reuse can be demonstrated with the Alice / Faber demos as
follows. We assume you have already somewhat familiar with your options for
running the [Alice Faber Demo] (e.g. locally or in a browser). Follow those
instruction up to the point where you are about to start the Faber and Alice agents.

[Alice Faber Demo]: ../demo/README.md

1. On a command line, run Faber with these parameters: `./run_demo faber
   --reuse-connections --public-did-connections --events`.
2. On a second command line, run Alice as normal, perhaps with the `events`
   option: `./run_demo alice --reuse-connections --events`
3. Copy the invitation from the Faber terminal and paste it into the Alice
   terminal at the prompt.
4. Verify that the connection was established.
   1. If you want, go to the Alice OpenAPI screen (port `8031`, path
      `api/docs`), and then use the `GET Connections` to see that Alice has one
      connection to Faber.
5. In the Faber terminal, type `4` to get a prompt for a new connection. This
   will generate a new invitation with the same public DID.
6. In the Alice terminal, type `4` to get a prompt for a new connection, and
   paste the new invitation.
7. Note from the webhook events in the Faber terminal that the `reuse` message
   is received from Alice, and as a result, no new connection was created.
   1. Execute again the `GET Connections` endpoint on the Alice OpenAPI screen
      to confirm that there is still just one established connection.
8. Try running the demo again **without** the `--reuse-connections` parameter and
   compare the `services` value in the new invitation vs. what was generated in
   Steps 3 and 7. It is not a DID, but rather a one time use, inline DIDDoc
   item.

While in the demo Faber uses in the invitation the same DID they publish as an
issuer (and uses in creating the schema and Cred Def for the demo), Faber could
use any *resolvable* (not inline) DID, including DID Peer types 2 or 4 DIDs, as
long as the DID is the same in every invitation. It is the fact that the DID is
always the same that tells the invitee that they can reuse an existing connection.

For example, to run faber with connection reuse using a non-public DID:

``` bash
./run_demo faber --reuse-connections --events
```

To run faber using a `did:peer` and reusable connections:

``` bash
./run_demo faber --reuse-connections --emit-did-peer-2 --events
```

To run this demo using a multi-use invitation (from Faber):

``` bash
./run_demo faber --reuse-connections --emit-did-peer-2 --multi-use-invitations --events
```
