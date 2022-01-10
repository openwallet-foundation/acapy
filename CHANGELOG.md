# 0.7.3

## January 10, 2022

This release includes some new AIP 2.0 features out (Revocation Notification and
Discover Features 2.0), a major new feature for those using Indy ledger (multi-ledger support),
a new "version upgrade" process that automates updating data in secure storage required after
a new release, and a fix for a critical bug in some mediator scenarios. The release also includes several new
pieces of documentation (upgrade processing, storage database information and logging) and some other documentation
updates that make the ACA-Py [Read The Docs site](https://aries-cloud-agent-python.readthedocs.io/en/latest/)
useful again. And of course, some recent bug fixes and cleanups are included.

There is a **BREAKING CHANGE** for those deploying ACA-Py with an external outbound queue
implementation (see [PR #1501](https://github.com/hyperledger/aries-cloudagent-python/pull/1501)).
As far as we know, there is only one organization that has such an implementation and they
were involved in the creation of this PR, so we are not making this release a minor or major update.
However, anyone else using an external queue should be aware of the impact of this PR that is
included in the release.

For those that have an existing deployment of ACA-Py with long-lasting connection records, an upgrade is needed to use
[RFC 434 Out of Band](https://github.com/hyperledger/aries-rfcs/tree/main/features/0434-outofband) and the "reuse connection" as the invitee. In PR #1453
(details below) a performance improvement was made when finding a connection for reuse. The new approach
(adding a tag to the connection to enable searching) applies only to connections made using this ACA-Py
release and later, and "as-is" connections made using earlier releases of ACA-Py will not be found as reuse
candidates. A new "Upgrade deployment" capability ([#1557](https://github.com/hyperledger/aries-cloudagent-python/pull/1557),
described below) must be executed to update your deployment to add tags for all existing connections.

The [Supported RFCs document](/SupportedRFCs.md) has been updated to reflect the addition of the
AIP 2.0 RFCs for which support was added.

The following is an annotated list of PRs in the release, including a link to each PR.

- **AIP 2.0 Features**
  - Discover Features Protocol: v1_0 refactoring and v2_0 implementation [[#1500](https://github.com/hyperledger/aries-cloudagent-python/pull/1500)](https://github.com/hyperledger/aries-cloudagent-python/pull/1500)
    - Updates the Discover Features 1.0 (AIP 1.0) implementation and implements the new 2.0 version. In doing so, adds generalized support for goal codes to ACA-Py.
    - fix DiscoveryExchangeRecord RECORD_TOPIC typo fix [#1566](https://github.com/hyperledger/aries-cloudagent-python/pull/1566)
  - Implement Revocation Notification v1.0 [#1464](https://github.com/hyperledger/aries-cloudagent-python/pull/1464)
  - Fix integration tests (revocation notifications) [#1528](https://github.com/hyperledger/aries-cloudagent-python/pull/1528)
  - Add Revocation notification support to alice/faber [#1527](https://github.com/hyperledger/aries-cloudagent-python/pull/1527)
- **Other New Features**
  - Multiple Indy Ledger support and State Proof verification [#1425](https://github.com/hyperledger/aries-cloudagent-python/pull/1425)
    - Remove required dependencies from multi-ledger code that was requiring the import of Aries Askar even when not being used[#1550](https://github.com/hyperledger/aries-cloudagent-python/pull/1550)
    - Fixed IndyDID resolver bug after Tag 0.7.3rc0 created [#1569](https://github.com/hyperledger/aries-cloudagent-python/pull/1569)
    - Typo vdr service name [#1563](https://github.com/hyperledger/aries-cloudagent-python/pull/1563)
    - Fixes and cleanup for multiple ledger support with Askar [#1583](https://github.com/hyperledger/aries-cloudagent-python/pull/1583)
  - Outbound Queue - more usability improvements [#1501](https://github.com/hyperledger/aries-cloudagent-python/pull/1501)
  - Display QR code when generating/displaying invites on startup [#1526](https://github.com/hyperledger/aries-cloudagent-python/pull/1526)
  - Enable WS Pings for WS Inbound Transport [#1530](https://github.com/hyperledger/aries-cloudagent-python/pull/1530)
    - Faster detection of lost Web Socket connections; implementation verified with an existing mediator.
  - Performance Improvement when using connection reuse in OOB and there are many DID connections. ConnRecord tags - their_public_did and invitation_msg_id [#1543](https://github.com/hyperledger/aries-cloudagent-python/pull/1543)
    - In previous releases, a "their_public_did" was not a tag, so to see if you can reuse a connection, all connections were retrieved from the database to see if a matching public DID can be found. Now, connections created after deploying this release will have a tag on the connection such that an indexed query can be used. See "Breaking Change" note above and "Update" feature below.
    - Follow up to [#1543](https://github.com/hyperledger/aries-cloudagent-python/pull/1543) - Adding invitation_msg_id and their_public_did back to record_value [#1553](https://github.com/hyperledger/aries-cloudagent-python/pull/1553)
  - A generic "Upgrade Deployment" capability was added to ACA-Py that operates like a database migration capability in relational databases. When executed (via a command line option), a current version of the deployment is detected and if any storage updates need be applied to be consistent with the new version, they are, and the stored "current version"is updated to the new version. An instance of this capability can be used to address the new feature #1543 documented above. [#1557](https://github.com/hyperledger/aries-cloudagent-python/pull/1557)
  - Adds a "credential_revoked" state to the Issue Credential protocol state object. When the protocol state object is retained past the completion of the protocol, it is updated when the credential is revoked. [#1545](https://github.com/hyperledger/aries-cloudagent-python/pull/1545)
  - Updated a missing dependency that recently caused an error when using the `--version` command line option [#1589](https://github.com/hyperledger/aries-cloudagent-python/pull/1589)
- **Critical Fixes**
  - Fix connection record response for mobile [#1469](https://github.com/hyperledger/aries-cloudagent-python/pull/1469)
- **Documentation Additions and Updates**
  - added documentation for wallet storage databases [#1523](https://github.com/hyperledger/aries-cloudagent-python/pull/1523)
  - added logging documentation [#1519](https://github.com/hyperledger/aries-cloudagent-python/pull/1519)
  - Fix warnings when generating ReadTheDocs [#1509](https://github.com/hyperledger/aries-cloudagent-python/pull/1509)
  - Remove Streetcred references [#1504](https://github.com/hyperledger/aries-cloudagent-python/pull/1504)
  - Add RTD configs to get generator working [#1496](https://github.com/hyperledger/aries-cloudagent-python/pull/1496)
  - The Alice/Faber demo was updated to allow connections based on Public DIDs to be established, including reusing a connection if there is an existing connection. [#1574](https://github.com/hyperledger/aries-cloudagent-python/pull/1574)
- **Other Fixes**
  - Connection Handling / Out of Band Invitations Fixes
    - OOB: Fixes issues with multiple public explicit invitation and unused 0160 connection [#1525](https://github.com/hyperledger/aries-cloudagent-python/pull/1525)
    - OOB added webhooks to notify the controller when a connection reuse message is used in response to an invitation [#1581](https://github.com/hyperledger/aries-cloudagent-python/pull/1581)
    - Delete unused ConnRecord generated - OOB invitation (use_exising_connection) [#1521](https://github.com/hyperledger/aries-cloudagent-python/pull/1521)
      - When an invitee responded with a "reuse" message, the connection record associated with the invitation was not being deleted. Now it is.
    - Await asyncio.sleeps to cleanup warnings in Python 3.8/3.9 [#1558](https://github.com/hyperledger/aries-cloudagent-python/pull/1558)
    - Add alias field to didexchange invitation UI [#1561](https://github.com/hyperledger/aries-cloudagent-python/pull/1561)
    - fix: use invitation key for connection query [#1570](https://github.com/hyperledger/aries-cloudagent-python/pull/1570)
    - Fix the inconsistency of invitation_msg_id between invitation and response [#1564](https://github.com/hyperledger/aries-cloudagent-python/pull/1564)
    - chore: update pydid to ^0.3.3 [#1562](https://github.com/hyperledger/aries-cloudagent-python/pull/1562)
  - DIF Presentation Exchange Cleanups
    - Fix DIF Presentation Request Input Validation [#1517](https://github.com/hyperledger/aries-cloudagent-python/pull/1517)
      - Some validation checking of a DIF presentation request to prevent uncaught errors later in the process.
    - DIF PresExch - ProblemReport and "is_holder" [#1493](https://github.com/hyperledger/aries-cloudagent-python/pull/1493)
      - Cleanups related to when "is_holder" is or is not required. Related to [Issue #1486](https://github.com/hyperledger/aries-cloudagent-python/issues/1486)
  - Indy SDK Related Fixes
    - Fix AttributeError when writing an Indy Cred Def record [#1516](https://github.com/hyperledger/aries-cloudagent-python/pull/1516)
    - Fix TypeError when calling credential_definitions_fix_cred_def_wallet… [#1515](https://github.com/hyperledger/aries-cloudagent-python/pull/1515)
    - Fix TypeError when writing a Schema record [#1494](https://github.com/hyperledger/aries-cloudagent-python/pull/1494)
    - Fix validation for range checks [#1538](https://github.com/hyperledger/aries-cloudagent-python/pull/1538)
      - Back out some of the validation checking for proof requests with predicates as they were preventing valid proof requests from being processed.
  - Aries Askar Related Fixes:
    - Fix bug when getting credentials on askar-profile [#1510](https://github.com/hyperledger/aries-cloudagent-python/pull/1510)
    - Fix error when removing a wallet on askar-profile [#1518](https://github.com/hyperledger/aries-cloudagent-python/pull/1518)
    - Fix error when connection request is received (askar, public invitation) [#1508](https://github.com/hyperledger/aries-cloudagent-python/pull/1508)
    - Fix error when an error occurs while issuing a revocable credential [#1591](https://github.com/hyperledger/aries-cloudagent-python/pull/1591)
  - Docker fixes:
    - Update docker scripts to use new & improved docker IP detection [#1565](https://github.com/hyperledger/aries-cloudagent-python/pull/1565)
  - Release Adminstration:
    - Changelog and RTD updates for the pending 0.7.3 release [#1553](https://github.com/hyperledger/aries-cloudagent-python/pull/1553)
  
# 0.7.2

## November 15, 2021

A mostly maintenance release with some key updates and cleanups based on community deployments and discovery.
With usage in the field increasing, we're cleaning up edge cases and issues related to volume deployments.

The most significant new feature for users of Indy ledgers is a simplified approach for transaction authors getting their transactions
signed by an endorser. Transaction author controllers now do almost nothing other than configuring their instance to use an Endorser,
and ACA-Py takes care of the rest. Documentation of that feature is [here](Endorser.md).

- Improve cloud native deployments/scaling
  - unprotect liveness and readiness endpoints [#1416](https://github.com/hyperledger/aries-cloudagent-python/pull/1416)
  - Open askar sessions only on demand - Connections [#1424](https://github.com/hyperledger/aries-cloudagent-python/pull/1424)
  - Fixed potential deadlocks by opening sessions only on demand (Wallet endpoints) [#1472](https://github.com/hyperledger/aries-cloudagent-python/pull/1472)
  - Fixed potential deadlocks by opening sessions only on demand [#1439](https://github.com/hyperledger/aries-cloudagent-python/pull/1439)
  - Make mediation invitation parameter idempotent [#1413](https://github.com/hyperledger/aries-cloudagent-python/pull/1413)
- Indy Transaction Endorser Support Added
  - Endorser protocol configuration, automation and demo integration [#1422](https://github.com/hyperledger/aries-cloudagent-python/pull/1422)
  - Auto connect from author to endorser on startup [#1461](https://github.com/hyperledger/aries-cloudagent-python/pull/1461)
  - Startup and shutdown events (prep for endorser updates) [#1459](https://github.com/hyperledger/aries-cloudagent-python/pull/1459)
  - Endorser protocol askar fixes [#1450](https://github.com/hyperledger/aries-cloudagent-python/pull/1450)
  - Endorser protocol updates - refactor to use event bus [#1448](https://github.com/hyperledger/aries-cloudagent-python/pull/1448)
- Indy verifiable credential/presentation fixes and updates
  - Update credential and proof mappings to allow negative encoded values [#1475](https://github.com/hyperledger/aries-cloudagent-python/pull/1475)
  - Add credential validation to offer issuance step [#1446](https://github.com/hyperledger/aries-cloudagent-python/pull/1446)
  - Fix error removing proof req entries by timestamp [#1465](https://github.com/hyperledger/aries-cloudagent-python/pull/1465)
  - Fix issue with cred limit on presentation endpoint [#1437](https://github.com/hyperledger/aries-cloudagent-python/pull/1437)
  - Add support for custom offers from the proposal [#1426](https://github.com/hyperledger/aries-cloudagent-python/pull/1426)
  - Make requested attributes and predicates required on indy proof request [#1411](https://github.com/hyperledger/aries-cloudagent-python/pull/1411)
  - Remove connection check on proof verify [#1383](https://github.com/hyperledger/aries-cloudagent-python/pull/1383)
- General cleanups and improvements to existing features
  - Fixes failing integration test -- JSON-LD context URL not loading because of external issue [#1491](https://github.com/hyperledger/aries-cloudagent-python/pull/1491)
  - Update base record time-stamp to standard ISO format [#1453](https://github.com/hyperledger/aries-cloudagent-python/pull/1453)
  - Encode DIDComm messages before sent to the queue [#1408](https://github.com/hyperledger/aries-cloudagent-python/pull/1408)
  - Add Event bus Metadata [#1429](https://github.com/hyperledger/aries-cloudagent-python/pull/1429)
  - Allow base wallet to connect to a mediator after startup [#1463](https://github.com/hyperledger/aries-cloudagent-python/pull/1463)
  - Log warning when unsupported problem report code is received [#1409](https://github.com/hyperledger/aries-cloudagent-python/pull/1409)
  - feature/inbound-transport-profile [#1407](https://github.com/hyperledger/aries-cloudagent-python/pull/1407)
  - Import cleanups [#1393](https://github.com/hyperledger/aries-cloudagent-python/pull/1393)
  - Add no-op handler for generic ack message (RFC 0015) [#1390](https://github.com/hyperledger/aries-cloudagent-python/pull/1390)
  - Align OutOfBandManager.receive_invitation with other connection managers [#1382](https://github.com/hyperledger/aries-cloudagent-python/pull/1382)
- Bug fixes
  - fix: fixes error in use of a default mediator in connections/out of band -- mediation ID was being saved as None instead of the retrieved default mediator value [#1490](https://github.com/hyperledger/aries-cloudagent-python/pull/1490)
  - fix: help text for open-mediation flag [#1445](https://github.com/hyperledger/aries-cloudagent-python/pull/1445)
  - fix: incorrect return type [#1438](https://github.com/hyperledger/aries-cloudagent-python/pull/1438)
  - Add missing param to ws protocol [#1442](https://github.com/hyperledger/aries-cloudagent-python/pull/1442)
  - fix: create static doc use empty endpoint if None [#1483](https://github.com/hyperledger/aries-cloudagent-python/pull/1483)
  - fix: use named tuple instead of dataclass in mediation invite store [#1476](https://github.com/hyperledger/aries-cloudagent-python/pull/1476)
  - When fetching the admin config, don't overwrite webhook settings [#1420](https://github.com/hyperledger/aries-cloudagent-python/pull/1420)
  - fix: return type of inject [#1392](https://github.com/hyperledger/aries-cloudagent-python/pull/1392)
  - fix: typo in connection static result schema [#1389](https://github.com/hyperledger/aries-cloudagent-python/pull/1389)
  - fix: don't require push on outbound queue implementations [#1387](https://github.com/hyperledger/aries-cloudagent-python/pull/1387)
- Updates/Fixes to the Alice/Faber demo and integration tests
  - Clarify instructions in the Acme Controller Demo [#1484](https://github.com/hyperledger/aries-cloudagent-python/pull/1484)
  - Fix aip 20 behaviour and other cleanup [#1406](https://github.com/hyperledger/aries-cloudagent-python/pull/1406)
  - Fix issue with startup sequence for faber agent [#1415](https://github.com/hyperledger/aries-cloudagent-python/pull/1415)
  - Connectionless proof demo [#1395](https://github.com/hyperledger/aries-cloudagent-python/pull/1395)
  - Typos in the demo's README.md [#1405](https://github.com/hyperledger/aries-cloudagent-python/pull/1405)
  - Run integration tests using external ledger and tails server [#1400](https://github.com/hyperledger/aries-cloudagent-python/pull/1400)
- Chores
  - Update CONTRIBUTING.md [#1428](https://github.com/hyperledger/aries-cloudagent-python/pull/1428)
  - Update to ReadMe and Supported RFCs for 0.7.2 [#1489](https://github.com/hyperledger/aries-cloudagent-python/pull/1489)
  - Updating the RTDs code for Release 0.7.2 - Try 2 [#1488](https://github.com/hyperledger/aries-cloudagent-python/pull/1488)

# 0.7.1

## August 31, 2021

A relatively minor maintenance release to address issues found since the 0.7.0 Release.
Includes some cleanups of JSON-LD Verifiable Credentials and Verifiable Presentations

- W3C  Verifiable Credential cleanups
  - Timezone inclusion [ISO 8601] for W3C VC and Proofs ([#1373](https://github.com/hyperledger/aries-cloudagent-python/pull/1373))
  - W3C VC handling where attachment is JSON and not Base64 encoded ([#1352](https://github.com/hyperledger/aries-cloudagent-python/pull/1352))
- Refactor outbound queue interface ([#1348](https://github.com/hyperledger/aries-cloudagent-python/pull/1348))
- Command line parameter handling for arbitrary plugins ([#1347](https://github.com/hyperledger/aries-cloudagent-python/pull/1347))
- Add an optional parameter '--ledger-socks-proxy' ([#1342](https://github.com/hyperledger/aries-cloudagent-python/pull/1342))
- OOB Protocol - CredentialOffer Support ([#1316](https://github.com/hyperledger/aries-cloudagent-python/pull/1316)), ([#1216](https://github.com/hyperledger/aries-cloudagent-python/pull/1216))
- Updated IndyCredPrecisSchema - pres_referents renamed to presentation_referents ([#1334](https://github.com/hyperledger/aries-cloudagent-python/pull/1334))
- Handle unpadded protected header in PackWireFormat::get_recipient_keys ([#1324](https://github.com/hyperledger/aries-cloudagent-python/pull/1324))
- Initial cut of OpenAPI Code Generation guidelines ([#1339](https://github.com/hyperledger/aries-cloudagent-python/pull/1339))
- Correct revocation API in credential revocation documentation ([#612](https://github.com/hyperledger/aries-cloudagent-python/pull/612))
- Documentation updates for Read-The-Docs ([#1359](https://github.com/hyperledger/aries-cloudagent-python/pull/1359),
[#1366](https://github.com/hyperledger/aries-cloudagent-python/pull/1366), [#1371](https://github.com/hyperledger/aries-cloudagent-python/pull/1371))
- Add `inject_or` method to dynamic injection framework to resolve typing ambiguity ([#1376](https://github.com/hyperledger/aries-cloudagent-python/pull/1376))
- Other fixes:
  - Indy Proof processing fix, error not raised in predicate timestamp check ([#1364](https://github.com/hyperledger/aries-cloudagent-python/pull/1364))
  - Problem Report handler for connection specific problems ([#1356](https://github.com/hyperledger/aries-cloudagent-python/pull/1356))
  - fix: error on deserializing conn record with protocol ([#1325](https://github.com/hyperledger/aries-cloudagent-python/pull/1325))
  - fix: failure to verify jsonld on non-conformant doc but vaild vmethod ([#1301](https://github.com/hyperledger/aries-cloudagent-python/pull/1301))
  - fix: allow underscore in endpoints ([#1378](https://github.com/hyperledger/aries-cloudagent-python/pull/1378))
  

# 0.7.0

## July 14, 2021

Another significant release, this version adds support for multiple new protocols, credential formats, and extension methods.

- Support for [W3C Standard Verifiable Credentials](https://www.w3.org/TR/vc-data-model/) based on JSON-LD using LD-Signatures and [BBS+ Signatures](https://w3c-ccg.github.io/ldp-bbs2020/), contributed by [Animo Solutions](https://animo.id/) - [#1061](https://github.com/hyperledger/aries-cloudagent-python/pull/1061)
- [Present Proof V2](https://github.com/hyperledger/aries-rfcs/tree/master/features/0454-present-proof-v2) including support for [DIF Presentation Exchange](https://identity.foundation/presentation-exchange/) - [#1125](https://github.com/hyperledger/aries-cloudagent-python/pull/1125)
- Pluggable DID Resolver (with a did:web resolver) with fallback to an external DID universal resolver, contributed by [Indicio](https://indicio.tech/) - [#1070](https://github.com/hyperledger/aries-cloudagent-python/pull/1070)
- Updates and extensions to ledger transaction endorsement via the [Sign Attachment Protocol](https://github.com/hyperledger/aries-rfcs/pull/586), contributed by [AyanWorks](https://www.ayanworks.com/) - [#1134](https://github.com/hyperledger/aries-cloudagent-python/pull/1134), [#1200](https://github.com/hyperledger/aries-cloudagent-python/pull/1200)
- Upgrades to Demos to add support for Credential Exchange 2.0 and W3C Verifiable Credentials [#1235](https://github.com/hyperledger/aries-cloudagent-python/pull/1235)
- Alpha support for the Indy/Aries Shared Components ([indy-vdr](https://github.com/hyperledger/indy-vdr), [indy-credx](https://github.com/hyperledger/indy-shared-rs) and [aries-askar](https://github.com/hyperledger/aries-askar)), which enable running ACA-Py without using Indy-SDK, while still supporting the use of Indy as a ledger, and Indy AnonCreds verifiable credentials [#1267](https://github.com/hyperledger/aries-cloudagent-python/pull/1267)
- A new event bus for distributing internally generated ACA-Py events to controllers and other listeners, contributed by [Indicio](https://indicio.tech/) - [#1063](https://github.com/hyperledger/aries-cloudagent-python/pull/1063)
- Enable operation without Indy ledger support if not needed
- Performance fix for deployments with large numbers of DIDs/connections [#1249](https://github.com/hyperledger/aries-cloudagent-python/pull/1249)
- Simplify the creation/handling of plugin protocols [#1086](https://github.com/hyperledger/aries-cloudagent-python/pull/1086), [#1133](https://github.com/hyperledger/aries-cloudagent-python/pull/1133), [#1226](https://github.com/hyperledger/aries-cloudagent-python/pull/1226)
- DID Exchange implicit invitation handling [#1174](https://github.com/hyperledger/aries-cloudagent-python/pull/1174)
- Add support for Indy 1.16 predicates (restrictions on predicates based on attribute name and value) [#1213](https://github.com/hyperledger/aries-cloudagent-python/pull/1213)
- BDD Tests run via GitHub Actions [#1046](https://github.com/hyperledger/aries-cloudagent-python/pull/1046)

# 0.6.0

## February 25, 2021

This is a significant release of ACA-Py with several new features, as well as changes to the internal architecture in order to set the groundwork for using the new shared component libraries: [indy-vdr](https://github.com/hyperledger/indy-vdr), [indy-credx](https://github.com/hyperledger/indy-shared-rs), and [aries-askar](https://github.com/hyperledger/aries-askar).

### Mediator support

While ACA-Py had previous support for a basic routing protocol, this was never fully developed or used in practice. Starting with this release, inbound and outbound connections can be established through a mediator agent using the Aries (Mediator Coordination Protocol)[https://github.com/hyperledger/aries-rfcs/tree/master/features/0211-route-coordination]. This work was initially contributed by Adam Burdett and Daniel Bluhm of [Indicio](https://indicio.tech/) on behalf of [SICPA](https://sicpa.com/). [Read more about mediation support](./Mediation.md).

### Multi-Tenancy support

Started by [BMW](https://bmw.com/) and completed by [Animo Solutions](https://animo.id/) and [Anon Solutions](https://anon-solutions.ca/) on behalf of [SICPA](https://sicpa.com/), this feature allows for a single ACA-Py instance to host multiple wallet instances. This can greatly reduce the resources required when many identities are being handled. [Read more about multi-tenancy support](./Multitenancy.md).

### New connection protocol(s)

In addition to the Aries 0160 Connections RFC, ACA-Py now supports the Aries [DID Exchange Protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0023-did-exchange) for connection establishment and reuse, as well as the Aries [Out-of-Band Protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0434-outofband) for representing connection invitations and other pre-connection requests.

### Issue-Credential v2

This release includes an initial implementation of the Aries [Issue Credential v2](https://github.com/hyperledger/aries-rfcs/tree/master/features/0453-issue-credential-v2) protocol.

### Notable changes for administrators

- There are several new endpoints available for controllers as well as new startup parameters related to the multi-tenancy and mediator features, see the feature description pages above in order to make use of these features. Additional admin endpoints are introduced for the DID Exchange, Issue Credential v2, and Out-of-Band protocols.

- When running `aca-py start`, a new wallet will no longer be created unless the `--auto-provision` argument is provided. It is recommended to always use `aca-py provision` to initialize the wallet rather than relying on automatic behaviour, as this removes the need for repeatedly providing the wallet seed value (if any). This is a breaking change from previous versions.

- When running `aca-py provision`, an existing wallet will not be removed and re-created unless the `--recreate-wallet` argument is provided. This is a breaking change from previous versions.

- The logic around revocation intervals has been tightened up in accordance with [Present Proof Best Practices](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0441-present-proof-best-practices).

### Notable changes for plugin writers

The following are breaking changes to the internal APIs which may impact Python code extensions.

- Manager classes generally accept a `Profile` instance, where previously they accepted a `RequestContext`.

- Admin request handlers now receive an `AdminRequestContext` as `app["context"]`. The current profile is available as `app["context"].profile`. The admin server now generates a unique context instance per request in order to facilitate multi-tenancy, rather than reusing the same instance for each handler.

- In order to inject the `BaseStorage` or `BaseWallet` interfaces, a `ProfileSession` must be used. Other interfaces can be injected at the `Profile` or `ProfileSession` level. This is obtained by awaiting `profile.session()` for the current `Profile` instance, or (preferably) using it as an async context manager:

```python=
async with profile.session() as session:
   storage = session.inject(BaseStorage)
```

- The `inject` method of a context is no longer `async`.

# 0.5.6

## October 19, 2020

- Fix an attempt to update the agent endpoint when configured with a read-only ledger [#758](https://github.com/hyperledger/aries-cloudagent-python/pull/758)

# 0.5.5

## October 9, 2020

- Support interactions using the new `https://didcomm.org` message type prefix (currently opt-in via the `--emit-new-didcomm-prefix` flag) [#705](https://github.com/hyperledger/aries-cloudagent-python/pull/705), [#713](https://github.com/hyperledger/aries-cloudagent-python/pull/713)
- Updates to application startup arguments, adding support for YAML configuration [#739](https://github.com/hyperledger/aries-cloudagent-python/pull/739), [#746](https://github.com/hyperledger/aries-cloudagent-python/pull/746), [#748](https://github.com/hyperledger/aries-cloudagent-python/pull/748)
- Add a new endpoint to check the revocation status of a stored credential [#735](https://github.com/hyperledger/aries-cloudagent-python/pull/735)
- Clean up API documentation and OpenAPI definition, minor API adjustments [#712](https://github.com/hyperledger/aries-cloudagent-python/pull/712), [#726](https://github.com/hyperledger/aries-cloudagent-python/pull/726), [#732](https://github.com/hyperledger/aries-cloudagent-python/pull/732), [#734](https://github.com/hyperledger/aries-cloudagent-python/pull/734), [#738](https://github.com/hyperledger/aries-cloudagent-python/pull/738), [#741](https://github.com/hyperledger/aries-cloudagent-python/pull/741), [#747](https://github.com/hyperledger/aries-cloudagent-python/pull/747)
- Add configurable support for unencrypted record tags [#723](https://github.com/hyperledger/aries-cloudagent-python/pull/723)
- Retain more limited records on issued credentials [#718](https://github.com/hyperledger/aries-cloudagent-python/pull/718)
- Fix handling of custom endpoint in connections `accept-request` API method [#715](https://github.com/hyperledger/aries-cloudagent-python/pull/715),
  [#716](https://github.com/hyperledger/aries-cloudagent-python/pull/716)
- Add restrictions around revocation registry sizes [#727](https://github.com/hyperledger/aries-cloudagent-python/pull/727)
- Allow the state for revocation registry records to be set manually [#708](https://github.com/hyperledger/aries-cloudagent-python/pull/708)
- Handle multiple matching credentials when satisfying a presentation request using `names` [#706](https://github.com/hyperledger/aries-cloudagent-python/pull/706)
- Additional handling for a missing local tails file, tails file rollover process [#702](https://github.com/hyperledger/aries-cloudagent-python/pull/702), [#717](https://github.com/hyperledger/aries-cloudagent-python/pull/717)
- Handle unknown credential ID in `create-proof` API method [#700](https://github.com/hyperledger/aries-cloudagent-python/pull/700)
- Improvements to revocation interval handling in presentation requests [#699](https://github.com/hyperledger/aries-cloudagent-python/pull/699), [#703](https://github.com/hyperledger/aries-cloudagent-python/pull/703)
- Clean up warnings on API redirects [#692](https://github.com/hyperledger/aries-cloudagent-python/pull/692)
- Extensions to DID publicity status [#691](https://github.com/hyperledger/aries-cloudagent-python/pull/691)
- Support Unicode text in JSON-LD credential handling [#687](https://github.com/hyperledger/aries-cloudagent-python/pull/687)

# 0.5.4

## August 24, 2020

- Improvements to schema, cred def registration procedure [#682](https://github.com/hyperledger/aries-cloudagent-python/pull/682), [#683](https://github.com/hyperledger/aries-cloudagent-python/pull/683)
- Updates to align admin API output with documented interface [#674](https://github.com/hyperledger/aries-cloudagent-python/pull/674), [#681](https://github.com/hyperledger/aries-cloudagent-python/pull/681)
- Fix provisioning issue when ledger is configured as read-only [#673](https://github.com/hyperledger/aries-cloudagent-python/pull/673)
- Add `get-nym-role` action [#671](https://github.com/hyperledger/aries-cloudagent-python/pull/671)
- Basic support for w3c profile endpoint [#667](https://github.com/hyperledger/aries-cloudagent-python/pull/667), [#669](https://github.com/hyperledger/aries-cloudagent-python/pull/669)
- Improve handling of non-revocation interval [#648](https://github.com/hyperledger/aries-cloudagent-python/pull/648), [#680](https://github.com/hyperledger/aries-cloudagent-python/pull/680)
- Update revocation demo after changes to tails file handling [#644](https://github.com/hyperledger/aries-cloudagent-python/pull/644)
- Improve handling of fatal ledger errors [#643](https://github.com/hyperledger/aries-cloudagent-python/pull/643), [#659](https://github.com/hyperledger/aries-cloudagent-python/pull/659)
- Improve `did:key:` handling in out-of-band protocol support [#639](https://github.com/hyperledger/aries-cloudagent-python/pull/639)
- Fix crash when no public DID is configured [#637](https://github.com/hyperledger/aries-cloudagent-python/pull/637)
- Fix high CPU usage when only messages pending retry are in the outbound queue [#636](https://github.com/hyperledger/aries-cloudagent-python/pull/636)
- Additional unit tests for config, messaging, revocation, startup, transports [#633](https://github.com/hyperledger/aries-cloudagent-python/pull/633), [#641](https://github.com/hyperledger/aries-cloudagent-python/pull/641), [#658](https://github.com/hyperledger/aries-cloudagent-python/pull/658), [#661](https://github.com/hyperledger/aries-cloudagent-python/pull/661), [#666](https://github.com/hyperledger/aries-cloudagent-python/pull/666)
- Allow forwarded messages to use existing connections and the outbound queue [#631](https://github.com/hyperledger/aries-cloudagent-python/pull/631)

# 0.5.3

## July 23, 2020

- Store endpoint on provisioned DID records [#610](https://github.com/hyperledger/aries-cloudagent-python/pull/610)
- More reliable delivery of outbound messages and webhooks [#615](https://github.com/hyperledger/aries-cloudagent-python/pull/615)
- Improvements for OpenShift pod handling [#614](https://github.com/hyperledger/aries-cloudagent-python/pull/614)
- Remove support for 'on-demand' revocation registries [#605](https://github.com/hyperledger/aries-cloudagent-python/pull/605)
- Sort tags in generated swagger JSON for better consistency [#602](https://github.com/hyperledger/aries-cloudagent-python/pull/602)
- Improve support for multi-credential proofs [#601](https://github.com/hyperledger/aries-cloudagent-python/pull/601)
- Adjust default settings for tracing and add documentation [#598](https://github.com/hyperledger/aries-cloudagent-python/pull/598), [#597](https://github.com/hyperledger/aries-cloudagent-python/pull/597)
- Fix reliance on local copy of revocation tails file [#590](https://github.com/hyperledger/aries-cloudagent-python/pull/590)
- Improved handling of problem reports [#595](https://github.com/hyperledger/aries-cloudagent-python/pull/595)
- Remove credential preview parameter from credential issue endpoint [#596](https://github.com/hyperledger/aries-cloudagent-python/pull/596)
- Looser format restrictions on dates [#586](https://github.com/hyperledger/aries-cloudagent-python/pull/586)
- Support `names` and attribute-value specifications in present-proof protocol [#587](https://github.com/hyperledger/aries-cloudagent-python/pull/587)
- Misc documentation updates and unit test coverage

# 0.5.2

## June 26, 2020

- Initial out-of-band protocol support [#576](https://github.com/hyperledger/aries-cloudagent-python/pull/576)
- Support provisioning a new local-only DID in the wallet, updating a DID endpoint [#559](https://github.com/hyperledger/aries-cloudagent-python/pull/559), [#573](https://github.com/hyperledger/aries-cloudagent-python/pull/573)
- Support pagination for holder search operation [#558](https://github.com/hyperledger/aries-cloudagent-python/pull/558)
- Add raw JSON credential signing and verification admin endpoints [#540](https://github.com/hyperledger/aries-cloudagent-python/pull/540)
- Catch fatal errors in admin and protocol request handlers [#527](https://github.com/hyperledger/aries-cloudagent-python/pull/527), [#533](https://github.com/hyperledger/aries-cloudagent-python/pull/533), [#534](https://github.com/hyperledger/aries-cloudagent-python/pull/534), [#539](https://github.com/hyperledger/aries-cloudagent-python/pull/539), [#543](https://github.com/hyperledger/aries-cloudagent-python/pull/543), [#554](https://github.com/hyperledger/aries-cloudagent-python/pull/554), [#555](https://github.com/hyperledger/aries-cloudagent-python/pull/555)
- Add wallet and DID key rotation operations [#525](https://github.com/hyperledger/aries-cloudagent-python/pull/525)
- Admin API documentation and usability improvements [#504](https://github.com/hyperledger/aries-cloudagent-python/pull/504), [#516](https://github.com/hyperledger/aries-cloudagent-python/pull/516), [#570](https://github.com/hyperledger/aries-cloudagent-python/pull/570)
- Adjust the maximum number of attempts for outbound messages [#501](https://github.com/hyperledger/aries-cloudagent-python/pull/501)
- Add demo support for tails server [#499](https://github.com/hyperledger/aries-cloudagent-python/pull/499)
- Various credential and presentation protocol fixes and improvements [#491](https://github.com/hyperledger/aries-cloudagent-python/pull/491), [#494](https://github.com/hyperledger/aries-cloudagent-python/pull/494), [#498](https://github.com/hyperledger/aries-cloudagent-python/pull/498), [#526](https://github.com/hyperledger/aries-cloudagent-python/pull/526), [#561](https://github.com/hyperledger/aries-cloudagent-python/pull/561), [#563](https://github.com/hyperledger/aries-cloudagent-python/pull/563), [#564](https://github.com/hyperledger/aries-cloudagent-python/pull/564), [#577](https://github.com/hyperledger/aries-cloudagent-python/pull/577), [#579](https://github.com/hyperledger/aries-cloudagent-python/pull/579)
- Fixes for multiple agent endpoints [#495](https://github.com/hyperledger/aries-cloudagent-python/pull/495), [#497](https://github.com/hyperledger/aries-cloudagent-python/pull/497)
- Additional test coverage [#482](https://github.com/hyperledger/aries-cloudagent-python/pull/482), [#485](https://github.com/hyperledger/aries-cloudagent-python/pull/485), [#486](https://github.com/hyperledger/aries-cloudagent-python/pull/486), [#487](https://github.com/hyperledger/aries-cloudagent-python/pull/487), [#490](https://github.com/hyperledger/aries-cloudagent-python/pull/490), [#493](https://github.com/hyperledger/aries-cloudagent-python/pull/493), [#509](https://github.com/hyperledger/aries-cloudagent-python/pull/509), [#553](https://github.com/hyperledger/aries-cloudagent-python/pull/553)
- Update marshmallow dependency [#479](https://github.com/hyperledger/aries-cloudagent-python/pull/479)

# 0.5.1

## April 23, 2020

- Restore previous response format for the `/credential/{id}` admin route [#474](https://github.com/hyperledger/aries-cloudagent-python/pull/474)

# 0.5.0

## April 21, 2020

- Add support for credential revocation and revocation registry handling, with thanks to Medici Ventures [#306](https://github.com/hyperledger/aries-cloudagent-python/pull/306), [#417](https://github.com/hyperledger/aries-cloudagent-python/pull/417), [#425](https://github.com/hyperledger/aries-cloudagent-python/pull/425), [#429](https://github.com/hyperledger/aries-cloudagent-python/pull/429), [#432](https://github.com/hyperledger/aries-cloudagent-python/pull/432), [#435](https://github.com/hyperledger/aries-cloudagent-python/pull/435), [#441](https://github.com/hyperledger/aries-cloudagent-python/pull/441), [#455](https://github.com/hyperledger/aries-cloudagent-python/pull/455)
- **Breaking change** Remove previous credential and presentation protocols (0.1 versions) [#416](https://github.com/hyperledger/aries-cloudagent-python/pull/416)
- Add support for major/minor protocol version routing [#443](https://github.com/hyperledger/aries-cloudagent-python/pull/443)
- Event tracing and trace reports for message exchanges [#440](https://github.com/hyperledger/aries-cloudagent-python/pull/451)
- Support additional Indy restriction operators (`>`, `<`, `<=` in addition to `>=`) [#457](https://github.com/hyperledger/aries-cloudagent-python/pull/457)
- Support signed attachments according to the updated Aries RFC 0017 [#456](https://github.com/hyperledger/aries-cloudagent-python/pull/456)
- Increased test coverage [#442](https://github.com/hyperledger/aries-cloudagent-python/pull/442), [#453](https://github.com/hyperledger/aries-cloudagent-python/pull/453)
- Updates to demo agents and documentation [#402](https://github.com/hyperledger/aries-cloudagent-python/pull/402), [#403](https://github.com/hyperledger/aries-cloudagent-python/pull/403), [#411](https://github.com/hyperledger/aries-cloudagent-python/pull/411), [#415](https://github.com/hyperledger/aries-cloudagent-python/pull/415), [#422](https://github.com/hyperledger/aries-cloudagent-python/pull/422), [#423](https://github.com/hyperledger/aries-cloudagent-python/pull/423), [#449](https://github.com/hyperledger/aries-cloudagent-python/pull/449), [#450](https://github.com/hyperledger/aries-cloudagent-python/pull/450), [#452](https://github.com/hyperledger/aries-cloudagent-python/pull/452)
- Use Indy generate_nonce method to create proof request nonces [#431](https://github.com/hyperledger/aries-cloudagent-python/pull/431)
- Make request context available in the outbound transport handler [#408](https://github.com/hyperledger/aries-cloudagent-python/pull/408)
- Contain indy-anoncreds usage in IndyIssuer, IndyHolder, IndyProver classes [#406](https://github.com/hyperledger/aries-cloudagent-python/pull/406), [#463](https://github.com/hyperledger/aries-cloudagent-python/pull/463)
- Fix issue with validation of proof with predicates and revocation support [#400](https://github.com/hyperledger/aries-cloudagent-python/pull/400)

# 0.4.5

## March 3, 2020

- Added NOTICES file with license information for dependencies [#398](https://github.com/hyperledger/aries-cloudagent-python/pull/398)
- Updated documentation for administration API demo [#397](https://github.com/hyperledger/aries-cloudagent-python/pull/397)
- Accept self-attested attributes in presentation verification, only when no restrictions are present on the requested attribute [#394](https://github.com/hyperledger/aries-cloudagent-python/pull/394), [#396](https://github.com/hyperledger/aries-cloudagent-python/pull/396)

# 0.4.4

## February 28, 2020

- Update docker image used in demo and test containers [#391](https://github.com/hyperledger/aries-cloudagent-python/pull/391)
- Fix pre-verify check on received presentations [#390](https://github.com/hyperledger/aries-cloudagent-python/pull/390)
- Do not canonicalize attribute names in credential previews [#389](https://github.com/hyperledger/aries-cloudagent-python/pull/389)

# 0.4.3

## February 26, 2020

- Fix the application of transaction author agreement acceptance to signed ledger requests [#385](https://github.com/hyperledger/aries-cloudagent-python/pull/385)
- Add a command line argument to preserve connection exchange records [#355](https://github.com/hyperledger/aries-cloudagent-python/pull/355)
- Allow custom credential IDs to be specified by the controller in the issue-credential protocol [#384](https://github.com/hyperledger/aries-cloudagent-python/pull/384)
- Handle send timeouts in the admin server websocket implementation [#377](https://github.com/hyperledger/aries-cloudagent-python/pull/377)
- [Aries RFC 0348](https://github.com/hyperledger/aries-rfcs/tree/master/features/0348-transition-msg-type-to-https): Support the 'didcomm.org' message type prefix for incoming messages [#379](https://github.com/hyperledger/aries-cloudagent-python/pull/379)
- Add support for additional postgres wallet schemes such as "MultiWalletDatabase" [#378](https://github.com/hyperledger/aries-cloudagent-python/pull/378)
- Updates to the demo agents and documentation to support demos using the OpenAPI interface [#371](https://github.com/hyperledger/aries-cloudagent-python/pull/371), [#375](https://github.com/hyperledger/aries-cloudagent-python/pull/375), [#376](https://github.com/hyperledger/aries-cloudagent-python/pull/376), [#382](https://github.com/hyperledger/aries-cloudagent-python/pull/382), [#383](https://github.com/hyperledger/aries-cloudagent-python/pull/376), [#382](https://github.com/hyperledger/aries-cloudagent-python/pull/383)
- Add a new flag for preventing writes to the ledger [#364](https://github.com/hyperledger/aries-cloudagent-python/pull/364)

# 0.4.2

## February 8, 2020

- Adjust logging on HTTP request retries [#363](https://github.com/hyperledger/aries-cloudagent-python/pull/363)
- Tweaks to `run_docker`/`run_demo` scripts for Windows [#357](https://github.com/hyperledger/aries-cloudagent-python/pull/357)
- Avoid throwing exceptions on invalid or incomplete received presentations [#359](https://github.com/hyperledger/aries-cloudagent-python/pull/359)
- Restore the `present-proof/create-request` admin endpoint for creating connectionless presentation requests [#356](https://github.com/hyperledger/aries-cloudagent-python/pull/356)
- Activate the `connections/create-static` admin endpoint for creating static connections [#354](https://github.com/hyperledger/aries-cloudagent-python/pull/354)

# 0.4.1

## January 31, 2020

- Update Forward messages and handlers to align with RFC 0094 for compatibility with libvcx and Streetcred [#240](https://github.com/hyperledger/aries-cloudagent-python/pull/240), [#349](https://github.com/hyperledger/aries-cloudagent-python/pull/349)
- Verify encoded attributes match raw attributes on proof presentation [#344](https://github.com/hyperledger/aries-cloudagent-python/pull/344)
- Improve checks for existing credential definitions in the wallet and on ledger when publishing [#333](https://github.com/hyperledger/aries-cloudagent-python/pull/333), [#346](https://github.com/hyperledger/aries-cloudagent-python/pull/346)
- Accommodate referents in presentation proposal preview attribute specifications [#333](https://github.com/hyperledger/aries-cloudagent-python/pull/333)
- Make credential proposal optional in issue-credential protocol [#336](https://github.com/hyperledger/aries-cloudagent-python/pull/336)
- Handle proofs with repeated credential definition IDs [#330](https://github.com/hyperledger/aries-cloudagent-python/pull/330)
- Allow side-loading of alternative inbound transports [#322](https://github.com/hyperledger/aries-cloudagent-python/pull/322)
- Various fixes to documentation and message schemas, and improved unit test coverage

# 0.4.0

## December 10, 2019

- Improved unit test coverage (actionmenu, basicmessage, connections, introduction, issue-credential, present-proof, routing protocols)
- Various documentation and bug fixes
- Add admin routes for fetching and accepting the ledger transaction author agreement [#144](https://github.com/hyperledger/aries-cloudagent-python/pull/144)
- Add support for receiving connection-less proof presentations [#296](https://github.com/hyperledger/aries-cloudagent-python/pull/296)
- Set attachment id explicitely in unbound proof request [#289](https://github.com/hyperledger/aries-cloudagent-python/pull/289)
- Add create-proposal admin endpoint to the present-proof protocol [#288](https://github.com/hyperledger/aries-cloudagent-python/pull/288)
- Remove old anon/authcrypt support [#282](https://github.com/hyperledger/aries-cloudagent-python/pull/282)
- Allow additional endpoints to be specified [#276](https://github.com/hyperledger/aries-cloudagent-python/pull/276)
- Allow timestamp without trailing 'Z' [#275](https://github.com/hyperledger/aries-cloudagent-python/pull/275), [#277](https://github.com/hyperledger/aries-cloudagent-python/pull/277)
- Display agent label and version on CLI and SwaggerUI [#274](https://github.com/hyperledger/aries-cloudagent-python/pull/274)
- Remove connection activity tracking and add ping webhooks (with --monitor-ping) [#271](https://github.com/hyperledger/aries-cloudagent-python/pull/271)
- Refactor message transport to track all async tasks, active message handlers [#269](https://github.com/hyperledger/aries-cloudagent-python/pull/269), [#287](https://github.com/hyperledger/aries-cloudagent-python/pull/287)
- Add invitation mode "static" for static connections [#260](https://github.com/hyperledger/aries-cloudagent-python/pull/260)
- Allow for cred proposal underspecification of cred def id, only lock down cred def id at issuer on offer. Sync up api requests to Aries RFC-36 verbiage [#259](https://github.com/hyperledger/aries-cloudagent-python/pull/259)
- Disable cookies on outbound requests (avoid session affinity) [#258](https://github.com/hyperledger/aries-cloudagent-python/pull/258)
- Add plugin registry for managing all loaded protocol plugins, streamline ClassLoader [#257](https://github.com/hyperledger/aries-cloudagent-python/pull/257), [#261](https://github.com/hyperledger/aries-cloudagent-python/pull/261)
- Add support for locking a cache key to avoid repeating expensive operations [#256](https://github.com/hyperledger/aries-cloudagent-python/pull/256)
- Add optional support for uvloop [#255](https://github.com/hyperledger/aries-cloudagent-python/pull/255)
- Output timing information when --timing-log argument is provided [#254](https://github.com/hyperledger/aries-cloudagent-python/pull/254)
- General refactoring - modules moved from messaging into new core, protocols, and utils sub-packages [#250](https://github.com/hyperledger/aries-cloudagent-python/pull/250), [#301](https://github.com/hyperledger/aries-cloudagent-python/pull/301)
- Switch performance demo to the newer issue-credential protocol [#243](https://github.com/hyperledger/aries-cloudagent-python/pull/243)

# 0.3.5

## November 1, 2019

- Switch performance demo to the newer issue-credential protocol [#243](https://github.com/hyperledger/aries-cloudagent-python/pull/243)
- Remove old method for reusing credential requests and replace with local caching for credential offers and requests [#238](https://github.com/hyperledger/aries-cloudagent-python/pull/238), [#242](https://github.com/hyperledger/aries-cloudagent-python/pull/242)
- Add statistics on HTTP requests to timing output [#237](https://github.com/hyperledger/aries-cloudagent-python/pull/237)
- Reduce the number of tags on non-secrets records to reduce storage requirements and improve performance [#235](https://github.com/hyperledger/aries-cloudagent-python/pull/235)

# 0.3.4

## October 23, 2019

- Clean up base64 handling in wallet utils and add tests [#224](https://github.com/hyperledger/aries-cloudagent-python/pull/224)
- Support schema sequence numbers for lookups and caching and allow credential definition tag override via admin API [#223](https://github.com/hyperledger/aries-cloudagent-python/pull/223)
- Support multiple proof referents in the present-proof protocol [#222](https://github.com/hyperledger/aries-cloudagent-python/pull/222)
- Group protocol command line arguments appropriately [#217](https://github.com/hyperledger/aries-cloudagent-python/pull/217)
- Don't require a signature for get_txn_request in credential_definition_id2schema_id and reduce public DID lookups [#215](https://github.com/hyperledger/aries-cloudagent-python/pull/215)
- Add a role property to credential exchange and presentation exchange records [#214](https://github.com/hyperledger/aries-cloudagent-python/pull/214), [#218](https://github.com/hyperledger/aries-cloudagent-python/pull/218)
- Improve attachment decorator handling [#210](https://github.com/hyperledger/aries-cloudagent-python/pull/210)
- Expand and correct documentation of the OpenAPI interface [#208](https://github.com/hyperledger/aries-cloudagent-python/pull/208), [#212](https://github.com/hyperledger/aries-cloudagent-python/pull/212)

# 0.3.3

## September 27, 2019

- Clean up LGTM errors and warnings and fix a message dispatch error [#203](https://github.com/hyperledger/aries-cloudagent-python/pull/203)
- Avoid wrapping messages with Forward wrappers when returning them directly [#199](https://github.com/hyperledger/aries-cloudagent-python/pull/199)
- Add a CLI parameter to override the base URL used in URL-formatted connection invitations [#197](https://github.com/hyperledger/aries-cloudagent-python/pull/197)
- Update the feature discovery protocol to match the RFC and rename the admin API endpoint [#193](https://github.com/hyperledger/aries-cloudagent-python/pull/193)
- Add CLI parameters for specifying additional properties of the printed connection invitation [#192](https://github.com/hyperledger/aries-cloudagent-python/pull/192)
- Add support for explicitly setting the wallet credential ID on storage [#188](https://github.com/hyperledger/aries-cloudagent-python/pull/188)
- Additional performance tracking and storage reductions [#187](https://github.com/hyperledger/aries-cloudagent-python/pull/187)
- Handle connection invitations in base64 or URL format in the Alice demo agent [#186](https://github.com/hyperledger/aries-cloudagent-python/pull/186)
- Add admin API methods to get and set the credential tagging policy for a credential definition ID [#185](https://github.com/hyperledger/aries-cloudagent-python/pull/185)
- Allow querying of credentials for proof requests with multiple referents [#181](https://github.com/hyperledger/aries-cloudagent-python/pull/181)
- Allow self-connected agents to issue credentials, present proofs [#179](https://github.com/hyperledger/aries-cloudagent-python/pull/179)
- Add admin API endpoints to register a ledger nym, fetch a ledger DID verkey, or fetch a ledger DID endpoint [#178](https://github.com/hyperledger/aries-cloudagent-python/pull/178)

# 0.3.2

## September 3, 2019

- Merge support for Aries #36 (issue-credential) and Aries #37 (present-proof) protocols [#164](https://github.com/hyperledger/aries-cloudagent-python/pull/164), [#167](https://github.com/hyperledger/aries-cloudagent-python/pull/167)
- Add `initiator` to connection record queries to ensure uniqueness in the case of a self-connection [#161](https://github.com/hyperledger/aries-cloudagent-python/pull/161)
- Add connection aliases [#149](https://github.com/hyperledger/aries-cloudagent-python/pull/149)
- Misc documentation updates

# 0.3.1

## August 15, 2019

- Do not fail with an error when no ledger is configured [#145](https://github.com/hyperledger/aries-cloudagent-python/pull/145)
- Switch to PyNaCl instead of pysodium; update dependencies [#143](https://github.com/hyperledger/aries-cloudagent-python/pull/143)
- Support reusable connection invitations [#142](https://github.com/hyperledger/aries-cloudagent-python/pull/142)
- Fix --version option and optimize Docker builds [#136](https://github.com/hyperledger/aries-cloudagent-python/pull/136)
- Add connection_id to basicmessage webhooks [#134](https://github.com/hyperledger/aries-cloudagent-python/pull/134)
- Fixes for transaction author agreements [#133](https://github.com/hyperledger/aries-cloudagent-python/pull/133)

# 0.3.0

## August 9, 2019

- Ledger and wallet config updates; add support for transaction author agreements [#127](https://github.com/hyperledger/aries-cloudagent-python/pull/127)
- Handle duplicate schema in send_schema by always fetching first [#126](https://github.com/hyperledger/aries-cloudagent-python/pull/126)
- More flexible timeout support in detect_process [#125](https://github.com/hyperledger/aries-cloudagent-python/pull/125)
- Add start command to run_docker invocations [#119](https://github.com/hyperledger/aries-cloudagent-python/pull/119)
- Add issuer stored state [#114](https://github.com/hyperledger/aries-cloudagent-python/pull/114)
- Add admin route to create a presentation request without sending it [#112](https://github.com/hyperledger/aries-cloudagent-python/pull/112)
- Add -v option to aca-py executable to print version [#110](https://github.com/hyperledger/aries-cloudagent-python/pull/110)
- Fix demo presentation request, optimize credential retrieval [#108](https://github.com/hyperledger/aries-cloudagent-python/pull/108)
- Add pypi badge to README and make document link URLs absolute [#103](https://github.com/hyperledger/aries-cloudagent-python/pull/103)
- Add admin routes for creating and listing wallet DIDs, adjusting the public DID [#102](https://github.com/hyperledger/aries-cloudagent-python/pull/102)
- Update the running locally instructions based on feedback from Sam Smith [#101](https://github.com/hyperledger/aries-cloudagent-python/pull/101)
- Add support for multiple invocation commands, implement start/provision/help commands [#99](https://github.com/hyperledger/aries-cloudagent-python/pull/99)
- Add admin endpoint to send problem report [#98](https://github.com/hyperledger/aries-cloudagent-python/pull/98)
- Add credential received state transition [#97](https://github.com/hyperledger/aries-cloudagent-python/pull/97)
- Adding documentation for the routing version of the performance example [#94](https://github.com/hyperledger/aries-cloudagent-python/pull/94)
- Document listing the Aries RFCs supported by ACA-Py and reference to the list in the README [#89](https://github.com/hyperledger/aries-cloudagent-python/pull/89)
- Further updates to the running locally section of the demo README [#86](https://github.com/hyperledger/aries-cloudagent-python/pull/86)
- Don't extract decorators with names matching the 'data_key' of defined schema fields [#85](https://github.com/hyperledger/aries-cloudagent-python/pull/85)
- Allow demo scripts to run outside of Docker; add command line parsing [#84](https://github.com/hyperledger/aries-cloudagent-python/pull/84)
- Connection invitation fixes and improvements; support DID-based invitations [#82](https://github.com/hyperledger/aries-cloudagent-python/pull/82)

# 0.2.1

## July 16, 2019

- Add missing MANIFEST file [#78](https://github.com/hyperledger/aries-cloudagent-python/pull/78)

# 0.2.0

## July 16, 2019

This is the first PyPI release. The history begins with the transfer of aca-py from [bcgov](https://github.com/bcgov) to [hyperledger](https://github.com/hyperledger).

- Prepare for version 0.2.0 release [#77](https://github.com/hyperledger/aries-cloudagent-python/pull/77)
- Update von-network related references. [#74](https://github.com/hyperledger/aries-cloudagent-python/pull/74)
- Fixed log_level arg, added validation error logging [#73](https://github.com/hyperledger/aries-cloudagent-python/pull/73)
- fix shell inconsistency [#72](https://github.com/hyperledger/aries-cloudagent-python/pull/72)
- further cleanup to the OpenAPI demo script [#71](https://github.com/hyperledger/aries-cloudagent-python/pull/71)
- Updates to invitation handling and performance test [#68](https://github.com/hyperledger/aries-cloudagent-python/pull/68)
- Api security [#67](https://github.com/hyperledger/aries-cloudagent-python/pull/67)
- Fix line endings on Windows [#66](https://github.com/hyperledger/aries-cloudagent-python/pull/66)
- Fix repository name in badge links [#65](https://github.com/hyperledger/aries-cloudagent-python/pull/65)
- Connection record is_ready refactor [#64](https://github.com/hyperledger/aries-cloudagent-python/pull/64)
- Fix API instructions for cred def id [#58](https://github.com/hyperledger/aries-cloudagent-python/pull/58)
- Updated API demo docs to use alice/faber scripts [#54](https://github.com/hyperledger/aries-cloudagent-python/pull/54)
- Updates to the readme for the demo to add PWD support [#53](https://github.com/hyperledger/aries-cloudagent-python/pull/53)
- Swallow empty input in demo scripts [#51](https://github.com/hyperledger/aries-cloudagent-python/pull/51)
- Set credential_exchange state when created from a cached credential request [#49](https://github.com/hyperledger/aries-cloudagent-python/pull/49)
- Check for readiness instead of activeness in credential admin routes [#46](https://github.com/hyperledger/aries-cloudagent-python/pull/46)
- Demo updates [#43](https://github.com/hyperledger/aries-cloudagent-python/pull/43)
- Misc fixes [#42](https://github.com/hyperledger/aries-cloudagent-python/pull/42)
- Readme updates [#41](https://github.com/hyperledger/aries-cloudagent-python/pull/41)
- Change installed "binary" name to aca-py [#40](https://github.com/hyperledger/aries-cloudagent-python/pull/40)
- Tweak in script to work under Linux; updates to readme for demo [#33](https://github.com/hyperledger/aries-cloudagent-python/pull/33)
- New routing example document, typo corrections [#31](https://github.com/hyperledger/aries-cloudagent-python/pull/31)
- More bad links [#30](https://github.com/hyperledger/aries-cloudagent-python/pull/30)
- Links cleanup for the documentation [#29](https://github.com/hyperledger/aries-cloudagent-python/pull/29)
- Alice-Faber demo update [#28](https://github.com/hyperledger/aries-cloudagent-python/pull/28)
- Deployment Model document [#27](https://github.com/hyperledger/aries-cloudagent-python/pull/27)
- Plantuml source and images for documentation; w/image generator script [#26](https://github.com/hyperledger/aries-cloudagent-python/pull/26)
- Move generated documentation. [#25](https://github.com/hyperledger/aries-cloudagent-python/pull/25)
- Update generated documents [#24](https://github.com/hyperledger/aries-cloudagent-python/pull/24)
- Split application configuration into separate modules and add tests [#23](https://github.com/hyperledger/aries-cloudagent-python/pull/23)
- Updates to the RTD configuration file [#22](https://github.com/hyperledger/aries-cloudagent-python/pull/22)
- Merge DIDDoc support from von_anchor [#21](https://github.com/hyperledger/aries-cloudagent-python/pull/21)
- Adding Prov of BC, Gov of Canada copyright [#19](https://github.com/hyperledger/aries-cloudagent-python/pull/19)
- Update test configuration [#18](https://github.com/hyperledger/aries-cloudagent-python/pull/18)
- CI updates [#17](https://github.com/hyperledger/aries-cloudagent-python/pull/17)
- Transport updates [#15](https://github.com/hyperledger/aries-cloudagent-python/pull/15)
