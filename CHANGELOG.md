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
