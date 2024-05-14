# Qualified DIDs In ACA-Py

## Context

In the past, ACA-Py has used "unqualified" DIDs by convention established early on in the Aries ecosystem, before the concept of Peer DIDs, or DIDs that existed only between peers and were not (necessarily) published to a distributed ledger, fully matured. These "unqualified" DIDs were effectively Indy Nyms that had not been published to an Indy network. Key material and service endpoints were communicated by embedding the DID Document for the "DID" in DID Exchange request and response messages.

For those familiar with the DID Core Specification, it is a stretch to refer to these unqualified DIDs as DIDs. Usage of these DIDs will be phased out, as dictated by [Aries RFC 0793: Unqualified DID Transition][rfc0793]. These DIDs will be phased out in favor of the `did:peer` DID Method. ACA-Py's support for this method and it's use in DID Exchange and DID Rotation is dictated below.

[rfc0793]: https://github.com/hyperledger/aries-rfcs/blob/50d148b812c45af3fc847c1e7033b084683dceb7/features/0793-unqualfied-dids-transition/README.md

## DID Exchange

When using DID Exchange as initiated by an Out-of-Band invitation:

- `POST /out-of-band/create-invitation` accepts two parameters (in addition to others):
  - `use_did_method`: a DID Method (options: `did:peer:2` `did:peer:4`) indicating that a DID of that type is created (if necessary), and used in the invitation. If a DID of the type has to be created, it is flagged as the "invitation" DID and used in all future invitations so that connection reuse is the default behaviour.
    - This is the recommend approach, and we further recommend using `did:peer:4`.
  - `use_did`: a complete DID, which will be used for the invitation being established.  This supports the edge case of an entity wanting to use a new DID for every invitation. It is the responsibility of the controller to create the DID before passing it in.
  - If not provided, the 0.11.0 behaviour of an unqualified DID is used.
    - We expect this behaviour will change in a later release to be that `use_did_method="did:peer:4"` is the default, which is created and (re)used.
- The provided handshake protocol list must also include `didexchange/1.1`. Optionally, `didexchage/1.0` may also be provided, thus enabling backwards compatibility with agents that do not yet support `didexchage/1.0` and use of unqualified DIDs.

When receiving an OOB invitation or creating a DID Exchange request to a known Public DID:

- `POST /didexchange/create-request` and `POST /didexchange/{conn_id}/accept-invitation` accepts two parameters (in addition to others):
   - `use_did_method`: a DID Method (options: `did:peer:2` `did:peer:4`) indicating that a DID of that type should be created and used for the connection.
      - This is the recommend approach, and we further recommend using `did:peer:4`.
   - `use_did`: a complete DID, which will be used for the connection being established. This supports the edge case of an entity wanting to use the same DID for more than one connection. It is the responsibility of the controller to create the DID before passing it in.
   - If neither option is provided, the 0.11.0 behaviour of an unqualified DID is created if DID Exchange 1.0 is used, and a DID Peer 4 is used if DID Exchange 1.1 is used.
     - We expect this behaviour will change in a later release to be that a `did:peer:4` is created and DID Exchange 1.1 is always used.
- When `auto-accept` is used with DID Exchange, then an unqualified DID is created if DID Exchange 1.0 is being used, and a DID Peer 4 is used if DID Exchange 1.1 is used.

With these changes, an existing ACA-Py installation using unqualified DIDs can upgrade to use qualified DIDs:

- Reactively in 0.12.0 and later, by using like DIDs from the other agent.
- Proactively, by adding the `use_did` or `use_did_method` parameter on the `POST /out-of-band/create-invitation`, `POST /didexchange/create-request`. and `POST /didexchange/{conn_id}/accept_invitation` endpoints and specifying `did:peer:2` or `did_peer:4`.
  - The other agent must be able to process the selected DID Method.
- Proactively, by updating to use DID Exchange v1.1 and having the other side `auto-accept` the connection.

## DID Rotation

As part of the transition to qualified DIDs, existing connections may be updated to qualified DIDs using the DID Rotate protocol. This is not strictly required; since DIDComm v1 depends on recipient keys for correlating a received message back to a connection, the DID itself is mostly ignored. However, as we transition to DIDComm v2 or if it is desired to update the keys associated with a connection, DID Rotate may be used to update keys and service endpoints.

The steps to do so are:

- The rotating party creates a new DID using `POST /wallet/did/create` (or through the endpoints provided by a plugged in DID Method, if relevant).
  - For example, the rotating party will likely create a new `did:peer:4`.
- The rotating party initiates the rotation with `POST /did-rotate/{conn_id}/rotate` providing the created DID as the `to_did` in the body of the Admin API request.
- If the receiving party supports DID rotation, a `did_rotate` webhook will be emitted indicating success.
