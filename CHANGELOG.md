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
