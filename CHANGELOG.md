# Aries Cloud Agent Python Changelog

## 1.3.0rc2

### April 28, 2025

ACA-Py 1.3.0 introduces significant improvements across wallet types, AnonCreds support, multi-tenancy, DIDComm interoperability, developer experience, and software supply chain management. This release strengthens stability, modernizes protocol support, and delivers important updates for AnonCreds credential handling. A small number of breaking changes are included and are detailed below.

Updates were made to to the `askar-anoncreds` wallet type ([Askar](https://github.com/openwallet-foundation/askar) plus the latest [AnonCreds Rust](https://github.com/hyperledger/anoncreds-rs) library), addressing issues with multi-ledger configurations, multitenant deployments, and credential handling across different wallet types. Wallet profile management was strengthened by enforcing unique names to avoid conflicts in multitenant environments.

AnonCreds handling saw extensive refinements, including fixes to credential issuance, revocation management, and proof presentation workflows. The release also introduces support for `did:indy` Transaction Version 2 and brings better alignment between the ledger API responses and the expected schemas. Several API documentation updates and improvements to type hints further enhance the developer experience when working with AnonCreds features.

Support for multi-tenancy continues to mature, with fixes that better isolate tenant wallets from the base wallet and improved connection reuse across tenants.

Logging across ACA-Py has been significantly improved to deliver clearer, more actionable logs, while error handling was enhanced to provide better diagnostics for validation failures and resolver setup issues.

Work toward broader interoperability continued, with the introduction of support for the [Verifiable Credentials Data Model (VCDM) 2.0](https://www.w3.org/TR/vc-data-model-2.0/), as well as enhancements to DIDDoc handling, including support for BLS12381G2 key types. A new DIDComm route for fetching existing invitations was added, and a number of minor protocol-level improvements were made to strengthen reliability.

The release also includes many improvements for developers, including a new ACA-Py Helm Chart to simplify Kubernetes deployments, updated tutorials, and more updates to demos (such as [AliceGetsAPhone](https://aca-py.org/latest/demo/AliceGetsAPhone/)). Dependency upgrades across the project further solidify the platform for long-term use.

Significant work was also done in this release to improve the security and integrity of ACA-Py's software supply chain. Updates to the CI/CD pipelines hardened GitHub Actions workflows, introduced pinned dependencies and digests for builds, optimized Dockerfile construction, and improved dependency management practices. These changes directly contribute to a stronger security posture and have improved [ACA-Py's OpenSSF Scorecard evaluation](https://scorecard.dev/viewer/?uri=github.com/openwallet-foundation/acapy), ensuring higher levels of trust and verifiability for those deploying ACA-Py in production environments.

### 1.3.0 Deprecation Notices

- In the next ACA-Py release, we will be dropping from the core ACA-Py repository the [AIP 1.0] [RFC 0037 Issue Credentials v1.0] and [RFC 0037 Present Proof v1.0] DIDComm protocols. Each of the protocols will be moved to the [ACA-Py Plugins] repo. All ACA-Py implementers that use those protocols **SHOULD** update as soon as possible to the [AIP 2.0] versions of those protocols ([RFC 0453 Issue Credential v2.0] and [RFC 0454 Present Proof v2.0], respectively). Once the protocols are removed from ACA-Py, anyone still using those protocols **MUST** adjust their configuration to load those protocols from the respective plugins.

[ACA-Py Plugins]: https://plugins.aca-py.org
[RFC 0160 Connections]: https://identity.foundation/aries-rfcs/latest/features/0160-connection-protocol/
[RFC 0037 Issue Credentials v1.0]: https://identity.foundation/aries-rfcs/latest/features/0036-issue-credential/
[RFC 0037 Present Proof v1.0]: https://identity.foundation/aries-rfcs/latest/features/0037-present-proof/
[AIP 1.0]: https://github.com/decentralized-identity/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-10
[AIP 2.0]: https://identity.foundation/aries-rfcs/latest/aip2/0003-protocols/
[RFC 0434 Out of Band]: https://identity.foundation/aries-rfcs/latest/aip2/0434-outofband/
[RFC 0023 DID Exchange]: https://identity.foundation/aries-rfcs/latest/aip2/0023-did-exchange/
[RFC 0453 Issue Credential v2.0]: https://identity.foundation/aries-rfcs/latest/aip2/0453-issue-credential-v2/
[RFC 0454 Present Proof v2.0]: https://identity.foundation/aries-rfcs/latest/aip2/0454-present-proof-v2/
[Connections Protocol Plugin]: https://plugins.aca-py.org/latest/connections/

### 1.3.0 Breaking Changes

This release includes a small number of breaking changes:

- The DIDComm [RFC 0160 Connections] protocol is removed, in favour of the newer, more complete [RFC 0434 Out of Band] and [RFC 0023 DID Exchange]. Those still requiring [RFC 0160 Connections] protocol support must update their startup parameters to include the [Connections Protocol Plugin]. See the documentation for details, but once the ACA-Py instance startup options are extended to include the Connections protocol plugin, Controllers using the Connections protocol should continue to work as they had been. That said, we highly recommend implementers seeking interoperability move to the [RFC 0434 Out of Band] and [RFC 0023 DID Exchange] Protocols as soon as possible.
- Schema objects related to `did:indy` operations have been renamed to improve clarity and consistency. Clients interacting with `did:indy` endpoints should review and adjust any schema validations or mappings in their applications.

### 1.3.0 ACA-Py Controller API Changes

- `did:indy` support added, including a new `POST /did/indy/create` endpoint.
- Routes that support pagination (such as endpoints for fetching connections or credential/presentation exchange records), now include `descending` as an optional query parameter and have deprecated the `count` and `start` query parameters in favor of the more standard `limit` and `offset` parameters.
- `validFrom` and `validUntil` added to the `Credential` and `VerifiableCredential` objects.
- For consistency (and developer sanity), all `Anoncreds` references in the ACA-Py codebase have been changed to the more common `AnonCreds` (see [PR \#3573](https://github.com/openwallet-foundation/acapy/pull/3573)). Controller references may have to be updated to reflect the update.

Specifics of the majority of the changes can be found by looking at the diffs for the `swagger.json` and `openapi.json` files that are part of the [1.3.0 Release Pull Request](https://github.com/openwallet-foundation/acapy/pull/3604). Later pull requests might introduce some additional changes.

### 1.3.0 Categorized List of Pull Requests

- Updates/fixes to wallet types -- `askar` and `askar-anoncreds`
  - fix: Support askar-anoncreds backend in multi-ledger configuration [\#3603](https://github.com/openwallet-foundation/acapy/pull/3603) [MonolithicMonk](https://github.com/MonolithicMonk)
  - :bug: Fix: allow anoncreds wallet to delete indy credentials [\#3551](https://github.com/openwallet-foundation/acapy/pull/3551) [ff137](https://github.com/ff137)
  - :bug: Fix: allow multitenant askar-anoncreds wallets to present indy credentials [\#3549](https://github.com/openwallet-foundation/acapy/pull/3549) [ff137](https://github.com/ff137)
  - fix: ensure profile names are unique [\#3470](https://github.com/openwallet-foundation/acapy/pull/3470) [dbluhm](https://github.com/dbluhm)
  - feat: add did management design doc [\#3375](https://github.com/openwallet-foundation/acapy/pull/3375) [dbluhm](https://github.com/dbluhm)
  - Add did:indy transaction version 2 support [\#3253](https://github.com/openwallet-foundation/acapy/pull/3253) [jamshale](https://github.com/jamshale)
  - :art: Deprecate count/start query params and implement limit/offset [\#3208](https://github.com/openwallet-foundation/acapy/pull/3208) [ff137](https://github.com/ff137)
  - :sparkles: Add ordering options to askar scan and fetch_all methods [\#3173](https://github.com/openwallet-foundation/acapy/pull/3173) [ff137](https://github.com/ff137)
- Updates/fixes to AnonCreds Processing
  - :art: Fix swagger tag names for AnonCreds endpoints [\#3661](https://github.com/openwallet-foundation/acapy/pull/3661) [ff137](https://github.com/ff137)
  - :art: Add type hints to anoncreds module [\#3652](https://github.com/openwallet-foundation/acapy/pull/3652) [ff137](https://github.com/ff137)
  - :bug: Fix publishing all pending AnonCreds revocations [\#3626](https://github.com/openwallet-foundation/acapy/pull/3626) [ff137](https://github.com/ff137)
  - :art: Rename Anoncreds to AnonCreds [\#3573](https://github.com/openwallet-foundation/acapy/pull/3573) [ff137](https://github.com/ff137)
  - :art: Use correct model for sending AnonCreds presentation [\#3618](https://github.com/openwallet-foundation/acapy/pull/3618) [ff137](https://github.com/ff137)
  - fix: align ledger config schema with API response [\#3615](https://github.com/openwallet-foundation/acapy/pull/3615) [MonolithicMonk](https://github.com/MonolithicMonk)
  - fix(ledger): correct response format for /ledger/get-write-ledgers endpoint [\#3613](https://github.com/openwallet-foundation/acapy/pull/3613) [MonolithicMonk](https://github.com/MonolithicMonk)
  - :bug: Fix unchanged endpoint being rewritten to ledger [\#3608](https://github.com/openwallet-foundation/acapy/pull/3608) [ff137](https://github.com/ff137)
  - :bug: Fix auto creation of revocation registries [\#3601](https://github.com/openwallet-foundation/acapy/pull/3601) [ff137](https://github.com/ff137)
  - :sparkles: Refactor TailsServer injection pattern [\#3587](https://github.com/openwallet-foundation/acapy/pull/3587) [ff137](https://github.com/ff137)
  - :bug: Fix: Register both askar and anoncreds plugins for multitenancy [\#3585](https://github.com/openwallet-foundation/acapy/pull/3585) [ff137](https://github.com/ff137)
  - Repair anoncreds holder revocation list request [\#3570](https://github.com/openwallet-foundation/acapy/pull/3570) [jamshale](https://github.com/jamshale)
  - Anoncreds proof validation issue (once credential has been revoked) [\#3557](https://github.com/openwallet-foundation/acapy/pull/3557) [ianco](https://github.com/ianco)
  - Fix revocation accum sync when endorsement txn fails [\#3547](https://github.com/openwallet-foundation/acapy/pull/3547) [jamshale](https://github.com/jamshale)
  - Allow schema id to be used during anoncreds issuance [\#3497](https://github.com/openwallet-foundation/acapy/pull/3497) [jamshale](https://github.com/jamshale)
  - Fix Class import for AnonCreds Registry routes [\#3495](https://github.com/openwallet-foundation/acapy/pull/3495) [PatStLouis](https://github.com/PatStLouis)
  - fix typo in error message of indy credential offer [\#3485](https://github.com/openwallet-foundation/acapy/pull/3485) [zoblazo](https://github.com/zoblazo)
  - Fixing BaseAnonCredsResolver get_revocation_list abstract method [\#3484](https://github.com/openwallet-foundation/acapy/pull/3484) [thiagoromanos](https://github.com/thiagoromanos)
  - Anoncreds Issuance - Extra options. [\#3483](https://github.com/openwallet-foundation/acapy/pull/3483) [jamshale](https://github.com/jamshale)
- Multi-Tenancy Related Updates and Fixes:
  - fix: tenant access to endpoints leading to access the base wallet [\#3545](https://github.com/openwallet-foundation/acapy/pull/3545) [thiagoromanos](https://github.com/thiagoromanos)
  - fix: connection reuse with multi-tenancy [\#3543](https://github.com/openwallet-foundation/acapy/pull/3543) [dbluhm](https://github.com/dbluhm)
  - Remove base wallet type must be new wallet type restriction [\#3542](https://github.com/openwallet-foundation/acapy/pull/3542) [jamshale](https://github.com/jamshale)
- Logging and Error Handling Updates and Fixes:
  - :art: Replace print statements in Banner with info log [\#3643](https://github.com/openwallet-foundation/acapy/pull/3643) [ff137](https://github.com/ff137)
  - :sparkles: Improve logging in core components [\#3332](https://github.com/openwallet-foundation/acapy/pull/3332) [ff137](https://github.com/ff137)
  - :art: Include the validation error in Unprocessable Entity reason [\#3517](https://github.com/openwallet-foundation/acapy/pull/3517) [ff137](https://github.com/ff137)
  - Catch and log universal resolver setup error [\#3511](https://github.com/openwallet-foundation/acapy/pull/3511) [jamshale](https://github.com/jamshale)
- W3C Verifiable Credentials Support Updates and Fixes:
  - Add vcdm 2.0 model and context [\#3436](https://github.com/openwallet-foundation/acapy/pull/3436) [PatStLouis](https://github.com/PatStLouis)
- DID Doc Handling Updates
  - (fix) VM resolution strategy correction for embedded VMs [\#3665](https://github.com/openwallet-foundation/acapy/pull/3665) [gmulhearn](https://github.com/gmulhearn)
  - :bug: Fix public did no longer being correctly configured [\#3646](https://github.com/openwallet-foundation/acapy/pull/3646) [ff137](https://github.com/ff137)
  - :art: Add type hints to `messaging/jsonld` [\#3650](https://github.com/openwallet-foundation/acapy/pull/3650) [ff137](https://github.com/ff137)
  - Add BLS12381G2 keys to multikey manager [\#3640](https://github.com/openwallet-foundation/acapy/pull/3640) [gmulhearn](https://github.com/gmulhearn)
  - (fix) VM resolution strategy correction [\#3622](https://github.com/openwallet-foundation/acapy/pull/3622) [gmulhearn](https://github.com/gmulhearn)
- DIDComm Protocol Updates and Fixes:
  - Fetch existing invitation route [\#3572](https://github.com/openwallet-foundation/acapy/pull/3572) [PatStLouis](https://github.com/PatStLouis)
  - BREAKING: remove connection protocol [\#3184](https://github.com/openwallet-foundation/acapy/pull/3184) [dbluhm](https://github.com/dbluhm)
- Indy Ledger Handling Updates/Fixes
  - :art: Make ledger config more readable [\#3664](https://github.com/openwallet-foundation/acapy/pull/3664) [ff137](https://github.com/ff137)
  - :art: Rename did:indy create/response schema objects [\#3663](https://github.com/openwallet-foundation/acapy/pull/3663) [ff137](https://github.com/ff137)
  - :sparkles: Don't shutdown on ledger error [\#3636](https://github.com/openwallet-foundation/acapy/pull/3636) [ff137](https://github.com/ff137)
- Documentation and Tutorial Pull Requests:
  - Use current version of aca-py in devcontainer [\#3638](https://github.com/openwallet-foundation/acapy/pull/3638) [esune](https://github.com/esune)
  - Devcointainer and docs update [\#3629](https://github.com/openwallet-foundation/acapy/pull/3629) [esune](https://github.com/esune)
  - AliceGetsAPhone demo works in local docker environment [\#3623](https://github.com/openwallet-foundation/acapy/pull/3623) [davidchaiken](https://github.com/davidchaiken)
  - feat(demo): remove broken aip 10 and fix aip 20 [\#3611](https://github.com/openwallet-foundation/acapy/pull/3611) [davidchaiken](https://github.com/davidchaiken)
  - Fix demo implementation of vc_di cred issue [\#3609](https://github.com/openwallet-foundation/acapy/pull/3609) [ianco](https://github.com/ianco)
  - chore(demo): remove aip 10 code [\#3619](https://github.com/openwallet-foundation/acapy/pull/3619) [davidchaiken](https://github.com/davidchaiken)
  - Create Acapy Helm Chart [\#3599](https://github.com/openwallet-foundation/acapy/pull/3599) [i5okie](https://github.com/i5okie)
  - :memo: Update README [\#3588](https://github.com/openwallet-foundation/acapy/pull/3588) [ff137](https://github.com/ff137)
  - Fix missing log_timer import in acme.py [\#3562](https://github.com/openwallet-foundation/acapy/pull/3562) [parth5805](https://github.com/parth5805)
  - Fix prompt for alice/faber demo [\#3553](https://github.com/openwallet-foundation/acapy/pull/3553) [ianco](https://github.com/ianco)
  - Add reuse document to MkDocs YML to add to doc site [\#3535](https://github.com/openwallet-foundation/acapy/pull/3535) [swcurran](https://github.com/swcurran)
  - Create ReuseConnection.md [\#3534](https://github.com/openwallet-foundation/acapy/pull/3534) [MonolithicMonk](https://github.com/MonolithicMonk)
  - :white_check_mark: Fix demo playground example tests [\#3531](https://github.com/openwallet-foundation/acapy/pull/3531) [ff137](https://github.com/ff137)
  - :arrow_up: Upgrade sphinx versions in docs [\#3530](https://github.com/openwallet-foundation/acapy/pull/3530) [ff137](https://github.com/ff137)
- ACA-Py Testing and CI/CD Pull Requests:
  - :bug: Fix permissions in nightly publish job [\#3682](https://github.com/openwallet-foundation/acapy/pull/3682) [ff137](https://github.com/ff137)
  - :lock: Update Token Permissions in GitHub Actions [\#3678](https://github.com/openwallet-foundation/acapy/pull/3678) [ff137](https://github.com/ff137)
  - :lock: ci: Harden GitHub Actions [\#3670](https://github.com/openwallet-foundation/acapy/pull/3670) [step-security-bot](https://github.com/step-security-bot)
  - :construction_worker: Update dependabot file [\#3669](https://github.com/openwallet-foundation/acapy/pull/3669) [ff137](https://github.com/ff137)
  - :pushpin: Pin Actions to a full length commit SHA and image tags to digests [\#3668](https://github.com/openwallet-foundation/acapy/pull/3668) [step-security-bot](https://github.com/step-security-bot)
  - :test_tube: Fix test warnings [\#3656](https://github.com/openwallet-foundation/acapy/pull/3656) [ff137](https://github.com/ff137)
  - :construction_worker: :technologist: Optimize Docker build to reduce cache invalidation [\#3655](https://github.com/openwallet-foundation/acapy/pull/3655) [rblaine95](https://github.com/rblaine95)
  - 👷 Split Docker Builds [\#3654](https://github.com/openwallet-foundation/acapy/pull/3654) [rblaine95](https://github.com/rblaine95)
  - :construction_worker: Fix Docker Caching [\#3653](https://github.com/openwallet-foundation/acapy/pull/3653) [rblaine95](https://github.com/rblaine95)
  - Repair BDD integration release tests [\#3605](https://github.com/openwallet-foundation/acapy/pull/3605) [jamshale](https://github.com/jamshale)
  - Indicate when interop tests fail [\#3592](https://github.com/openwallet-foundation/acapy/pull/3592) [jamshale](https://github.com/jamshale)
  - :zap: Automatically use pytest-xdist to run tests in parallel [\#3574](https://github.com/openwallet-foundation/acapy/pull/3574) [ff137](https://github.com/ff137)
  - :arrow_up: Upgrade poetry to 2.1 [\#3538](https://github.com/openwallet-foundation/acapy/pull/3538) [ff137](https://github.com/ff137)
  - :zap: Remove `--cov` from pytest.ini_options [\#3522](https://github.com/openwallet-foundation/acapy/pull/3522) [ff137](https://github.com/ff137)
  - :heavy_plus_sign: Re-add `git` to Dockerfile [\#3515](https://github.com/openwallet-foundation/acapy/pull/3515) [ff137](https://github.com/ff137)
  - Restore connection route tests [\#3461](https://github.com/openwallet-foundation/acapy/pull/3461) [dbluhm](https://github.com/dbluhm)
- Dependency Management pull requests (other than Dependabot):
  - :arrow_up: Weekly dependency updates [\#3634](https://github.com/openwallet-foundation/acapy/pull/3634) [ff137](https://github.com/ff137)
  - Upgrade docker images to release 1.2.4 [\#3597](https://github.com/openwallet-foundation/acapy/pull/3597) [jamshale](https://github.com/jamshale)
  - Update changed-files to non vulnerable version [\#3591](https://github.com/openwallet-foundation/acapy/pull/3591) [ryjones](https://github.com/ryjones)
  - :arrow_up: Update lock file [\#3590](https://github.com/openwallet-foundation/acapy/pull/3590) [ff137](https://github.com/ff137)
  - :arrow_up: Upgrade ruff to 0.11 [\#3589](https://github.com/openwallet-foundation/acapy/pull/3589) [ff137](https://github.com/ff137)
  - Update acapy images to 1.2.3 [\#3571](https://github.com/openwallet-foundation/acapy/pull/3571) [jamshale](https://github.com/jamshale)
  - :construction_worker: Dependabot: don't ignore major releases [\#3521](https://github.com/openwallet-foundation/acapy/pull/3521) [ff137](https://github.com/ff137)
  - Grouped upgrades - Week 7, 2025 [\#3508](https://github.com/openwallet-foundation/acapy/pull/3508) [jamshale](https://github.com/jamshale)
  - Upgrade to bookworm [\#3498](https://github.com/openwallet-foundation/acapy/pull/3498) [jamshale](https://github.com/jamshale)
  - Update aries-askar / Generate poetry.lock with poetry 2.0 [\#3478](https://github.com/openwallet-foundation/acapy/pull/3478) [jamshale](https://github.com/jamshale)
  - Upgrade askar and did_webvh [\#3474](https://github.com/openwallet-foundation/acapy/pull/3474) [jamshale](https://github.com/jamshale)
  - Update dockerfile image after release [\#3469](https://github.com/openwallet-foundation/acapy/pull/3469) [jamshale](https://github.com/jamshale)
  - :arrow_up: Upgrade dependencies [\#3455](https://github.com/openwallet-foundation/acapy/pull/3455) [ff137](https://github.com/ff137)
- Release management pull requests:
  - 1.3.0rc2 [\#3687](https://github.com/openwallet-foundation/acapy/pull/3687) [swcurran](https://github.com/swcurran)
  - 1.3.0rc1 [\#3628](https://github.com/openwallet-foundation/acapy/pull/3628) [swcurran](https://github.com/swcurran)
  - 1.3.0rc0 [\#3604](https://github.com/openwallet-foundation/acapy/pull/3604) [swcurran](https://github.com/swcurran)
- Dependabot PRs
  - [Link to list of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A2025-01-21..2025-04-28+author%3Aapp%2Fdependabot+)

## 1.2.4

### March 13, 2025

This patch release addresses three bugs backported from the `main` branch:

- Fixes a problem in the handling of connection reuse in multitenancy environments. This is a backport of the PR [fix: connection reuse with multi-tenancy #3543](https://github.com/openwallet-foundation/acapy/pull/3543). This fixes the issue when using multi-tenancy, calls to `POST /out-of-band/receive-invitation?use_existing_connection=true` failing with a record not found error, despite connection reuse actually being completed in the background.
- Fixes a problem when using acapy with multitenant enabled and admin-insecure-mode. Without this fix, tenant endpoints (like `GET /wallet/did` for example) could be accessed without a bearer token. For details see: [fix: tenant access to endpoints leading to access the base wallet #3545](https://github.com/openwallet-foundation/acapy/pull/3545).
- Fixes the AnonCreds holder revocation list endpoint which was erroneously using the `to` timestamp for the `from`, preventing the creation of valid non-revocation proofs. For details, see: [Repair anoncreds holder revocation list request](https://github.com/openwallet-foundation/acapy/pull/3570)

### 1.2.4 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.1.0](#110) release about AIP 1.0 protocols still apply. The protocols remain in this 1.2.4 release, but the Connections Protocol has been removed from the ACA-Py `main` branch, and is available as a [plugin](https://github.com/openwallet-foundation/acapy-plugins/tree/main/connections). The Issue Credential v1 and Present Proof v1 protocols will soon be changed similarly. Please review these notifications carefully!

### 1.2.4 Breaking Changes

There are no breaking changes in this release.

### 1.2.4 Categorized List of Pull Requests

- AnonCreds Revocation Fixes
  - 1.2.LTS Repair anoncreds holder revocation list request [\#3580](https://github.com/openwallet-foundation/acapy/pull/3580) [jamshale](https://github.com/jamshale)
- Multitenant Fixes
  - fix: cherry-pick fixes from main to 1.2.lts [\#3577](https://github.com/openwallet-foundation/acapy/pull/3577) [thiagoromanos](https://github.com/thiagoromanos)

- Release management pull requests:
  - 1.2.4 [\#3582](https://github.com/openwallet-foundation/acapy/pull/3582) [swcurran](https://github.com/swcurran)

## 1.2.3

### March 6, 2025

This patch release addresses a bug in the publishing of AnonCreds revocation entries that caused the ledger and issuer wallet to become out of sync. As a result, revoked credentials were not being correctly flagged as revoked when presented. Previously, this issue was mitigated by an automatic “sync-revocation” process, which generally resolved the problem. However, we recently identified scenarios where the presence of an Indy Endorser in the revocation publication flow caused the “sync-revocation” process to fail silently.

This patch resolves that issue. Once applied, if a revocation batch results in an out-of-sync state, the “sync-revocation” process will automatically run to correct it.

For more details, see [Issue 3546](https://github.com/openwallet-foundation/acapy/issues/3546).

### 1.2.3 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.1.0](#110) release about AIP 1.0 protocols still apply. The protocols remain in this 1.2.3 release, but the Connections Protocol has been removed from the ACA-Py `main` branch, and is available as a [plugin](https://github.com/openwallet-foundation/acapy-plugins/tree/main/connections). The Issue Credential v1 and Present Proof v1 protocols will soon be changed similarly. Please review these notifications carefully!

### 1.2.3 Breaking Changes

There are no breaking changes in this release.

### 1.2.3 Categorized List of Pull Requests

- AnonCreds Revocation Fixes
  - 1.2.LTS Fix revocation accum sync when endorsement txn fails (#3547) [\#3555](https://github.com/openwallet-foundation/acapy/pull/3555) [jamshale](https://github.com/jamshale)

- Release management pull requests:
  - 1.2.3 [\#3559](https://github.com/openwallet-foundation/acapy/pull/3559) [swcurran](https://github.com/swcurran)

## 1.2.2

### January 30, 2025

A patch release to upgrade [Askar](https://github.com/openwallet-foundation/askar) to [0.4.3](https://github.com/openwallet-foundation/askar/releases/tag/v0.4.3) and fixes a problem with wallet names in a multitenant, single-wallet configuration.

Addresses the problem outlined in [#3471](https://github.com/openwallet-foundation/acapy/issues/3471) around profiles in multi-tenant/single wallet deployments. The update to Askar addresses an intermittent hang on startup, and a dependency change that can result in a substantial performance improvement in some cases. See issues: [openwallet-foundation/askar#350](https://github.com/openwallet-foundation/askar/pull/350), [openwallet-foundation/askar#351](https://github.com/openwallet-foundation/askar/pull/351), [openwallet-foundation/askar#354](https://github.com/openwallet-foundation/askar/pull/354). This [comment on one of the PRs](https://github.com/openwallet-foundation/askar/pull/350#issuecomment-2615727109) describes the scenario where a substantial performance improvement was seen as a result of the change in Askar.

### 1.2.2 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.1.0](#110) release about AIP 1.0 protocols still apply. The protocols remain in the 1.2.2 release, but will be moved out of the core and into plugins soon. Please review these notifications carefully!

### 1.2.2 Breaking Changes

There are no breaking changes in this release.

### 1.2.2 Categorized List of Pull Requests

- Startup, Wallet, and Upgrade Fixes
  - 1.2 LTS: Askar upgrade and fix profile unique names [\#3477](https://github.com/openwallet-foundation/acapy/pull/3477) [jamshale](https://github.com/jamshale)

- Release management pull requests:
  - 1.2.2 [\#3482](https://github.com/openwallet-foundation/acapy/pull/3482) [swcurran](https://github.com/swcurran)

## 1.2.1

### January 21, 2025

Release 1.2.1 is a patch to fix a couple of issues introduced in [Release 1.2.0](#120) that prevent the startup of multi-tenant/single database instances of ACA-Py. The release includes the fixes, plus a new test for testing ACA-Py upgrades -- a new test type introduced in [Release 1.2.0](#120). Given that there are no breaking changes in this release, we'll move the [1.2.lts branch](https://github.com/openwallet-foundation/acapy/tree/1.2.lts) to be based on this release.

Enhancements in Release 1.2.1 are the addition of support for the Linked Data proof cryptosuite `EcdsaSecp256r1Signature2019`, and support for P256 keys generally and in `did:key` form.

### 1.2.1 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.1.0](#110) release about AIP 1.0 protocols still apply. The protocols remain in the 1.2.1 release, but will be moved out of the core and into plugins soon. Please review these notifications carefully!

### 1.2.1 Breaking Changes

There are no breaking changes in this release, just fixes, new tests and minor updates.

### 1.2.1 Categorized List of Pull Requests

- Linked Data Proof and Key Type Additions
  - Support EcdsaSecp256r1Signature2019 linked data proof [\#3443](https://github.com/openwallet-foundation/acapy/pull/3443) [gmulhearn](https://github.com/gmulhearn)
  - Support P256 keys & did:keys [\#3442](https://github.com/openwallet-foundation/acapy/pull/3442) [gmulhearn](https://github.com/gmulhearn)

- Startup, Wallet Keys, and Upgrade Fixes
  - Check admin wallet anoncreds upgrade on startup [\#3458](https://github.com/openwallet-foundation/acapy/pull/3458) [jamshale](https://github.com/jamshale)
  - Add Multi-tenancy single wallet upgrade test [\#3457](https://github.com/openwallet-foundation/acapy/pull/3457) [jamshale](https://github.com/jamshale)
  - Pass the correct key for multitenant single wallets [\#3450](https://github.com/openwallet-foundation/acapy/pull/3450) [jamshale](https://github.com/jamshale)
  - Prevent dummy profiles on start up [\#3449](https://github.com/openwallet-foundation/acapy/pull/3449) [jamshale](https://github.com/jamshale)
  - Fixed handling of base wallet routes in auth decorator [\#3448](https://github.com/openwallet-foundation/acapy/pull/3448) [esune](https://github.com/esune)

- DID Registration and Resolution
  - Change did:tdw resolver naming to did:webvh [\#3429](https://github.com/openwallet-foundation/acapy/pull/3429) [jamshale](https://github.com/jamshale)

- Test Suite Updates and Artifact Publishing
  - Only copy agent code in dockerfiles [\#3393](https://github.com/openwallet-foundation/acapy/pull/3393) [jamshale](https://github.com/jamshale)

- Internal Improvements / Cleanups / Tech Debt Updates
  - Update versions.json to correct the version drop down on aca-py.org [\#3434](https://github.com/openwallet-foundation/acapy/pull/3434) [swcurran](https://github.com/swcurran)
  - Follow up from Release 1.2.0 -- including LTS change [\#3432](https://github.com/openwallet-foundation/acapy/pull/3432) [swcurran](https://github.com/swcurran)

- Consolidate Dependabot updates and other library/dependency updates
  - :arrow_up: Upgrade dev dependencies [\#3454](https://github.com/openwallet-foundation/acapy/pull/3454) [ff137](https://github.com/ff137)
  - :recycle: Sync ruff version in workflows [\#3447](https://github.com/openwallet-foundation/acapy/pull/3447) [ff137](https://github.com/ff137)

- Release management pull requests:
  - 1.2.1 [\#3460](https://github.com/openwallet-foundation/acapy/pull/3460) [swcurran](https://github.com/swcurran)
  - 1.2.1rc0 [\#3459](https://github.com/openwallet-foundation/acapy/pull/3459) [swcurran](https://github.com/swcurran)

- Dependabot PRs
  - [Link to list of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A2025-01-08..2025-01-21+author%3Aapp%2Fdependabot+)

## 1.2.0

### January 8, 2025

!!! warning "Multi-tenant, Single Database Deployments"

    A bug in Release 1.2.0 prevents using the release with existing multi-tenant, single wallet deployments. Those requiring such support **MUST** skip Release 1.2.0 and move to [Release 1.2.1](https://github.com/openwallet-foundation/acapy/releases/tag/1.2.1) or higher.

Release 1.2.0 is a minor update to ACA-Py that contains an update to the AnonCreds implementation to make it easier to deploy on other than Hyperledger Indy, and a lengthy list of adjustments, improvements and fixes, with a focus on removing technical debt. In addition to the AnonCreds updates, the most visible change is the removal of the "in-memory wallet" implementation in favour of using the SQLite in-memory wallet (`sqlite://:memory:`), including removing the logic for handling that extra wallet type. In removing the in-memory wallet, all of the unit and integration tests that used the in-memory wallet have been updated to use SQLite's in-memory wallet.

Release 1.2.x is the new current Long Term Support (LTS) for ACA-Py, as defined in the [LTS Strategy](./LTS-Strategy.md) document. With this release, the "end of life" for the previous "current LTS release" -- [0.12](#0123) -- is set for October 2025.

The first step to full support of [did:webvh](https://identity.foundation/didwebvh/) ("`did:web` + Verifiable History"-- formerly `did:tdw`) has been added to ACA-Py -- a resolver. We're working on improving the new DID Registration mechanism for it, [Cheqd] and other DID Methods, enabling ACA-Py to be used easily with a variety of DID Methods.

[Cheqd]: https://cheqd.io/

The move to the [OpenWallet Foundation](https://openwallet.foundation/) is now complete. If you haven't done so already, please update your ACA-Py deployment to use:

- the [ACA-Py OWF repository](https://github.com/openwallet-foundation/acapy),
- the new [acapy-agent in PyPi](https://pypi.org/project/acapy-agent/), and
- the container images for ACA-Py hosted by the OpenWallet Foundation GitHub organization within the GitHub Container Repository (GHCR).

A significant testing capability was added in this release -- the ability to run an integration test that includes an ACA-Py upgrade in the middle. This allows us to test, for example starting an agent on one release, doing an upgrade (possibly including running a migration script), and then completing the test on the upgraded release. This is enable by adding a capability to restart Docker containers in the middle of tests. Nice work, @ianco!

### 1.2.0 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.1.0](#110) release about AIP 1.0 protocols still apply. The protocols remain in the 1.2.0 release, but will be moved out of the core and into plugins soon. Please review these notifications carefully!

### 1.2.0 Breaking Changes

The removal of the "in-memory" wallet implementation might be break some test scripts. Rather than using the in-memory wallet, tests should be updated to use SQLite's special `sqlite://:memory:` database instead. This results in a better alignment between the Askar storage configuration in test environments and what is used in production.

A fix for a multi-tenancy bug in the holding of VC-LD credentials that resulted in the storing of such credentials in the base wallet versus the intended tenant wallet in included in this release. As part of that fix, [PR #3391] impacts those using the GET /vc/credentials endpoint; the response is now an object with a single results attribute where it was previously a flat list.

[PR #3391]: https://github.com/openwallet-foundation/acapy/pull/3391

### 1.2.0 Categorized List of Pull Requests

- AnonCreds VC Issuance and Presentation Enhancement / Fixes
  - Fix indy fallback format in presentation from holder [\#3413](https://github.com/openwallet-foundation/acapy/pull/3413) [jamshale](https://github.com/jamshale)
  - Anoncreds post api object handling [\#3411](https://github.com/openwallet-foundation/acapy/pull/3411) [jamshale](https://github.com/jamshale)
  - fix: Anoncreds schemas and validation [\#3397](https://github.com/openwallet-foundation/acapy/pull/3397) [DaevMithran](https://github.com/DaevMithran)
  - Update accumulator value in wallet on repair [\#3299](https://github.com/openwallet-foundation/acapy/pull/3299) [jamshale](https://github.com/jamshale)
  - Repair release bdd tests [\#3376](https://github.com/openwallet-foundation/acapy/pull/3376) [jamshale](https://github.com/jamshale)
  - Update anoncreds format names [\#3374](https://github.com/openwallet-foundation/acapy/pull/3374) [jamshale](https://github.com/jamshale)
  - Anoncreds create credential [\#3369](https://github.com/openwallet-foundation/acapy/pull/3369) [jamshale](https://github.com/jamshale)
  - Fix tails upload for anoncreds multitenancy [\#3346](https://github.com/openwallet-foundation/acapy/pull/3346) [jamshale](https://github.com/jamshale)
  - Fix subwallet anoncreds upgrade check [\#3345](https://github.com/openwallet-foundation/acapy/pull/3345) [jamshale](https://github.com/jamshale)
  - Add anoncreds issuance and presentation format [\#3331](https://github.com/openwallet-foundation/acapy/pull/3331) [jamshale](https://github.com/jamshale)
  - Fix endorsement setup with existing connection [\#3309](https://github.com/openwallet-foundation/acapy/pull/3309) [jamshale](https://github.com/jamshale)

- Middleware Handling and Multi-tenancy
  - BREAKING: VCHolder multitenant binding [\#3391](https://github.com/openwallet-foundation/acapy/pull/3391) [jamshale](https://github.com/jamshale)
  - Restore `--base-wallet-routes` flag functionality [\#3344](https://github.com/openwallet-foundation/acapy/pull/3344) [esune](https://github.com/esune)
  - :white_check_mark: Re-add ready_middleware unit tests [\#3330](https://github.com/openwallet-foundation/acapy/pull/3330) [ff137](https://github.com/ff137)
  - :sparkles: Handle NotFound and UnprocessableEntity errors in middleware [\#3327](https://github.com/openwallet-foundation/acapy/pull/3327) [ff137](https://github.com/ff137)
  - :art: Refactor Multitenant Manager errors and exception handling [\#3323](https://github.com/openwallet-foundation/acapy/pull/3323) [ff137](https://github.com/ff137)
  - Don't pass rekey to sub_wallet_profile [\#3312](https://github.com/openwallet-foundation/acapy/pull/3312) [jamshale](https://github.com/jamshale)

- DID Registration and Resolution
  - :bug: Ensure supported DID before calling Rotate [\#3380](https://github.com/openwallet-foundation/acapy/pull/3380) [ff137](https://github.com/ff137)
  - fix: check routing keys on indy_vdr endpoint refresh [\#3371](https://github.com/openwallet-foundation/acapy/pull/3371) [dbluhm](https://github.com/dbluhm)
  - Fix/universal resolver [\#3354](https://github.com/openwallet-foundation/acapy/pull/3354) [jamshale](https://github.com/jamshale)
  - More robust verification method selection by did [\#3279](https://github.com/openwallet-foundation/acapy/pull/3279) [dbluhm](https://github.com/dbluhm)
  - did:tdw resolver [\#3237](https://github.com/openwallet-foundation/acapy/pull/3237) [jamshale](https://github.com/jamshale)

- DIDComm Updates and Enhancements
  - :bug: Rearrange connection record deletion after hangup [\#3310](https://github.com/openwallet-foundation/acapy/pull/3310) [ff137](https://github.com/ff137)
  - :bug: Handle failure to resolve DIDComm services in DIDXManager [\#3298](https://github.com/openwallet-foundation/acapy/pull/3298) [ff137](https://github.com/ff137)

- Test Suite Updates and Artifact Publishing
  - Scenario test with anoncreds wallet upgrade and restart [\#3410](https://github.com/openwallet-foundation/acapy/pull/3410) [ianco](https://github.com/ianco)
  - Add legacy pypi token [\#3408](https://github.com/openwallet-foundation/acapy/pull/3408) [jamshale](https://github.com/jamshale)
  - Aca-Py test scenario including a container restart (with aca-py version upgrade) [\#3400](https://github.com/openwallet-foundation/acapy/pull/3400) [ianco](https://github.com/ianco)
  - Adjust coverage location for sonarcloud [\#3399](https://github.com/openwallet-foundation/acapy/pull/3399) [jamshale](https://github.com/jamshale)
  - Remove sonar cov report move step [\#3398](https://github.com/openwallet-foundation/acapy/pull/3398) [jamshale](https://github.com/jamshale)
  - Update Sonarcloud to new action [\#3390](https://github.com/openwallet-foundation/acapy/pull/3390) [ryjones](https://github.com/ryjones)
  - Switch to COPY commands in dockerfiles [\#3389](https://github.com/openwallet-foundation/acapy/pull/3389) [jamshale](https://github.com/jamshale)
  - Fix sonar coverage on merge main [\#3388](https://github.com/openwallet-foundation/acapy/pull/3388) [jamshale](https://github.com/jamshale)
  - Add test wallet config option [\#3355](https://github.com/openwallet-foundation/acapy/pull/3355) [jamshale](https://github.com/jamshale)
  - :art: Fix current test warnings [\#3338](https://github.com/openwallet-foundation/acapy/pull/3338) [ff137](https://github.com/ff137)
  - :construction_worker: Fix Nightly Publish to not run on forks [\#3333](https://github.com/openwallet-foundation/acapy/pull/3333) [ff137](https://github.com/ff137)

- Internal Improvements / Cleanups / Tech Debt Updates
  - Fix devcontainer poetry install [\#3428](https://github.com/openwallet-foundation/acapy/pull/3428) [jamshale](https://github.com/jamshale)
  - Pin poetry to 1.8.3 in dockerfiles [\#3427](https://github.com/openwallet-foundation/acapy/pull/3427) [jamshale](https://github.com/jamshale)
  - Adds the OpenSSF to the readme [\#3412](https://github.com/openwallet-foundation/acapy/pull/3412) [swcurran](https://github.com/swcurran)
  - The latest tag doesn't exist in git, just github [\#3392](https://github.com/openwallet-foundation/acapy/pull/3392) [ryjones](https://github.com/ryjones)
  - :art: Fix model name for consistency [\#3382](https://github.com/openwallet-foundation/acapy/pull/3382) [ff137](https://github.com/ff137)
  - Fix for demo initial cred_type override [\#3378](https://github.com/openwallet-foundation/acapy/pull/3378) [ianco](https://github.com/ianco)
  - :zap: Add class caching to DeferLoad [\#3361](https://github.com/openwallet-foundation/acapy/pull/3361) [ff137](https://github.com/ff137)
  - :art: Sync Ruff version in configs and apply formatting [\#3358](https://github.com/openwallet-foundation/acapy/pull/3358) [ff137](https://github.com/ff137)
  - :art: Replace deprecated ABC decorators [\#3357](https://github.com/openwallet-foundation/acapy/pull/3357) [ff137](https://github.com/ff137)
  - :art: Refactor the logging module monolith [\#3319](https://github.com/openwallet-foundation/acapy/pull/3319) [ff137](https://github.com/ff137)
  - :wrench: set default fixture scope for pytest-asyncio [\#3318](https://github.com/openwallet-foundation/acapy/pull/3318) [ff137](https://github.com/ff137)
  - Docs (devcontainer) Change folder names [\#3317](https://github.com/openwallet-foundation/acapy/pull/3317) [loneil](https://github.com/loneil)
  - :art: Refactor string concatenation in model descriptions [\#3313](https://github.com/openwallet-foundation/acapy/pull/3313) [ff137](https://github.com/ff137)
  - Remove in memory wallet [\#3311](https://github.com/openwallet-foundation/acapy/pull/3311) [jamshale](https://github.com/jamshale)

- Consolidate Dependabot updates and other library/dependency updates
  - Week 49 Library upgrades [\#3368](https://github.com/openwallet-foundation/acapy/pull/3368) [jamshale](https://github.com/jamshale)
  - :arrow_up: Update lock file [\#3296](https://github.com/openwallet-foundation/acapy/pull/3296) [ff137](https://github.com/ff137)

- Release management pull requests:
  - 1.2.0 [\#3430](https://github.com/openwallet-foundation/acapy/pull/3430) [swcurran](https://github.com/swcurran)
  - 1.2.0rc0 [\#3420](https://github.com/openwallet-foundation/acapy/pull/3420) [swcurran](https://github.com/swcurran)
  - 1.1.1rc0 [\#3372](https://github.com/openwallet-foundation/acapy/pull/3372) [swcurran](https://github.com/swcurran)

- Dependabot PRs
  - [Link to list of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A2024-10-15..2025-01-08+author%3Aapp%2Fdependabot+)

## 1.1.1

ACA-Py Release 1.1.1 was a release candidate for 1.2.0. A mistake in the release PR meant the 1.1.1rc0 was tagged published to PyPi as Release 1.1.1. Since that was not intended to be a final release, the release changelog for 1.2.0 includes the Pull Requests that would have been in 1.1.1.

## 1.1.0

### October 15, 2024

Release 1.1.0 is the first release of ACA-Py from the [OpenWallet Foundation] (OWF). The only reason for the release is to test out all of the release publishing actions now that we have moved the repo to its new home ([https://github.com/openwallet-foundation/acapy](https://github.com/openwallet-foundation/acapy)). Almost all of the changes in the release are related to the move.

The move triggered some big changes for those with existing ACA-Py deployments resulting from the change in the GitHub organization (from Hyperledger to OWF) and source code name (from `aries_cloudagent` to `acapy_agent`). See the [Release 1.1.0 breaking changes](#110-breaking-changes) for the details.

For up to date details on what the repo move means for ACA-Py users, including steps for updating deployments, please follow the updates in [GitHub Issue #3250]. We'll keep you informed about the approach, timeline, and progress of the move. Stay tuned!

### 1.1.0 Deprecation Notices

The same **[deprecation notices](#101-deprecation-notices)** from the [1.0.1](#101) release about AIP 1.0 protocols still apply. The protocols remain in the 1.1.0 release, but will be moved out of the core and into plugins soon. Please review these notifications carefully!

### 1.1.0 Breaking Changes

The only (but significant) breaking changes in 1.1.0 are related to the GitHub organization and project name changes. Specific impacts are:

- the renaming of the source code folder from `aries_cloudagent` to `acapy_agent`,
- the publication of the [PyPi] project under the new `acapy_agent` name, and
- the use of the OWF organizational GitHub Container Registry ([GHCR]) and `acapy_agent` as the name for release container image artifacts.
  - The patterns for the image tags remain the same as before. So, for example, the new nightly artifact can be found here: `docker pull ghcr.io/openwallet-foundation/acapy-agent:py3.12-nightly`.

[GHCR]: https://ghcr.io

Anyone deploying ACA-Py should use this release to update their existing deployments. Since there are no other changes to ACA-Py, any issues found should relate back to those changes.

- Deployments referencing the [PyPi] project (including those in custom plugins) **MUST** update their deployments to use the new name.
- Deployments sourcing the ACA-Py published container image artifacts to [GHCR] must update their deployments to use the new URLs.

Please note that if and when the current LTS releases (0.11 and 0.12) have new releases, they will continue to use the `aries_cloudagent` source folder, the existing locations for the [PyPi] and [GHCR] container image artifacts.

#### 1.1.0 Categorized List of Pull Requests

- Updates related to the move and rename of the repository from the Hyperledger to [OpenWallet Foundation] GitHub organization
  - Change pypi upload workflow to use pypa/gh-action-pypi-publish [\#3291](https://github.com/openwallet-foundation/acapy/pull/3291) [jamshale](https://github.com/jamshale)
  - Update interop fork location after AATH update [\#3282](https://github.com/openwallet-foundation/acapy/pull/3282) [jamshale](https://github.com/jamshale)
  - Fix interop test fork location replacement [\#3280](https://github.com/openwallet-foundation/acapy/pull/3280) [jamshale](https://github.com/jamshale)
  - Update MDs and release publishing files to reflect the repo move to OWF [\#3270](https://github.com/openwallet-foundation/acapy/pull/3270) [swcurran](https://github.com/swcurran)
  - General repo updates post OWF move. [\#3267](https://github.com/openwallet-foundation/acapy/pull/3267) [jamshale](https://github.com/jamshale)

- Release management pull requests:
  - 1.1.0 [\#3294](https://github.com/openwallet-foundation/acapy/pull/3292) [swcurran](https://github.com/swcurran)
  - 1.1.0rc1 [\#3292](https://github.com/openwallet-foundation/acapy/pull/3292) [swcurran](https://github.com/swcurran)
  - 1.1.0rc0 [\#3284](https://github.com/openwallet-foundation/acapy/pull/3284) [swcurran](https://github.com/swcurran)

- Dependabot PRs
  - [Link to list of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A2024-10-08..2024-10-15+author%3Aapp%2Fdependabot+)

## 1.0.1

### October 8, 2024

Release 1.0.1 will be the last release of ACA-Py from the Hyperledger organization before the repository moves to the [OpenWallet Foundation] (OWF). Soon after this release, the ACA-Py project and this repository will move to the OWF's GitHub organization as the [new "acapy" project](https://github.com/openwallet-foundation/project-proposals/blob/main/projects/aca-py.md).

[OpenWallet Foundation]: https://openwallet.foundation/

For details on what this means for ACA-Py users, including steps for updating deployments, please follow the updates in [GitHub Issue #3250]. We'll keep you informed about the approach, timeline, and progress of the move. Stay tuned!

[GitHub Issue #3250]: https://github.com/hyperledger/aries-cloudagent-python/issues/3250

The 1.0.1 release contains mostly internal clean ups, technical debt elimination, and a revision to the integration testing approach, incorporating the [Aries Agent Test Harness] tests in the ACA-Py continuous integration testing process. There are substantial enhancements in the management of keys and their use with [VC-DI] proofs, and web-based DID methods like `did:web`. See the `Wallet and Key Handling` updates in the categorized PR list below.

[Aries Agent Test Harness]: https://github.com/hyperledger/aries-agent-test-harness
[VC-DI]: https://www.w3.org/TR/vc-data-integrity/

There are several important **[deprecation notices](#101-deprecation-notices)** in this release in preparation for the next ACA-Py release. Please review these notifications carefully!

In an attempt to shorten the categorized list of PRs in the release, rather than listing all of the `dependabot` PRs in the release, we've included a link to a list of those PRs.

#### 1.0.1 Deprecation Notices

- ACA-Py will soon be moved from the Hyperledger GitHub organization to that of the [OpenWallet Foundation]. As such, there will be changes in the names and locations of the artifacts produced -- the [PyPi] project and the container images in the [GitHub Container Registry]. We will retain the ability to publish LTS releases of ACA-Py for the current LTS versions (0.11, 0.12) in the current locations. For details, guidance, timing, and progress on the move, please monitor the description of [GitHub Issue #3250] that will be maintained throughout the process.

[PyPi]: https://pypi.org
[GitHub Container Registry]: https://ghcr.io

- In the next ACA-Py release, we will be dropping from the core ACA-Py repository the AIP 1.0 [RFC 0160 Connections], [RFC 0037 Issue Credentials v1.0] and [RFC 0037 Present Proof v1.0] DIDComm protocols. Each of the protocols will be moved to the [ACA-Py Plugins] repo. All deployers that use those protocols **SHOULD** update to the [AIP 2.0] versions of those protocols ([RFC 0434 Out of Band]+[RFC 0023 DID Exchange], [RFC 0453 Issue Credential v2.0] and [RFC 0454 Present Proof v2.0], respectively). Once the protocols are removed from ACA-Py, anyone still using those protocols **MUST** adjust their configuration to load those protocols from the respective plugins.

### 1.0.1 Breaking Changes

There are no breaking changes in ACA-Py Release 1.0.1.

#### 1.0.1 Categorized List of Pull Requests

- Wallet and Key Handling Updates
  - Data integrity routes [\#3261](https://github.com/hyperledger/aries-cloudagent-python/pull/3261) [PatStLouis](https://github.com/PatStLouis)
  - [BUG] Handle get key operation when no tag has been set [\#3256](https://github.com/hyperledger/aries-cloudagent-python/pull/3256) [PatStLouis](https://github.com/PatStLouis)
  - Feature multikey management [\#3246](https://github.com/hyperledger/aries-cloudagent-python/pull/3246) [PatStLouis](https://github.com/PatStLouis)
  - chore: delete unused keypair storage manager [\#3245](https://github.com/hyperledger/aries-cloudagent-python/pull/3245) [dbluhm](https://github.com/dbluhm)

- Credential Exchange Updates
  - feat: verify creds signed with Ed25519VerificationKey2020 [\#3244](https://github.com/hyperledger/aries-cloudagent-python/pull/3244) [dbluhm](https://github.com/dbluhm)
  - Add anoncreds profile basic scenario test [\#3232](https://github.com/hyperledger/aries-cloudagent-python/pull/3232) [jamshale](https://github.com/jamshale)
  - fix: anoncreds revocation notification when revoking [\#3226](https://github.com/hyperledger/aries-cloudagent-python/pull/3226) [thiagoromanos](https://github.com/thiagoromanos)

- OpenAPI Updates
  - :art: fix type hints for optional method parameters [\#3234](https://github.com/hyperledger/aries-cloudagent-python/pull/3234) [ff137](https://github.com/ff137)

- Documentation and GHA Test Updates
  - Prevent integration tests on forks [\#3276](https://github.com/hyperledger/aries-cloudagent-python/pull/3276) [jamshale](https://github.com/jamshale)
  - :memo Fix typos in PUBLISHING.md [\#3274](https://github.com/hyperledger/aries-cloudagent-python/pull/3274) [claudiotorrens](https://github.com/claudiotorrens)
  - Fix scenario tests [\#3231](https://github.com/hyperledger/aries-cloudagent-python/pull/3231) [jamshale](https://github.com/jamshale)
  - Only run integration tests on correct file changes [\#3230](https://github.com/hyperledger/aries-cloudagent-python/pull/3230) [jamshale](https://github.com/jamshale)
  - Update docs for outstanding anoncreds work [\#3229](https://github.com/hyperledger/aries-cloudagent-python/pull/3229) [jamshale](https://github.com/jamshale)
  - Only change interop testing fork on pull requests [\#3218](https://github.com/hyperledger/aries-cloudagent-python/pull/3218) [jamshale](https://github.com/jamshale)
  - Remove the RC from the versions table [\#3213](https://github.com/hyperledger/aries-cloudagent-python/pull/3213) [swcurran](https://github.com/swcurran)
  - Document the documentation site generation process [\#3212](https://github.com/hyperledger/aries-cloudagent-python/pull/3212) [swcurran](https://github.com/swcurran)
  - Remove 1.0.0rc6 documentation from gh-pages [\#3211](https://github.com/hyperledger/aries-cloudagent-python/pull/3211) [swcurran](https://github.com/swcurran)  - Adjust nightly and release workflows [\#3210](https://github.com/hyperledger/aries-cloudagent-python/pull/3210) [jamshale](https://github.com/jamshale)
  - Change interop tests to critical on PRs [\#3209](https://github.com/hyperledger/aries-cloudagent-python/pull/3209) [jamshale](https://github.com/jamshale)
  - Change integration testing [\#3194](https://github.com/hyperledger/aries-cloudagent-python/pull/3194) [jamshale](https://github.com/jamshale)

- Dependencies and Internal Fixes/Updates:
  - Adjust sonarcloud and integration test workflows [\#3259](https://github.com/hyperledger/aries-cloudagent-python/pull/3259) [jamshale](https://github.com/jamshale)
  - fix: enable refreshing did endpoint using mediator info [\#3260](https://github.com/hyperledger/aries-cloudagent-python/pull/3260) [dbluhm](https://github.com/dbluhm)
  - Removing padding from url invitations [\#3238](https://github.com/hyperledger/aries-cloudagent-python/pull/3238) [jamshale](https://github.com/jamshale)
  - Ensure that DAP_PORT is always an int [\#3241](https://github.com/hyperledger/aries-cloudagent-python/pull/3241) [Gavinok](https://github.com/Gavinok)
  - Fix logic to send verbose webhooks [\#3193](https://github.com/hyperledger/aries-cloudagent-python/pull/3193) [ianco](https://github.com/ianco)
  - fixes #3186: handler_timed_file_handler [\#3187](https://github.com/hyperledger/aries-cloudagent-python/pull/3187) [rngadam](https://github.com/rngadam)
  - issue #3182: replace deprecated ptvsd debugger by debugpy [\#3183](https://github.com/hyperledger/aries-cloudagent-python/pull/3183) [rngadam](https://github.com/rngadam)
  - 👷Publish `aries-cloudagent-bbs`  Docker image [\#3175](https://github.com/hyperledger/aries-cloudagent-python/pull/3175) [rblaine95](https://github.com/rblaine95)
  - [ POST v1.0.0 ] Adjust message queue error handling [\#3170](https://github.com/hyperledger/aries-cloudagent-python/pull/3170) [jamshale](https://github.com/jamshale)

- Release management pull requests:
  - 1.0.1 [\#3278](https://github.com/hyperledger/aries-cloudagent-python/pull/3278) [swcurran](https://github.com/swcurran)
  - 1.0.1rc1 [\#3268](https://github.com/hyperledger/aries-cloudagent-python/pull/3268) [swcurran](https://github.com/swcurran)
  - 1.0.1rc0 [\#3254](https://github.com/hyperledger/aries-cloudagent-python/pull/3254) [swcurran](https://github.com/swcurran)

- Dependabot PRs
  - [Link to list of Dependabot PRs in this release](https://github.com/hyperledger/aries-cloudagent-python/pulls?q=is%3Apr+is%3Amerged+merged%3A2024-08-15..2024-10-08+author%3Aapp%2Fdependabot+)

## 1.0.0

### August 16, 2024

Release 1.0.0 is finally here! While Aries Cloud Agent Python has been used in production for several years, the maintainers have decided it is finally time to put a "1.0" tag on the project. The 1.0.0 release itself includes well over 100 PRs merged since [Release 0.12.1](#0121). The vast majority of that work was in hardening the product in preparation for this 1.0.0 release. While there are a number of new features and a new Long Term Support (LTS) policy, the majority of the focus has been on eliminating technical debt and improving the underlying implementation. The full list of PRs in this release can be [found below](#100-categorized-list-of-pull-requests). here are the highlights of the release:

- A formal ACA-Py Long Term Support (LTS) policy has been documented and is being followed.
- The default underlying Python version has been upgraded to 3.12. Happily, there were minimal code changes to enable the upgrade to 3.12 from the previous Python 3.9.
- A new ACA-Py Plugins Store at [https://plugins.aca-py.org](https://plugins.aca-py.org). Check out the plugins that have been published by ACA-Py contributors, and learn how to add your own plugins!
- We've improved the developer experience by enabling support in ACA-Py artifacts for the ARM Architecture (and notably, Mac M1 and later systems). To do so, we have removed *default* support for BBS Signatures. BBS Signatures are still supported in the codebase, and guidance is provided for how to enable the support in artifacts (Docker images, etc.) for those needing it. We look forward to updating the BBS support in ACA-Py based on libraries that include multi-architecture support.
- Pagination support has been added to a number of Admin API queries for object lists, enabling the development of better user interfaces for large deployments.
- Cleanup in the ACA-Py AnonCreds Revocation Registry handling to prevent errors that were found occurring under certain specific conditions.
- Upgraded pull request and release pipeline, including:
  - Enabling a much more aggressive approach to dependabot notifications, beyond just those for security vulnerabilities. Along with those upgrades, we've moved to newer/better build pipeline tooling, such as switching from Black to Ruff, and re-enable per pull request code coverage notifications.
    - Many of the PRs in this release are related to dependency updates from dependabot or applied directly.
  - A switch to more used tooling, such as a switch from black to ruff.
  - Improvements in coverage monitoring of pull requests.
- The start of a [DIDComm v2](https://identity.foundation/didcomm-messaging/spec/) implementation in ACA-Py. The work is not complete, as we are taking an incremental approach to adding DIDComm v2 support.
- A decorator has been added for enabling direct support for Admin API authentication. Previously, the only option to enable (the necessary) Admin API was to put the API behind a proxy that could manage authentication. With this update, ACA-Py deployments can handle authentication directly, without a proxy.
- We have dropped support for the old, archived [Indy SDK]. If you have not migrated your deployment off of the Indy SDK, you must do so now. See this [Indy SDK to Askar migration documentation](#https://aca-py.org/latest/deploying/IndySDKtoAskarMigration/) for guidance.
- Support added for using AnonCreds in [W3C VCDM](https://www.w3.org/TR/vc-data-model-1.1/) format.

### 1.0.0 Breaking Changes

With the focus of the pull requests for this release on stabilizing the implementation, there were a few breaking changes:

- The default underlying Python version has been upgraded to 3.12.
- ACA-Py has supported BBS Signatures for some time. However, the dependency that is used (`bbs`) does not support the ARM architecture, and its inclusion in the default ACA-Py artifacts mean that developers using ARM-based hardware (such as Apple M1 Macs or later) cannot run ACA-Py "out-of-the-box". We feel that providing a better developer experience by supporting the ARM architecture is more important than BBS Signature support at this time. As such, we have removed the BBS dependency from the base ACA-Py artifacts and made it an add-on that those using ACA-Py with BBS must take extra steps to build into their own artifacts, as documented [here](https://aca-py.org/latest/deploying/BBSSignatures/).
- Support for the Indy SDK has been dropped. It had been previously deprecated. See this [Indy SDK to Askar migration documentation](https://aca-py.org/latest/deploying/IndySDKtoAskarMigration/) for guidance. [Hyperledger Indy](https://www.hyperledger.org/projects/hyperledger-indy) is still fully supported - it's just the Indy SDK client-side library that has been removed.
- The webhook sent after receipt of presentation by a verifier has been updated to include all of the information needed by the verifier so that the controller does not have to call the "Verify Presentation" endpoint. The issue with calling that endpoint after the presentation has been received is that there is a race condition between the controller and the ACA-Py cleanup process deleting completed Present Proof protocol instances. See [\#3081](https://github.com/hyperledger/aries-cloudagent-python/pull/3081) for additional details.
- A fix to an obscure bug includes a change to the data sent to the controller after publishing multiple, endorsed credential definition revocation registries in a single call. The bug fix was to properly process the publishing. The breaking change is that when the process (now successfully) completes, the controller is sent the list of published credential definitions. Previously only a single value was being sent. See PR [\#3107](https://github.com/hyperledger/aries-cloudagent-python/pull/3107) for additional details.
- The configuration settings around whether a multitenant wallet uses a single database vs. a database per tenant has been made more explicit. The previous settings were not clear, resulting in some deployments that were intended to be a database per tenant actually result in all tenants being in the same database. For details about the change, see [\#3105](https://github.com/hyperledger/aries-cloudagent-python/pull/3105).
 
#### 1.0.0 Categorized List of Pull Requests

- LTS Support Policy:
  - LTS Strategy and Scanner GHA [\#3143](https://github.com/hyperledger/aries-cloudagent-python/pull/3143) [swcurran](https://github.com/swcurran)

- DIDComm and Connection Establishment updates/fixes:
  - fix: multiuse invites with did peer 4 [\#3112](https://github.com/hyperledger/aries-cloudagent-python/pull/3112) [dbluhm](https://github.com/dbluhm)
  - Check connection is ready in all connection required handlers [\#3095](https://github.com/hyperledger/aries-cloudagent-python/pull/3095) [jamshale](https://github.com/jamshale)
  - fix: didexchange manager not checking the did-rotate content correctly [\#3057](https://github.com/hyperledger/aries-cloudagent-python/pull/3057) [gmulhearn-anonyome](https://github.com/gmulhearn-anonyome)
  - fix: respond to did:peer:1 with did:peer:4 [\#3050](https://github.com/hyperledger/aries-cloudagent-python/pull/3050) [dbluhm](https://github.com/dbluhm)
  - DIDComm V2 Initial Implementation [\#2959](https://github.com/hyperledger/aries-cloudagent-python/pull/2959) [TheTechmage](https://github.com/TheTechmage)
  - Feature: use decorators for admin api authentication [\#2860](https://github.com/hyperledger/aries-cloudagent-python/pull/2860) [esune](https://github.com/esune)

- Admin API, Startup, OpenAPI/Swagger Updates and Improvements:
  - Add rekey feature with blank key support [\#3125](https://github.com/hyperledger/aries-cloudagent-python/pull/3125) [jamshale](https://github.com/jamshale)
  - BREAKING: Make single wallet config more explicit [\#3105](https://github.com/hyperledger/aries-cloudagent-python/pull/3105) [jamshale](https://github.com/jamshale)
  - 🐛 fix IndyAttrValue bad reference in OpenAPI spec [\#3090](https://github.com/hyperledger/aries-cloudagent-python/pull/3090) [ff137](https://github.com/ff137)
  - 🎨 improve record querying logic [\#3083](https://github.com/hyperledger/aries-cloudagent-python/pull/3083) [ff137](https://github.com/ff137)
  - 🐛 fix storage record pagination with post-filter query params [\#3082](https://github.com/hyperledger/aries-cloudagent-python/pull/3082) [ff137](https://github.com/ff137)
  - ✨ Add pagination support for listing Connection, Cred Ex, and Pres Ex records [\#3033](https://github.com/hyperledger/aries-cloudagent-python/pull/3033) [ff137](https://github.com/ff137)
  - ✨ Adds support for paginated storage queries, and implements pagination for the wallets_list endpoint [\#3000](https://github.com/hyperledger/aries-cloudagent-python/pull/3000) [ff137](https://github.com/ff137)
  - Enable no-transport mode as startup parameter [\#2990](https://github.com/hyperledger/aries-cloudagent-python/pull/2990) [PatStLouis](https://github.com/PatStLouis)

- Test and Demo updates:
  - Postgres Demo - Upgrade postgres and change entrypoint file [\#3004](https://github.com/hyperledger/aries-cloudagent-python/pull/3004) [jamshale](https://github.com/jamshale)
  - Example integration test issuing 2 credentials under the same schema [\#2948](https://github.com/hyperledger/aries-cloudagent-python/pull/2948) [ianco](https://github.com/ianco)

- Credential Exchange updates and fixes:
  - Update TxnOrPublishRevocationsResultSchema [\#3164](https://github.com/hyperledger/aries-cloudagent-python/pull/3164) [cl0ete](https://github.com/cl0ete)
  - For proof problem handler [\#3068](https://github.com/hyperledger/aries-cloudagent-python/pull/3068) [loneil](https://github.com/loneil)
  - Breaking: Fix publishing multiple rev reg defs with endorsement [\#3107](https://github.com/hyperledger/aries-cloudagent-python/pull/3107) [jamshale](https://github.com/jamshale)
  - Fix the check for vc_di proof [\#3106](https://github.com/hyperledger/aries-cloudagent-python/pull/3106) [ianco](https://github.com/ianco)
  - Add DIF presentation exchange context and cache document [\#3093](https://github.com/hyperledger/aries-cloudagent-python/pull/3093) [gmulhearn](https://github.com/gmulhearn)
  - Add by_format to terse webhook for presentations [\#3081](https://github.com/hyperledger/aries-cloudagent-python/pull/3081) [ianco](https://github.com/ianco)
  - Use anoncreds registry for holder credential endpoints [\#3063](https://github.com/hyperledger/aries-cloudagent-python/pull/3063) [jamshale](https://github.com/jamshale)
  - For proof problem handler, allow no connection record (OOB cases), prevent unhandled exception [\#3068](https://github.com/hyperledger/aries-cloudagent-python/pull/3068) [loneil](https://github.com/loneil)
  - Handle failed tails server issuance [Anoncreds] [\#3049](https://github.com/hyperledger/aries-cloudagent-python/pull/3049) [jamshale](https://github.com/jamshale)
  - Prevent getting stuck with no active registry [\#3032](https://github.com/hyperledger/aries-cloudagent-python/pull/3032) [jamshale](https://github.com/jamshale)
  - Fix and refactor anoncreds revocation recovery [\#3029](https://github.com/hyperledger/aries-cloudagent-python/pull/3029) [jamshale](https://github.com/jamshale)
  - Fix issue with requested to revoke before registry creation [\#2995](https://github.com/hyperledger/aries-cloudagent-python/pull/2995) [jamshale](https://github.com/jamshale)
  - Add support for revocable credentials in vc_di handler [\#2967](https://github.com/hyperledger/aries-cloudagent-python/pull/2967) [EmadAnwer](https://github.com/EmadAnwer)
  - Fix clear revocation logic [\#2956](https://github.com/hyperledger/aries-cloudagent-python/pull/2956) [jamshale](https://github.com/jamshale)
  - Anoncreds - Send full registry list when getting revocation states [\#2946](https://github.com/hyperledger/aries-cloudagent-python/pull/2946) [jamshale](https://github.com/jamshale)
  - Add missing VC-DI/LD-Proof verification method option [\#2867](https://github.com/hyperledger/aries-cloudagent-python/pull/2867) [PatStLouis](https://github.com/PatStLouis)
  - feat: Integrate AnonCreds with W3C VCDI Format Support in ACA-Py [\#2861](https://github.com/hyperledger/aries-cloudagent-python/pull/2861) [sarthakvijayvergiya](https://github.com/sarthakvijayvergiya)
  - Correct the response type in send_rev_reg_def [\#2355](https://github.com/hyperledger/aries-cloudagent-python/pull/2355) [ff137](https://github.com/ff137)

- Upgrade Updates and Improvements:
  - 👷 Enable linux/arm64 docker builds [\#3171](https://github.com/hyperledger/aries-cloudagent-python/pull/3171) [rblaine95](https://github.com/rblaine95)
  - BREAKING: Enable ARM-based ACA-Py artifacts by default by removing BBS+ Signatures as a default inclusion [\#3127](https://github.com/hyperledger/aries-cloudagent-python/pull/3127) [amanji](https://github.com/amanji)
  - Re-enable ledger plugin when --no-legder is set [\#3070](https://github.com/hyperledger/aries-cloudagent-python/pull/3070) [PatStLouis](https://github.com/PatStLouis)
  - Upgrade to anoncreds via api endpoint [\#2922](https://github.com/hyperledger/aries-cloudagent-python/pull/2922) [jamshale](https://github.com/jamshale)
  - 🐛 fix wallet_update when only extra_settings requested [\#2612](https://github.com/hyperledger/aries-cloudagent-python/pull/2612) [ff137](https://github.com/ff137)

- Release management pull requests:
  - 1.0.0 [\#3172](https://github.com/hyperledger/aries-cloudagent-python/pull/3172) [swcurran](https://github.com/swcurran)
  - 1.0.0rc6 [\#3147](https://github.com/hyperledger/aries-cloudagent-python/pull/3147) [swcurran](https://github.com/swcurran)
  - 1.0.0rc5 [\#3118](https://github.com/hyperledger/aries-cloudagent-python/pull/3118) [swcurran](https://github.com/swcurran)
  - 1.0.0rc4 [\#3092](https://github.com/hyperledger/aries-cloudagent-python/pull/3092) [swcurran](https://github.com/swcurran)

- Documentation, code formatting, publishing process updates:
  - 🎨 organize imports [\#3169](https://github.com/hyperledger/aries-cloudagent-python/pull/3169) [ff137](https://github.com/ff137)
  - 👷 fix lint workflow and 🎨 apply ruff linting [\#3166](https://github.com/hyperledger/aries-cloudagent-python/pull/3166) [ff137](https://github.com/ff137)
  - Fix typo credetial, uste [\#3146](https://github.com/hyperledger/aries-cloudagent-python/pull/3146) [rngadam](https://github.com/rngadam)
  - Fix links to AliceGetsAPhone.md from abs to rel and blob refs [\#3128](https://github.com/hyperledger/aries-cloudagent-python/pull/3128) [rngadam](https://github.com/rngadam)
  - DOC: Verifiable Credential Data Integrity (VC-DI) Credentials in Aries Cloud Agent Python (ACA-Py) #2947 [\#3110](https://github.com/hyperledger/aries-cloudagent-python/pull/3110) [kenechukwu-orjiene](https://github.com/kenechukwu-orjiene)
  - demo/ACA-Py-Workshop.md tweak for Traction Sandbox update [\#3136](https://github.com/hyperledger/aries-cloudagent-python/pull/3136) [loneil](https://github.com/loneil)
  - Adds documentation site docs for releases 0.11.0 [\#3133](https://github.com/hyperledger/aries-cloudagent-python/pull/3133) [swcurran](https://github.com/swcurran)
  - Add descriptive error for issuance without RevRegRecord [\#3109](https://github.com/hyperledger/aries-cloudagent-python/pull/3109) [jamshale](https://github.com/jamshale)
  - Switch from black to ruff [\#3080](https://github.com/hyperledger/aries-cloudagent-python/pull/3080) [jamshale](https://github.com/jamshale)
  - fix: print provision messages when auto-provision is triggered [\#3077](https://github.com/hyperledger/aries-cloudagent-python/pull/3077) [TheTechmage](https://github.com/TheTechmage)
  - Rule D417 [\#3072](https://github.com/hyperledger/aries-cloudagent-python/pull/3072) [jamshale](https://github.com/jamshale)
  - Fix - only run integration tests on opened PR's [\#3042](https://github.com/hyperledger/aries-cloudagent-python/pull/3042) [jamshale](https://github.com/jamshale)
  - docs: added section on environment variables [\#3028](https://github.com/hyperledger/aries-cloudagent-python/pull/3028) [Executioner1939](https://github.com/Executioner1939)
  - Fix deprecation warnings [\#2756](https://github.com/hyperledger/aries-cloudagent-python/pull/2756) [ff137](https://github.com/ff137)
  - 🎨 clarify LedgerError message when TAA is required and not accepted [\#2545](https://github.com/hyperledger/aries-cloudagent-python/pull/2545) [ff137](https://github.com/ff137)
  - Chore: fix marshmallow warnings [\#2398](https://github.com/hyperledger/aries-cloudagent-python/pull/2398) [ff137](https://github.com/ff137)
  - Fix formatting and grammatical errors in different readme's [\#2222](https://github.com/hyperledger/aries-cloudagent-python/pull/2222) [ff137](https://github.com/ff137)
  - Fix broken link in README [\#2221](https://github.com/hyperledger/aries-cloudagent-python/pull/2221) [ff137](https://github.com/ff137)
  - Manage integration tests with GitHub Actions (#2952) [\#2996](https://github.com/hyperledger/aries-cloudagent-python/pull/2996) [jamshale](https://github.com/jamshale)
  - Update README.md [\#2927](https://github.com/hyperledger/aries-cloudagent-python/pull/2927) [KPCOFGS](https://github.com/KPCOFGS)
  - Add anoncreds migration guide [\#2881](https://github.com/hyperledger/aries-cloudagent-python/pull/2881) [jamshale](https://github.com/jamshale)
  - Fix formatting and grammatical errors in different readme's [\#2222](https://github.com/hyperledger/aries-cloudagent-python/pull/2222) [ff137](https://github.com/ff137)
  - Fix broken link in README [\#2221](https://github.com/hyperledger/aries-cloudagent-python/pull/2221) [ff137](https://github.com/ff137)

- Dependencies and Internal Updates:
  - Add explicit write permission to publish workflow [\#3167](https://github.com/hyperledger/aries-cloudagent-python/pull/3167) [jamshale](https://github.com/jamshale)
  - Upgrade python to version 3.12 [\#3067](https://github.com/hyperledger/aries-cloudagent-python/pull/3067) [jamshale](https://github.com/jamshale)
  - Use a published version of aiohttp-apispec [\#3019](https://github.com/hyperledger/aries-cloudagent-python/pull/3019) [jamshale](https://github.com/jamshale)
  - Add sonarcloud badges [\#3014](https://github.com/hyperledger/aries-cloudagent-python/pull/3014) [jamshale](https://github.com/jamshale)
  - Switch from pytz to dateutil [\#3012](https://github.com/hyperledger/aries-cloudagent-python/pull/3012) [jamshale](https://github.com/jamshale)
  - feat: soft binding for plugin flexibility [\#3010](https://github.com/hyperledger/aries-cloudagent-python/pull/3010) [dbluhm](https://github.com/dbluhm)
  - feat: inject profile and session [\#2997](https://github.com/hyperledger/aries-cloudagent-python/pull/2997) [dbluhm](https://github.com/dbluhm)
  - ✨ Faster uuid generation [\#2994](https://github.com/hyperledger/aries-cloudagent-python/pull/2994) [ff137](https://github.com/ff137)
  - Sonarcloud with code coverage [\#2968](https://github.com/hyperledger/aries-cloudagent-python/pull/2968) [jamshale](https://github.com/jamshale)
  - Fix Snyk sarif file [\#2961](https://github.com/hyperledger/aries-cloudagent-python/pull/2961) [pradeepp88](https://github.com/pradeepp88)
  - Add OpenSSF Scorecard GHA - weekly [\#2955](https://github.com/hyperledger/aries-cloudagent-python/pull/2955) [swcurran](https://github.com/swcurran)
  - Fix Snyk Container scanning workflow [\#2951](https://github.com/hyperledger/aries-cloudagent-python/pull/2951) [WadeBarnes](https://github.com/WadeBarnes)
  - chore: updating dependabot to support gha, python, docker and dev container packages [\#2945](https://github.com/hyperledger/aries-cloudagent-python/pull/2945) [rajpalc7](https://github.com/rajpalc7)
  - fix(interop): overly strict validation [\#2943](https://github.com/hyperledger/aries-cloudagent-python/pull/2943) [dbluhm](https://github.com/dbluhm)
  - ⬆️ Upgrade test and lint dependencies [\#2939](https://github.com/hyperledger/aries-cloudagent-python/pull/2939) [ff137](https://github.com/ff137)
  - ⬆️ Upgrade aiohttp-apispec [\#2920](https://github.com/hyperledger/aries-cloudagent-python/pull/2920) [ff137](https://github.com/ff137)
  - ⬆️ Upgrade pydid (pydantic v2) [\#2919](https://github.com/hyperledger/aries-cloudagent-python/pull/2919) [ff137](https://github.com/ff137)
  - BREAKING feat: drop indy sdk [\#2892](https://github.com/hyperledger/aries-cloudagent-python/pull/2892) [dbluhm](https://github.com/dbluhm)
  - Change middleware registration order [\#2796](https://github.com/hyperledger/aries-cloudagent-python/pull/2796) [PatStLouis](https://github.com/PatStLouis)
  - ⬆️ Upgrade pytest to 8.0 [\#2773](https://github.com/hyperledger/aries-cloudagent-python/pull/2773) [ff137](https://github.com/ff137)
  - ⬆️ Update pytest-asyncio to 0.23.4 [\#2764](https://github.com/hyperledger/aries-cloudagent-python/pull/2764) [ff137](https://github.com/ff137)
  - Upgrade pre-commit and flake8 dependencies; fix flake8 warnings [\#2399](https://github.com/hyperledger/aries-cloudagent-python/pull/2399) [ff137](https://github.com/ff137)
  - ⬆️ upgrade requests to latest [\#2336](https://github.com/hyperledger/aries-cloudagent-python/pull/2336) [ff137](https://github.com/ff137)
  - ⬆️ upgrade pyjwt to latest; introduce leeway to jwt.decode [\#2335](https://github.com/hyperledger/aries-cloudagent-python/pull/2335) [ff137](https://github.com/ff137)
  - ⬆️ upgrade packaging to latest [\#2334](https://github.com/hyperledger/aries-cloudagent-python/pull/2334) [ff137](https://github.com/ff137)
  - ⬆️ upgrade marshmallow to latest [\#2322](https://github.com/hyperledger/aries-cloudagent-python/pull/2322) [ff137](https://github.com/ff137)
  - Upgrade codegen tools in scripts/generate-open-api-spec and publish Swagger 2.0 and OpenAPI 3.0 specs [\#2246](https://github.com/hyperledger/aries-cloudagent-python/pull/2246) [ff137](https://github.com/ff137)

- Dependabot PRs:
  - chore(deps): Bump ossf/scorecard-action from 2.3.3 to 2.4.0 in the all-actions group [\#3134](https://github.com/hyperledger/aries-cloudagent-python/pull/3134) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pre-commit from 3.7.1 to 3.8.0 [\#3129](https://github.com/hyperledger/aries-cloudagent-python/pull/3129) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump ruff from 0.5.4 to 0.5.5 [\#3131](https://github.com/hyperledger/aries-cloudagent-python/pull/3131) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump mkdocs-material from 9.5.29 to 9.5.30 [\#3130](https://github.com/hyperledger/aries-cloudagent-python/pull/3130) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pytest from 8.3.1 to 8.3.2 [\#3132](https://github.com/hyperledger/aries-cloudagent-python/pull/3132) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump ruff from 0.5.2 to 0.5.4 [\#3114](https://github.com/hyperledger/aries-cloudagent-python/pull/3114) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump pytest-asyncio from 0.23.7 to 0.23.8 in /demo/playground/examples [\#3117](https://github.com/hyperledger/aries-cloudagent-python/pull/3117) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pytest-ruff from 0.4.0 to 0.4.1 [\#3113](https://github.com/hyperledger/aries-cloudagent-python/pull/3113) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pytest from 8.2.2 to 8.3.1 [\#3115](https://github.com/hyperledger/aries-cloudagent-python/pull/3115) [dependabot bot](https://github.com/dependabot bot)
  - Library update 15/07/24 / Fix unit test typing [\#3103](https://github.com/hyperledger/aries-cloudagent-python/pull/3103) [jamshale](https://github.com/jamshale)
  - chore(deps): Bump certifi from 2024.6.2 to 2024.7.4 in /demo/playground/examples in the pip group [\#3084](https://github.com/hyperledger/aries-cloudagent-python/pull/3084) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump aries-askar from 0.3.1 to 0.3.2 [\#3088](https://github.com/hyperledger/aries-cloudagent-python/pull/3088) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump ruff from 0.5.0 to 0.5.1 [\#3087](https://github.com/hyperledger/aries-cloudagent-python/pull/3087) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump mkdocs-material from 9.5.27 to 9.5.28 [\#3089](https://github.com/hyperledger/aries-cloudagent-python/pull/3089) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump certifi from 2024.6.2 to 2024.7.4 in the pip group [\#3085](https://github.com/hyperledger/aries-cloudagent-python/pull/3085) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump requests from 2.32.2 to 2.32.3 [\#3076](https://github.com/hyperledger/aries-cloudagent-python/pull/3076) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump uuid-utils from 0.8.0 to 0.9.0 [\#3075](https://github.com/hyperledger/aries-cloudagent-python/pull/3075) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump mike from 2.0.0 to 2.1.2 [\#3074](https://github.com/hyperledger/aries-cloudagent-python/pull/3074) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump ruff from 0.4.10 to 0.5.0 [\#3073](https://github.com/hyperledger/aries-cloudagent-python/pull/3073) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump dawidd6/action-download-artifact from 5 to 6 in the all-actions group [\#3064](https://github.com/hyperledger/aries-cloudagent-python/pull/3064) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump markupsafe from 2.0.1 to 2.1.5 [\#3062](https://github.com/hyperledger/aries-cloudagent-python/pull/3062) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pydevd-pycharm from 193.6015.41 to 193.7288.30 [\#3060](https://github.com/hyperledger/aries-cloudagent-python/pull/3060) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump ruff from 0.4.4 to 0.4.10 [\#3058](https://github.com/hyperledger/aries-cloudagent-python/pull/3058) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump the pip group with 2 updates [\#3046](https://github.com/hyperledger/aries-cloudagent-python/pull/3046) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump urllib3 from 2.2.1 to 2.2.2 in /demo/playground/examples in the pip group [\#3045](https://github.com/hyperledger/aries-cloudagent-python/pull/3045) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump marshmallow from 3.20.2 to 3.21.3 [\#3038](https://github.com/hyperledger/aries-cloudagent-python/pull/3038) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump packaging from 23.1 to 23.2 [\#3037](https://github.com/hyperledger/aries-cloudagent-python/pull/3037) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump mkdocs-material from 9.5.10 to 9.5.27 [\#3036](https://github.com/hyperledger/aries-cloudagent-python/pull/3036) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump configargparse from 1.5.5 to 1.7 [\#3035](https://github.com/hyperledger/aries-cloudagent-python/pull/3035) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump uuid-utils from 0.7.0 to 0.8.0 [\#3034](https://github.com/hyperledger/aries-cloudagent-python/pull/3034) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump dawidd6/action-download-artifact from 3 to 5 in the all-actions group [\#3027](https://github.com/hyperledger/aries-cloudagent-python/pull/3027) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Update prompt-toolkit requirement from ~=2.0.9 to ~=2.0.10 in /demo [\#3026](https://github.com/hyperledger/aries-cloudagent-python/pull/3026) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps-dev): Bump pytest from 8.2.1 to 8.2.2 [\#3025](https://github.com/hyperledger/aries-cloudagent-python/pull/3025) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump pydid from 0.5.0 to 0.5.1 [\#3024](https://github.com/hyperledger/aries-cloudagent-python/pull/3024) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump sphinx from 1.8.4 to 1.8.6 [\#3021](https://github.com/hyperledger/aries-cloudagent-python/pull/3021) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump actions/checkout from 3 to 4 in the all-actions group [\#3011](https://github.com/hyperledger/aries-cloudagent-python/pull/3011) [dependabot bot](https://github.com/dependabot bot)
  - Merge all demo dependabot PRs [\#3008](https://github.com/hyperledger/aries-cloudagent-python/pull/3008) [PatStLouis](https://github.com/PatStLouis)
  - Merge all poetry dependabot PRs [\#3007](https://github.com/hyperledger/aries-cloudagent-python/pull/3007) [PatStLouis](https://github.com/PatStLouis)
  - chore(deps): Bump hyperledger/aries-cloudagent-python from py3.9-0.9.0 to py3.9-0.12.1 in /demo/multi-demo [\#2976](https://github.com/hyperledger/aries-cloudagent-python/pull/2976) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump hyperledger/aries-cloudagent-python from py3.9-0.10.4 to py3.9-0.12.1 in /demo/playground [\#2975](https://github.com/hyperledger/aries-cloudagent-python/pull/2975) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump hyperledger/aries-cloudagent-python from py3.9-0.9.0 to py3.9-0.12.1 in /demo/docker-agent [\#2973](https://github.com/hyperledger/aries-cloudagent-python/pull/2973) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump sphinx-rtd-theme from 1.1.1 to 1.3.0 in /docs [\#2970](https://github.com/hyperledger/aries-cloudagent-python/pull/2970) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump untergeek/curator from 8.0.2 to 8.0.15 in /demo/elk-stack/extensions/curator [\#2969](https://github.com/hyperledger/aries-cloudagent-python/pull/2969) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump ecdsa from 0.16.1 to 0.19.0 in the pip group across 1 directory [\#2933](https://github.com/hyperledger/aries-cloudagent-python/pull/2933) [dependabot bot](https://github.com/dependabot bot)

## 0.12.6

### March 13, 2025

This patch release addresses a bug in the handling connection reuse in multitenancy environments. This is a backport of the PR [fix: connection reuse with multi-tenancy #3543](https://github.com/openwallet-foundation/acapy/pull/3543). This fixes the issue when using multi-tenancy, calls to `POST /out-of-band/receive-invitation?use_existing_connection=true` failing with a record not found error, despite connection reuse actually being completed in the background.

### 0.12.6 Breaking Changes

There are no breaking changes in this release.

#### 0.12.6 Categorized List of Pull Requests

- Multitenancy Fixes
  - fix: cherry-pick fixes from main to 0.12.lts [\#3578](https://github.com/openwallet-foundation/acapy/pull/3578) [thiagoromanos](https://github.com/thiagoromanos)

- Release management pull requests:
  - 0.12.6 [\#3583](https://github.com/openwallet-foundation/acapy/pull/3583) [swcurran](https://github.com/swcurran)

## 0.12.5

### March 6, 2025

This patch release addresses a bug in the publishing of AnonCreds revocation entries that caused the ledger and issuer wallet to become out of sync. As a result, revoked credentials were not being correctly flagged as revoked when presented. Previously, this issue was mitigated by an automatic “sync-revocation” process, which generally resolved the problem. However, we recently identified scenarios where the presence of an Indy Endorser in the revocation publication flow caused the “sync-revocation” process to fail silently.

This patch resolves that issue. Once applied, if a revocation batch results in an out-of-sync state, the “sync-revocation” process will automatically run to correct it.

For more details, see [Issue 3546](https://github.com/openwallet-foundation/acapy/issues/3546).

### 0.12.5 Breaking Changes

There are no breaking changes in this release.

#### 0.12.5 Categorized List of Pull Requests

- AnonCreds Revocation Fixes
  - 0.12.lts Patch the fix_ledger_entry improvements [\#3558](https://github.com/openwallet-foundation/acapy/pull/3558) [jamshale](https://github.com/jamshale)
  - 0.12.lts Fix revocation accum sync when endorsement txn fails (#3547) [\#3554](https://github.com/openwallet-foundation/acapy/pull/3554) [jamshale](https://github.com/jamshale)

- Release management pull requests:
  - 0.12.5 [\#3560](https://github.com/openwallet-foundation/acapy/pull/3560) [swcurran](https://github.com/swcurran)

## 0.12.4

### January 30, 2025

A patch release to upgrade [Askar](https://github.com/openwallet-foundation/askar) to [0.4.3](https://github.com/openwallet-foundation/askar/releases/tag/v0.4.3) and fixes a problem with wallet names in a multitenant, single-wallet configuration.

Addresses the problem outlined in [#3471](https://github.com/openwallet-foundation/acapy/issues/3471) around profiles in multi-tenant/single wallet deployments. The update to Askar addresses an intermittent hang on startup, and a dependency change that can result in a substantial performance improvement in some cases. See issues: [openwallet-foundation/askar#350](https://github.com/openwallet-foundation/askar/pull/350), [openwallet-foundation/askar#351](https://github.com/openwallet-foundation/askar/pull/351), [openwallet-foundation/askar#354](https://github.com/openwallet-foundation/askar/pull/354). This [comment on one of the PRs](https://github.com/openwallet-foundation/askar/pull/350#issuecomment-2615727109) describes the scenario where a substantial performance improvement was seen as a result of the change in Askar.

### 0.12.4 Breaking Changes

There are no breaking changes in this release.

#### 0.12.4 Categorized List of Pull Requests

- Multitenant Single Wallet Configurations
  - 0.12 LTS: Askar upgrade and fix profile unique names [\#3475](https://github.com/openwallet-foundation/acapy/pull/3475)
- Release management pull requests
  - 0.12.4 [\#3481](https://github.com/hyperledger/aries-cloudagent-python/pull/3481) [swcurran](https://github.com/swcurran)

## 0.12.3

### December 17, 2024

A patch release to add address a bug found in the Linked Data Verifiable Credential handling for multi-tenant holders. The bug was fixed in the main branch, [PR 3391 - BREAKING: VCHolder multitenant binding](https://github.com/openwallet-foundation/acapy/pull/3391), and with this release is backported to 0.12 Long Term Support branch. Prior to this release, holder credentials received into a tenant wallet were actually received into the multi-tenant admin wallet.

### 0.12.3 Breaking Changes

There are no breaking changes in this release.

#### 0.12.3 Categorized List of Pull Requests

- Multitenant LD-VC Holders
  - Patch PR 3391 - 0.12.lts [\#3396](https://github.com/openwallet-foundation/acapy/pull/3396)
- Release management pull requests
  - 0.12.3 [\#3408](https://github.com/hyperledger/aries-cloudagent-python/pull/3408) [swcurran](https://github.com/swcurran)
  - 0.12.3rc0 [\#3406](https://github.com/hyperledger/aries-cloudagent-python/pull/3406) [swcurran](https://github.com/swcurran)

## 0.12.2

### August 2, 2024

A patch release to add the verification of a linkage between an inbound message and its associated connection (if any) before processing the message. Also adds some additional cleanup/fix PRs from the main branch (see list below) that might be useful for deployments currently using [Release 0.12.1](#0121) or [0.12.0](#0120).

### 0.12.2 Breaking Changes

There are no breaking changes in this release.

#### 0.12.2 Categorized List of Pull Requests

- Dependency update and release PR
  - [ PATCH ] 0.12.x with PR 3081 terse webhooks [\#3141](https://github.com/hyperledger/aries-cloudagent-python/pull/3141) [jamshale](https://github.com/jamshale)
  - Patch release 0.12.x [\#3121](https://github.com/hyperledger/aries-cloudagent-python/pull/3121) [jamshale](https://github.com/jamshale)
- Release management pull requests
  - 0.12.2 [\#3145](https://github.com/hyperledger/aries-cloudagent-python/pull/3145) [swcurran](https://github.com/swcurran)
  - 0.12.2rc1 [\#3123](https://github.com/hyperledger/aries-cloudagent-python/pull/3123) [swcurran](https://github.com/swcurran)
- PRs cherry-picked into [\#3121](https://github.com/hyperledger/aries-cloudagent-python/pull/3120) from the `main` branch:
  - fix: multiuse invites with did peer 4 [\#3112](https://github.com/hyperledger/aries-cloudagent-python/pull/3112) [dbluhm](https://github.com/dbluhm)
  - Check connection is ready in all connection required handlers [\#3095](https://github.com/hyperledger/aries-cloudagent-python/pull/3095) [jamshale](https://github.com/jamshale)
  - Add by_format to terse webhook for presentations [\#3081](https://github.com/hyperledger/aries-cloudagent-python/pull/3081) [ianco](https://github.com/ianco)
  - fix: respond to did:peer:1 with did:peer:4 [\#3050](https://github.com/hyperledger/aries-cloudagent-python/pull/3050) [dbluhm](https://github.com/dbluhm)
  - feat: soft binding for plugin flexibility [\#3010](https://github.com/hyperledger/aries-cloudagent-python/pull/3010) [dbluhm](https://github.com/dbluhm)
  - feat: inject profile and session [\#2997](https://github.com/hyperledger/aries-cloudagent-python/pull/2997) [dbluhm](https://github.com/dbluhm)
  - feat: external signature suite provider interface [\#2835](https://github.com/hyperledger/aries-cloudagent-python/pull/2835) [dbluhm](https://github.com/dbluhm)
  - fix(interop): overly strict validation [\#2943](https://github.com/hyperledger/aries-cloudagent-python/pull/2943) [dbluhm](https://github.com/dbluhm)

## 0.12.1

### April 26, 2024

Release 0.12.1 is a small patch to cleanup some edge case issues in the handling of Out of Band invitations, revocation notification webhooks, and connection querying uncovered after the 0.12.0 release. Fixes and improvements were also made to the generation of ACA-Py's OpenAPI specifications.

### 0.12.1 Breaking Changes

There are no breaking changes in this release.

#### 0.12.1 Categorized List of Pull Requests

- Out of Band Invitations and Connection Establishment updates/fixes:
  - 🐛 Fix ServiceDecorator parsing in oob record handling [\#2910](https://github.com/hyperledger/aries-cloudagent-python/pull/2910) [ff137](https://github.com/ff137)
  - fix: consider all resolvable dids in invites "public" [\#2900](https://github.com/hyperledger/aries-cloudagent-python/pull/2900) [dbluhm](https://github.com/dbluhm)
  - fix: oob record their_service should be updatable [\#2897](https://github.com/hyperledger/aries-cloudagent-python/pull/2897) [dbluhm](https://github.com/dbluhm)
  - fix: look up conn record by invite msg id instead of key [\#2891](https://github.com/hyperledger/aries-cloudagent-python/pull/2891) [dbluhm](https://github.com/dbluhm)

- OpenAPI/Swagger updates, fixes and cleanups:
  - Fix api schema mixup in revocation routes [\#2909](https://github.com/hyperledger/aries-cloudagent-python/pull/2909) [jamshale](https://github.com/jamshale)
  - 🎨 fix typos [\#2898](https://github.com/hyperledger/aries-cloudagent-python/pull/2898) [ff137](https://github.com/ff137)
  - ⬆️ Upgrade codegen tools used in generate-open-api-specols [\#2899](https://github.com/hyperledger/aries-cloudagent-python/pull/2899) [ff137](https://github.com/ff137)
  - 🐛 Fix IndyAttrValue model that was dropped from openapi spec [\#2894](https://github.com/hyperledger/aries-cloudagent-python/pull/2894) [ff137](https://github.com/ff137)

- Test and Demo updates:
  - fix Faber demo to use oob with aip10 to support connection reuse [\#2903](https://github.com/hyperledger/aries-cloudagent-python/pull/2903) [ianco](https://github.com/ianco)
  - fix: integration tests should use didex 1.1 [\#2889](https://github.com/hyperledger/aries-cloudagent-python/pull/2889) [dbluhm](https://github.com/dbluhm)

- Credential Exchange updates and fixes:
  - fix: rev notifications on publish pending [\#2916](https://github.com/hyperledger/aries-cloudagent-python/pull/2916) [dbluhm](https://github.com/dbluhm)

- Endorsement of Indy Transactions fixes:
  - Prevent 500 error when re-promoting DID with endorsement [\#2885](https://github.com/hyperledger/aries-cloudagent-python/pull/2885) [jamshale](https://github.com/jamshale)
  - Fix ack during for auto endorsement [\#2883](https://github.com/hyperledger/aries-cloudagent-python/pull/2883) [jamshale](https://github.com/jamshale)

- Documentation publishing process updates:
  - Some updates to the mkdocs publishing process [\#2888](https://github.com/hyperledger/aries-cloudagent-python/pull/2888) [swcurran](https://github.com/swcurran)
  - Update GHA so that broken image links work on docs site - without breaking them on GitHub [\#2852](https://github.com/hyperledger/aries-cloudagent-python/pull/2852) [swcurran](https://github.com/swcurran)

- Dependencies and Internal Updates:
  - chore(deps): Bump psf/black from 24.4.0 to 24.4.2 in the all-actions group [\#2924](https://github.com/hyperledger/aries-cloudagent-python/pull/2924) [dependabot bot](https://github.com/dependabot bot)
  - fix: fixes a regression that requires a log file in multi-tenant mode [\#2918](https://github.com/hyperledger/aries-cloudagent-python/pull/2918) [amanji](https://github.com/amanji)
  - Update AnonCreds to 0.2.2 [\#2917](https://github.com/hyperledger/aries-cloudagent-python/pull/2917) [swcurran](https://github.com/swcurran)
  - chore(deps): Bump aiohttp from 3.9.3 to 3.9.4  dependencies python [\#2902](https://github.com/hyperledger/aries-cloudagent-python/pull/2902) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump idna from 3.4 to 3.7 in /demo/playground/examples  dependencies python [\#2886](https://github.com/hyperledger/aries-cloudagent-python/pull/2886) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump psf/black from 24.3.0 to 24.4.0 in the all-actions group  dependencies github_actions [\#2893](https://github.com/hyperledger/aries-cloudagent-python/pull/2893) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump idna from 3.6 to 3.7  dependencies python [\#2887](https://github.com/hyperledger/aries-cloudagent-python/pull/2887) [dependabot bot](https://github.com/dependabot bot)
  - refactor: logging configs setup [\#2870](https://github.com/hyperledger/aries-cloudagent-python/pull/2870) [amanji](https://github.com/amanji)

- Release management pull requests:
  - 0.12.1 [\#2926](https://github.com/hyperledger/aries-cloudagent-python/pull/2926) [swcurran](https://github.com/swcurran)
  - 0.12.1rc1 [\#2921](https://github.com/hyperledger/aries-cloudagent-python/pull/2921) [swcurran](https://github.com/swcurran)
  - 0.12.1rc0 [\#2912](https://github.com/hyperledger/aries-cloudagent-python/pull/2912) [swcurran](https://github.com/swcurran)

## 0.12.0

### April 11, 2024

Release 0.12.0 is a large release with many new capabilities, feature improvements, upgrades, and bug fixes. Importantly, this release completes the ACA-Py implementation of [Aries Interop Profile v2.0], and enables the elimination of unqualified DIDs. While only deprecated for now, all deployments of ACA-Py **SHOULD** move to using only fully qualified DIDs as soon as possible.

Much progress has been made on `did:peer` support in this release, with the handling of inbound [DID Peer] 1 added, and inbound and outbound support for DID Peer 2 and 4. Much attention was also paid to making sure that the Peer DID and DID Exchange capabilities match those of [Credo-TS] (formerly Aries Framework JavaScript). The completion of that work eliminates the remaining places where "unqualified" DIDs were being used, and to enable the "connection reuse" feature in the Out of Band protocol when using DID Peer 2 and 4 DIDs in invitations. See the document [Qualified DIDs] for details about how to control the use of DID Peer 2 or 4 in an ACA-Py deployment, and how to eliminate the use of unqualified DIDs. Support for DID Exchange v1.1 has been added to ACA-Py, with support for DID Exchange v1.0 retained, and we've added support for DID Rotation.

[Qualified DIDs]: https://aca-py.org/latest/features/QualifiedDIDs/
[Credo-TS]:  https://github.com/openwallet-foundation/credo-ts
[Aries Interop Profile v2.0]: https://github.com/hyperledger/aries-rfcs/tree/main/concepts/0302-aries-interop-profile#aries-interop-profile-version-20

Work continues towards supporting ledger agnostic [AnonCreds], and the new [Hyperledger AnonCreds Rust] library. Some of that work is in this release, the rest will be in the next release.

Attention was given in the release to simplifying the handling of JSON-LD [Data Integrity Verifiable Credentials].

An important change in this release is the re-organization of the ACA-Py documentation, moving the vast majority of the documents to the folders within the `docs` folder -- a long overdue change that will allow us to soon publish the documents on [https://aca-py.org](https://aca-py.org) directly from the ACA-Py repository, rather than from the separate [aries-acapy-docs](https://github.com/hyperledger/aries-acapy-docs) currently being used.

A big developer improvement is a revamping of the test handling to eliminate ~2500 warnings that were previously generated in the test suite.  Nice job [@ff137](https://github.com/ff137)!

[DID Peer]: https://identity.foundation/peer-did-method-spec/
[AnonCreds]: https://www.hyperledger.org/projects/anoncreds
[Hyperledger AnonCreds Rust]: https://github.com/hyperledger/anoncreds-rs
[Data Integrity Verifiable Credentials]: https://www.w3.org/TR/vc-data-integrity/

### 0.12.0 Breaking Changes

A deployment of this release that uses DID Peer 2 and 4 invitations may encounter problems interacting with agents deployed using older Aries protocols. Led by the Aries Working Group, the Aries community is encouraging the upgrade of all ecosystem deployments to accept all commonly used qualified DIDs, including DID Peer 2 and 4. See the document [Qualified DIDs] for more details about the transition to using only qualified DIDs. If deployments you interact with are still using unqualified DIDs, please encourage them to upgrade as soon as possible.

Specifically for those upgrading their ACA-Py instance that create Out of Band invitations with more than one `handshake_protocol`, the protocol for the connection has been removed. See [Issue \#2879] contains the details of this subtle breaking change.

[Issue \#2879]: https://github.com/hyperledger/aries-cloudagent-python/pull/2880

New deprecation notices were added to ACA-Py on startup and in the OpenAPI/Swagger interface. Those added are listed below. As well, we anticipate 0.12.0 being the **last ACA-Py release to include support for the previously deprecated Indy SDK**.

- RFC 0036 Issue Credential v1
  - Migrate to use RFC 0453 Issue Credential v2
- RFC 0037 Present Proof v2
  - Migrate to use RFC 0454 Present Proof v2
- RFC 0169 Connections
  - Migrate to use RFC 0023 DID Exchange and 0434 Out-of-Band
- The use of `did:sov:...` as a Protocol Doc URI
  - Migrate to use `https://didcomm.org/`.

#### 0.12.0 Categorized List of Pull Requests

- DID Handling and Connection Establishment Updates/Fixes
  - fix: conn proto in invite webhook if known [\#2880](https://github.com/hyperledger/aries-cloudagent-python/pull/2880) [dbluhm](https://github.com/dbluhm)
  - Emit the OOB done event even for multi-use invites [\#2872](https://github.com/hyperledger/aries-cloudagent-python/pull/2872) [ianco](https://github.com/ianco)
  - refactor: introduce use_did and use_did_method [\#2862](https://github.com/hyperledger/aries-cloudagent-python/pull/2862) [dbluhm](https://github.com/dbluhm)
  - fix(credo-interop): various didexchange and did:peer related fixes  1.0.0 [\#2748](https://github.com/hyperledger/aries-cloudagent-python/pull/2748) [dbluhm](https://github.com/dbluhm)
  - Change did <--> verkey logging on connections [\#2853](https://github.com/hyperledger/aries-cloudagent-python/pull/2853) [jamshale](https://github.com/jamshale)
  - fix: did exchange multiuse invites respond in kind [\#2850](https://github.com/hyperledger/aries-cloudagent-python/pull/2850) [dbluhm](https://github.com/dbluhm)
  - Support connection re-use for did:peer:2/4 [\#2823](https://github.com/hyperledger/aries-cloudagent-python/pull/2823) [ianco](https://github.com/ianco)
  - feat: did-rotate [\#2816](https://github.com/hyperledger/aries-cloudagent-python/pull/2816) [amanji](https://github.com/amanji)
  - Author subwallet setup automation [\#2791](https://github.com/hyperledger/aries-cloudagent-python/pull/2791) [jamshale](https://github.com/jamshale)
  - fix: save multi_use to the DB for OOB invitations [\#2694](https://github.com/hyperledger/aries-cloudagent-python/pull/2694) [frostyfrog](https://github.com/frostyfrog)
  - Connection and DIDX Problem Reports [\#2653](https://github.com/hyperledger/aries-cloudagent-python/pull/2653) [usingtechnology](https://github.com/usingtechnology)

- DID Peer and DID Resolver Updates and Fixes
  - Integration test for did:peer [\#2713](https://github.com/hyperledger/aries-cloudagent-python/pull/2713) [ianco](https://github.com/ianco)
  - Feature/emit did peer 4 [\#2696](https://github.com/hyperledger/aries-cloudagent-python/pull/2696) [Jsyro](https://github.com/Jsyro)
  - did peer 4 resolution [\#2692](https://github.com/hyperledger/aries-cloudagent-python/pull/2692) [Jsyro](https://github.com/Jsyro)
  - Emit did:peer:2 for didexchange [\#2687](https://github.com/hyperledger/aries-cloudagent-python/pull/2687) [Jsyro](https://github.com/Jsyro)
  - Add did web method type as a default option [\#2684](https://github.com/hyperledger/aries-cloudagent-python/pull/2684) [PatStLouis](https://github.com/PatStLouis)
  - feat: add did:jwk resolver [\#2645](https://github.com/hyperledger/aries-cloudagent-python/pull/2645) [dbluhm](https://github.com/dbluhm)
  - feat: support resolving did:peer:1 received in did exchange [\#2611](https://github.com/hyperledger/aries-cloudagent-python/pull/2611) [dbluhm](https://github.com/dbluhm)

- AnonCreds and Ledger Agnostic AnonCreds RS Changes
  - Prevent revocable cred def being created without tails server [\#2849](https://github.com/hyperledger/aries-cloudagent-python/pull/2849) [jamshale](https://github.com/jamshale)
  - Anoncreds - support for anoncreds and askar wallets concurrently [\#2822](https://github.com/hyperledger/aries-cloudagent-python/pull/2822) [jamshale](https://github.com/jamshale)
  - Send revocation list instead of rev_list object - Anoncreds [\#2821](https://github.com/hyperledger/aries-cloudagent-python/pull/2821) [jamshale](https://github.com/jamshale)
  - Fix anoncreds non-endorsement revocation [\#2814](https://github.com/hyperledger/aries-cloudagent-python/pull/2814) [jamshale](https://github.com/jamshale)
  - Get and create anoncreds profile when using anoncreds subwallet [\#2803](https://github.com/hyperledger/aries-cloudagent-python/pull/2803) [jamshale](https://github.com/jamshale)
  - Add anoncreds multitenant endorsement integration tests [\#2801](https://github.com/hyperledger/aries-cloudagent-python/pull/2801) [jamshale](https://github.com/jamshale)
  - Anoncreds revoke and publish-revocations endorsement [\#2782](https://github.com/hyperledger/aries-cloudagent-python/pull/2782) [jamshale](https://github.com/jamshale)
  - Upgrade anoncreds to version 0.2.0-dev11 [\#2763](https://github.com/hyperledger/aries-cloudagent-python/pull/2763) [jamshale](https://github.com/jamshale)
  - Update anoncreds to 0.2.0-dev10 [\#2758](https://github.com/hyperledger/aries-cloudagent-python/pull/2758) [jamshale](https://github.com/jamshale)
  - Anoncreds - Cred Def and Revocation Endorsement [\#2752](https://github.com/hyperledger/aries-cloudagent-python/pull/2752) [jamshale](https://github.com/jamshale)
  - Upgrade anoncreds to 0.2.0-dev9 [\#2741](https://github.com/hyperledger/aries-cloudagent-python/pull/2741) [jamshale](https://github.com/jamshale)
  - Upgrade anoncred-rs to version 0.2.0-dev8 [\#2734](https://github.com/hyperledger/aries-cloudagent-python/pull/2734) [jamshale](https://github.com/jamshale)
  - Upgrade anoncreds to 0.2.0.dev7 [\#2719](https://github.com/hyperledger/aries-cloudagent-python/pull/2719) [jamshale](https://github.com/jamshale)
  - Improve api documentation and error handling [\#2690](https://github.com/hyperledger/aries-cloudagent-python/pull/2690) [jamshale](https://github.com/jamshale)
  - Add unit tests for anoncreds revocation [\#2688](https://github.com/hyperledger/aries-cloudagent-python/pull/2688) [jamshale](https://github.com/jamshale)
  - Return 404 when schema not found [\#2683](https://github.com/hyperledger/aries-cloudagent-python/pull/2683) [jamshale](https://github.com/jamshale)
  - Anoncreds - Add unit testing [\#2672](https://github.com/hyperledger/aries-cloudagent-python/pull/2672) [jamshale](https://github.com/jamshale)
  - Additional anoncreds integration tests  AnonCreds [\#2660](https://github.com/hyperledger/aries-cloudagent-python/pull/2660) [ianco](https://github.com/ianco)
  - Update integration tests for anoncreds-rs  AnonCreds [\#2651](https://github.com/hyperledger/aries-cloudagent-python/pull/2651) [ianco](https://github.com/ianco)
  - Initial migration of anoncreds revocation code  AnonCreds [\#2643](https://github.com/hyperledger/aries-cloudagent-python/pull/2643) [ianco](https://github.com/ianco)
  - Integrate Anoncreds rs into credential and presentation endpoints  AnonCreds [\#2632](https://github.com/hyperledger/aries-cloudagent-python/pull/2632) [ianco](https://github.com/ianco)
  - Initial code migration from anoncreds-rs branch  AnonCreds [\#2596](https://github.com/hyperledger/aries-cloudagent-python/pull/2596) [ianco](https://github.com/ianco)

- Hyperledger Indy ledger related updates and fixes
  - Remove requirement for write ledger in read-only mode. [\#2836](https://github.com/hyperledger/aries-cloudagent-python/pull/2836) [esune](https://github.com/esune)
  - Add known issues section to Multiledger.md documentation [\#2788](https://github.com/hyperledger/aries-cloudagent-python/pull/2788) [esune](https://github.com/esune)
  - fix: update constants in TransactionRecord [\#2698](https://github.com/hyperledger/aries-cloudagent-python/pull/2698) [amanji](https://github.com/amanji)
  - Cache TAA by wallet name [\#2676](https://github.com/hyperledger/aries-cloudagent-python/pull/2676) [jamshale](https://github.com/jamshale)
  - Fix: RevRegEntry Transaction Endorsement  0.11.0 [\#2558](https://github.com/hyperledger/aries-cloudagent-python/pull/2558) [shaangill025](https://github.com/shaangill025)

- JSON-LD Verifiable Credential/DIF Presentation Exchange updates
  - Add missing VC-DI/LD-Proof verification method option [\#2867](https://github.com/hyperledger/aries-cloudagent-python/pull/2867) [PatStLouis](https://github.com/PatStLouis)
  - Revert profile injection for VcLdpManager on vc-api endpoints [\#2794](https://github.com/hyperledger/aries-cloudagent-python/pull/2794) [PatStLouis](https://github.com/PatStLouis)
  - Add cached copy of BBS v1 context [\#2749](https://github.com/hyperledger/aries-cloudagent-python/pull/2749) [andrewwhitehead](https://github.com/andrewwhitehead)
  - Update BBS+ context to bypass redirections [\#2739](https://github.com/hyperledger/aries-cloudagent-python/pull/2739) [swcurran](https://github.com/swcurran)
  - feat: make VcLdpManager pluggable [\#2706](https://github.com/hyperledger/aries-cloudagent-python/pull/2706) [dbluhm](https://github.com/dbluhm)
  - fix: minor type hint corrections for VcLdpManager [\#2704](https://github.com/hyperledger/aries-cloudagent-python/pull/2704) [dbluhm](https://github.com/dbluhm)
  - Remove if condition which checks if the credential.type array is equal to 1 [\#2670](https://github.com/hyperledger/aries-cloudagent-python/pull/2670) [PatStLouis](https://github.com/PatStLouis)
  - Feature Suggestion: Include a Reason When Constraints Cannot Be Applied [\#2630](https://github.com/hyperledger/aries-cloudagent-python/pull/2630) [Ennovate-com](https://github.com/Ennovate-com)
  - refactor: make ldp_vc logic reusable [\#2533](https://github.com/hyperledger/aries-cloudagent-python/pull/2533) [dbluhm](https://github.com/dbluhm)

- Credential Exchange (Issue, Present) Updates
  - Allow for crids in event payload to be integers [\#2819](https://github.com/hyperledger/aries-cloudagent-python/pull/2819) [jamshale](https://github.com/jamshale)
  - Create revocation notification after list entry written to ledger [\#2812](https://github.com/hyperledger/aries-cloudagent-python/pull/2812) [jamshale](https://github.com/jamshale)
  - Remove exception on connectionless presentation problem report handler [\#2723](https://github.com/hyperledger/aries-cloudagent-python/pull/2723) [loneil](https://github.com/loneil)
  - Ensure "preserve_exchange_records" flags are set. [\#2664](https://github.com/hyperledger/aries-cloudagent-python/pull/2664) [usingtechnology](https://github.com/usingtechnology)
  - Slight improvement to credx proof validation error message [\#2655](https://github.com/hyperledger/aries-cloudagent-python/pull/2655) [ianco](https://github.com/ianco)
  - Add ConnectionProblemReport handler [\#2600](https://github.com/hyperledger/aries-cloudagent-python/pull/2600) [usingtechnology](https://github.com/usingtechnology)

- Multitenancy Updates and Fixes
  - feature/per tenant settings [\#2790](https://github.com/hyperledger/aries-cloudagent-python/pull/2790) [amanji](https://github.com/amanji)
  - Improve Per Tenant Logging: Fix issues around default log file path [\#2659](https://github.com/hyperledger/aries-cloudagent-python/pull/2659) [shaangill025](https://github.com/shaangill025)

- Other Fixes, Demo, DevContainer and Documentation Fixes
  - chore: propose official deprecations of a couple of features [\#2856](https://github.com/hyperledger/aries-cloudagent-python/pull/2856) [dbluhm](https://github.com/dbluhm)
  - feat: external signature suite provider interface [\#2835](https://github.com/hyperledger/aries-cloudagent-python/pull/2835) [dbluhm](https://github.com/dbluhm)
  - Update GHA so that broken image links work on docs site - without breaking them on GitHub [\#2852](https://github.com/hyperledger/aries-cloudagent-python/pull/2852) [swcurran](https://github.com/swcurran)
  - Minor updates to the documentation - links [\#2848](https://github.com/hyperledger/aries-cloudagent-python/pull/2848) [swcurran](https://github.com/swcurran)
  - Update to run_demo script to support Apple M1 CPUs [\#2843](https://github.com/hyperledger/aries-cloudagent-python/pull/2843) [swcurran](https://github.com/swcurran)
  - Add functionality for building and running agents seprately [\#2845](https://github.com/hyperledger/aries-cloudagent-python/pull/2845) [sarthakvijayvergiya](https://github.com/sarthakvijayvergiya)
  - Cleanup of docs [\#2831](https://github.com/hyperledger/aries-cloudagent-python/pull/2831) [swcurran](https://github.com/swcurran)
  - Create AnonCredsMethods.md [\#2832](https://github.com/hyperledger/aries-cloudagent-python/pull/2832) [swcurran](https://github.com/swcurran)
  - FIX: GHA update for doc publishing, fix doc file that was blanked [\#2820](https://github.com/hyperledger/aries-cloudagent-python/pull/2820) [swcurran](https://github.com/swcurran)
  - More updates to get docs publishing [\#2810](https://github.com/hyperledger/aries-cloudagent-python/pull/2810) [swcurran](https://github.com/swcurran)
  - Eliminate the double workflow event [\#2811](https://github.com/hyperledger/aries-cloudagent-python/pull/2811) [swcurran](https://github.com/swcurran)
  - Publish docs GHActions tweak [\#2806](https://github.com/hyperledger/aries-cloudagent-python/pull/2806) [swcurran](https://github.com/swcurran)
  - Update publish-docs to operate on main and on branches prefixed with docs-v [\#2804](https://github.com/hyperledger/aries-cloudagent-python/pull/2804) [swcurran](https://github.com/swcurran)
  - Add index.html redirector to gh-pages branch [\#2802](https://github.com/hyperledger/aries-cloudagent-python/pull/2802) [swcurran](https://github.com/swcurran)
  - Demo description of reuse in establishing a connection [\#2787](https://github.com/hyperledger/aries-cloudagent-python/pull/2787) [swcurran](https://github.com/swcurran)
  - Reorganize the ACA-Py Documentation Files [\#2765](https://github.com/hyperledger/aries-cloudagent-python/pull/2765) [swcurran](https://github.com/swcurran)
  - Tweaks to MD files to enable aca-py.org publishing [\#2771](https://github.com/hyperledger/aries-cloudagent-python/pull/2771) [swcurran](https://github.com/swcurran)
  - Update devcontainer documentation [\#2729](https://github.com/hyperledger/aries-cloudagent-python/pull/2729) [jamshale](https://github.com/jamshale)
  - Update the SupportedRFCs Document to be up to date [\#2722](https://github.com/hyperledger/aries-cloudagent-python/pull/2722) [swcurran](https://github.com/swcurran)
  - Fix incorrect Sphinx search library version reference [\#2716](https://github.com/hyperledger/aries-cloudagent-python/pull/2716) [swcurran](https://github.com/swcurran)
  - Update RTD requirements after security vulnerability recorded [\#2712](https://github.com/hyperledger/aries-cloudagent-python/pull/2712) [swcurran](https://github.com/swcurran)
  - Update legacy bcgovimages references. [\#2700](https://github.com/hyperledger/aries-cloudagent-python/pull/2700) [WadeBarnes](https://github.com/WadeBarnes)
  - fix: link to raw content change from master to main [\#2663](https://github.com/hyperledger/aries-cloudagent-python/pull/2663) [Ennovate-com](https://github.com/Ennovate-com)
  - fix: open-api generator script [\#2661](https://github.com/hyperledger/aries-cloudagent-python/pull/2661) [dbluhm](https://github.com/dbluhm)
  - Update the ReadTheDocs config in case we do another 0.10.x release [\#2629](https://github.com/hyperledger/aries-cloudagent-python/pull/2629) [swcurran](https://github.com/swcurran)

- Dependencies and Internal Updates
  - Add wallet.type config to /settings endpoint [\#2877](https://github.com/hyperledger/aries-cloudagent-python/pull/2877) [jamshale](https://github.com/jamshale)
  - chore(deps): Bump pillow from 10.2.0 to 10.3.0  dependencies python [\#2869](https://github.com/hyperledger/aries-cloudagent-python/pull/2869) [dependabot bot](https://github.com/dependabot bot)
  - Fix run_tests script [\#2866](https://github.com/hyperledger/aries-cloudagent-python/pull/2866) [ianco](https://github.com/ianco)
  - fix: states for discovery record to emit webhook [\#2858](https://github.com/hyperledger/aries-cloudagent-python/pull/2858) [dbluhm](https://github.com/dbluhm)
  - Increase promote did retries [\#2854](https://github.com/hyperledger/aries-cloudagent-python/pull/2854) [jamshale](https://github.com/jamshale)
  - chore(deps-dev): Bump black from 24.1.1 to 24.3.0  dependencies python [\#2847](https://github.com/hyperledger/aries-cloudagent-python/pull/2847) [dependabot bot](https://github.com/dependabot bot)
  - chore(deps): Bump the all-actions group with 1 update  dependencies github_actions [\#2844](https://github.com/hyperledger/aries-cloudagent-python/pull/2844) [dependabot bot](https://github.com/dependabot bot)
  - patch for #2781: User Agent header in doc loader [\#2824](https://github.com/hyperledger/aries-cloudagent-python/pull/2824) [gmulhearn-anonyome](https://github.com/gmulhearn-anonyome)
  - chore(deps): Bump jwcrypto from 1.5.4 to 1.5.6  dependencies python [\#2833](https://github.com/hyperledger/aries-cloudagent-python/pull/2833) [dependabot bot](https://github.com/dependabot bot)
  - bot    chore(deps): Bump cryptography from 42.0.3 to 42.0.4  dependencies python [\#2805](https://github.com/hyperledger/aries-cloudagent-python/pull/2805) [dependabot](https://github.com/dependabot)
  - bot    chore(deps): Bump the all-actions group with 3 updates  dependencies github_actions [\#2815](https://github.com/hyperledger/aries-cloudagent-python/pull/2815) [dependabot](https://github.com/dependabot)
  - Change middleware registration order [\#2796](https://github.com/hyperledger/aries-cloudagent-python/pull/2796) [PatStLouis](https://github.com/PatStLouis)
  - Bump pyld version to 2.0.4 [\#2795](https://github.com/hyperledger/aries-cloudagent-python/pull/2795) [PatStLouis](https://github.com/PatStLouis)
  - Revert profile inject [\#2789](https://github.com/hyperledger/aries-cloudagent-python/pull/2789) [jamshale](https://github.com/jamshale)
  - Move emit events to profile and delay sending until after commit [\#2760](https://github.com/hyperledger/aries-cloudagent-python/pull/2760) [ianco](https://github.com/ianco)
  - fix: partial revert of ConnRecord schema change  1.0.0 [\#2746](https://github.com/hyperledger/aries-cloudagent-python/pull/2746) [dbluhm](https://github.com/dbluhm)
  - chore(deps): Bump aiohttp from 3.9.1 to 3.9.2  dependencies [\#2745](https://github.com/hyperledger/aries-cloudagent-python/pull/2745) [dependabot bot](https://github.com/dependabot)
  - bump pydid to v 0.4.3 [\#2737](https://github.com/hyperledger/aries-cloudagent-python/pull/2737) [PatStLouis](https://github.com/PatStLouis)
  - Fix subwallet record removal [\#2721](https://github.com/hyperledger/aries-cloudagent-python/pull/2721) [andrewwhitehead](https://github.com/andrewwhitehead)
  - chore(deps): Bump jinja2 from 3.1.2 to 3.1.3  dependencies [\#2707](https://github.com/hyperledger/aries-cloudagent-python/pull/2707) [dependabot bot](https://github.com/dependabot)
  - feat: inject profile [\#2705](https://github.com/hyperledger/aries-cloudagent-python/pull/2705) [dbluhm](https://github.com/dbluhm)
  - Remove tiny-vim from being added to the container image to reduce reported vulnerabilities from scanning [\#2699](https://github.com/hyperledger/aries-cloudagent-python/pull/2699) [swcurran](https://github.com/swcurran)
  - chore(deps): Bump jwcrypto from 1.5.0 to 1.5.1  dependencies [\#2689](https://github.com/hyperledger/aries-cloudagent-python/pull/2689) [dependabot bot](https://github.com/dependabot)
  - Update dependencies [\#2686](https://github.com/hyperledger/aries-cloudagent-python/pull/2686) [andrewwhitehead](https://github.com/andrewwhitehead)
  - Fix: Change To Use Timezone Aware UTC datetime [\#2679](https://github.com/hyperledger/aries-cloudagent-python/pull/2679) [Ennovate-com](https://github.com/Ennovate-com)
  - fix: update broken demo dependency [\#2638](https://github.com/hyperledger/aries-cloudagent-python/pull/2638) [mrkaurelius](https://github.com/mrkaurelius)
  - Bump cryptography from 41.0.5 to 41.0.6  dependencies [\#2636](https://github.com/hyperledger/aries-cloudagent-python/pull/2636) [dependabot bot](https://github.com/dependabot)
  - Bump aiohttp from 3.8.6 to 3.9.0  dependencies [\#2635](https://github.com/hyperledger/aries-cloudagent-python/pull/2635) [dependabot bot](https://github.com/dependabot)

- CI/CD, Testing, and Developer Tools/Productivity Updates
  - Fix deprecation warnings [\#2756](https://github.com/hyperledger/aries-cloudagent-python/pull/2756) [ff137](https://github.com/ff137)
  - chore(deps): Bump the all-actions group with 10 updates  dependencies [\#2784](https://github.com/hyperledger/aries-cloudagent-python/pull/2784) [dependabot bot](https://github.com/dependabot)
  - Add Dependabot configuration [\#2783](https://github.com/hyperledger/aries-cloudagent-python/pull/2783) [WadeBarnes](https://github.com/WadeBarnes)
  - Implement B006 rule [\#2775](https://github.com/hyperledger/aries-cloudagent-python/pull/2775) [jamshale](https://github.com/jamshale)
  - ⬆️ Upgrade pytest to 8.0 [\#2773](https://github.com/hyperledger/aries-cloudagent-python/pull/2773) [ff137](https://github.com/ff137)
  - ⬆️ Update pytest-asyncio to 0.23.4 [\#2764](https://github.com/hyperledger/aries-cloudagent-python/pull/2764) [ff137](https://github.com/ff137)
  - Remove asynctest dependency and fix "coroutine not awaited" warnings [\#2755](https://github.com/hyperledger/aries-cloudagent-python/pull/2755) [ff137](https://github.com/ff137)
  - Fix pytest collection errors when anoncreds package is not installed [\#2750](https://github.com/hyperledger/aries-cloudagent-python/pull/2750) [andrewwhitehead](https://github.com/andrewwhitehead)
  - chore: pin black version [\#2747](https://github.com/hyperledger/aries-cloudagent-python/pull/2747) [dbluhm](https://github.com/dbluhm)
  - Tweak scope of GHA integration tests [\#2662](https://github.com/hyperledger/aries-cloudagent-python/pull/2662) [ianco](https://github.com/ianco)
  - Update snyk workflow to execute on Pull Request [\#2658](https://github.com/hyperledger/aries-cloudagent-python/pull/2658) [usingtechnology](https://github.com/usingtechnology)

- Release management pull requests
  - 0.12.0 [\#2882](https://github.com/hyperledger/aries-cloudagent-python/pull/2882) [swcurran](https://github.com/swcurran)
  - 0.12.0rc3 [\#2878](https://github.com/hyperledger/aries-cloudagent-python/pull/2878) [swcurran](https://github.com/swcurran)
  - 0.12.0rc2 [\#2825](https://github.com/hyperledger/aries-cloudagent-python/pull/2825) [swcurran](https://github.com/swcurran)
  - 0.12.0rc1 [\#2800](https://github.com/hyperledger/aries-cloudagent-python/pull/2800) [swcurran](https://github.com/swcurran)
  - 0.12.0rc1 [\#2799](https://github.com/hyperledger/aries-cloudagent-python/pull/2799) [swcurran](https://github.com/swcurran)
  - 0.12.0rc0 [\#2732](https://github.com/hyperledger/aries-cloudagent-python/pull/2732) [swcurran](https://github.com/swcurran)

## 0.11.3

### August 2, 2024

A patch release to add a fix that ensures that sufficient webhook information is sent to an ACA-Py controller that is executing the [AIP 2.0 Present Proof 2.0 Protocol].

[AIP 2.0 Present Proof 2.0 Protocol]: https://identity.foundation/aries-rfcs/latest/aip2/0454-present-proof-v2/

### 0.11.3 Breaking Changes

There are no breaking changes in this release.

#### 0.11.3 Categorized List of Pull Requests

- Dependency update and release PR
  - [ PATCH ] 0.11.x with PR 3081 terse webhooks [\#3142](https://github.com/hyperledger/aries-cloudagent-python/pull/3142) [jamshale](https://github.com/jamshale)
- Release management pull requests
  - 0.11.3 [\#3144](https://github.com/hyperledger/aries-cloudagent-python/pull/3144) [swcurran](https://github.com/swcurran)
- PRs cherry-picked into [\#3142](https://github.com/hyperledger/aries-cloudagent-python/pull/3142) from the `main` branch:
  - Add by_format to terse webhook for presentations [\#3081](https://github.com/hyperledger/aries-cloudagent-python/pull/3081) [ianco](https://github.com/ianco)

## 0.11.2

### July 25, 2024

A patch release to add the verification of a linkage between an inbound message and its associated connection (if any) before processing the message.

### 0.11.2 Breaking Changes

There are no breaking changes in this release.

#### 0.11.2 Categorized List of Pull Requests

- Dependency update and release PR
  - Apply security patch 0.11.x [\#3120](https://github.com/hyperledger/aries-cloudagent-python/pull/3120) [jamshale](https://github.com/jamshale)
- Release management pull requests
  - 0.11.2 [\#3122](https://github.com/hyperledger/aries-cloudagent-python/pull/3122) [swcurran](https://github.com/swcurran)
- PRs cherry-picked into [\#3120](https://github.com/hyperledger/aries-cloudagent-python/pull/3120) from the `main` branch:
  - Check connection is ready in all connection required handlers [\#3095](https://github.com/hyperledger/aries-cloudagent-python/pull/3095) [jamshale](https://github.com/jamshale)

## 0.11.1

### May 7, 2024

A patch release to update the `aiohttp` library such that a reported serious
vulnerability is addressed such that a crafted payload delivered to `aiohttp`
can put it in an infinite loop, which can be used for a low cost denial of
service attack. [CVE-2024-30251] describes the issue.

[CVE-2024-30251]: https://github.com/advisories/GHSA-5m98-qgg9-wh84

### 0.11.1 Breaking Changes

There are no breaking changes in this release. The only changed is the updated
`aiohttp` dependency.

#### 0.11.1 Categorized List of Pull Requests

- Dependency update and release PR
  - 0.11.1 and aiohttp update [\#2936](https://github.com/hyperledger/aries-cloudagent-python/pull/2936) [swcurran](https://github.com/swcurran)

## 0.11.0

### November 24, 2023

Release 0.11.0 is a relatively large release of new features, fixes, and
internal updates. 0.11.0 is planned to be the last significant update before we
begin the transition to using the ledger agnostic [AnonCreds
Rust](https://github.com/hyperledger/anoncreds-rs) in a release that is expected
to bring Admin/Controller API changes. We plan to do patches to the 0.11.x
branch while the transition is made to using [Anoncreds Rust].

An important addition to ACA-Py is support for signing and verifying
[SD-JWT] verifiable credentials. We expect this to be the first of the changes
to extend ACA-Py to support [OpenID4VC protocols].

This release and [Release 0.10.5] contain a high priority fix to correct
an issue with the handling of the JSON-LD presentation verifications, where the
status of the verification of the `presentation.proof` in the Verifiable
Presentation was not included when determining the verification value (`true` or
`false`) of the overall presentation. A forthcoming security advisory will cover
the details. **Anyone using JSON-LD presentations is recommended to upgrade to one
of these versions of ACA-Py as soon as possible.**

[SD-JWT]: https://sdjwt.info/
[OpenID4VC protocols]: https://openid.net/wg/digital-credentials-protocols/
[Release 0.10.5]: https://github.com/hyperledger/aries-cloudagent-python/releases/tag/0.10.5

In the CI/CD realm, substantial changes were applied to the source base in
switching from:

- `pip` to [Poetry](https://python-poetry.org/) for packaging and
dependency management,
- Flake8 to [Ruff](https://docs.astral.sh/ruff/) for linting,
- `asynctest` to `IsolatedAsyncioTestCase` and `AsyncMock`
objects now included in Python's builtin `unittest` package for unit testing.

These are necessary and important modernization changes, with the latter two
triggering many (largely mechanical) changes to the codebase.

### 0.11.0 Breaking Changes

In addition to the impacts of the change for developers in switching from `pip`
to Poetry, the only significant breaking change is the (overdue) transition of
ACA-Py to always use the new DIDComm message type prefix, changing the DID
Message prefix from the old hardcoded `did:sov:BzCbsNYhMrjHiqZDTUASHg;spec` to
the new hardcoded `https://didcomm.org` value, and using the new DIDComm MIME
type in place of the old. The vast majority (all?) Aries deployments have long
since been updated to accept both values, so this change just forces the use of
the newer value in sending messages. In updating this, we retained the old
configuration parameters most deployments were using
(`--emit-new-didcomm-prefix` and `--emit-new-didcomm-mime-type`) but updated the
code to set the configuration parameters to `true` even if the parameters were
not set. See [PR \#2517].

The JSON-LD verifiable credential handling of JSON-LD contexts has been updated
to pre-load the base contexts into the repository code so they are not fetched
at run time. This is a security best practice for JSON-LD, and prevents errors
in production when, from time to time, the JSON-LD contexts are unavailable
because of outages of the web servers where they are hosted. See [PR \#2587].

A Problem Report message is now sent when a request for a credential is received
and there is no associated Credential Exchange Record. This may happen, for
example, if an issuer decides to delete a Credential Exchange Record that has
not be answered for a long time, and the holder responds after the delete. See
[PR \#2577].

[PR \#2517]: https://github.com/hyperledger/aries-cloudagent-python/pull/2517
[PR \#2587]: https://github.com/hyperledger/aries-cloudagent-python/pull/2587
[PR \#2577]: https://github.com/hyperledger/aries-cloudagent-python/pull/2577

#### 0.11.0 Categorized List of Pull Requests

- DIDComm Messaging Improvements/Fixes
  - Change arg_parse to always set --emit-new-didcomm-prefix and --emit-new-didcomm-mime-type to true [\#2517](https://github.com/hyperledger/aries-cloudagent-python/pull/2517) [swcurran](https://github.com/swcurran)
- DID Handling and Connection Establishment Updates/Fixes
  - Goal and Goal Code in invitation URL. [\#2591](https://github.com/hyperledger/aries-cloudagent-python/pull/2591) [usingtechnology](https://github.com/usingtechnology)
  - refactor: use did-peer-2 instead of peerdid [\#2561](https://github.com/hyperledger/aries-cloudagent-python/pull/2561) [dbluhm](https://github.com/dbluhm)
  - Fix: Problem Report Before Exchange Established [\#2519](https://github.com/hyperledger/aries-cloudagent-python/pull/2519) [Ennovate-com](https://github.com/Ennovate-com)
  - fix: issue #2434: Change DIDExchange States to Match rfc160 [\#2461](https://github.com/hyperledger/aries-cloudagent-python/pull/2461) [anwalker293](https://github.com/anwalker293)
- DID Peer and DID Resolver Updates and Fixes
  - fix: unique ids for services in legacy peer [\#2476](https://github.com/hyperledger/aries-cloudagent-python/pull/2476) [dbluhm](https://github.com/dbluhm)
  - peer did 2/3 resolution  enhancement [\#2472](https://github.com/hyperledger/aries-cloudagent-python/pull/2472) [Jsyro](https://github.com/Jsyro)
  - feat: add timeout to did resolver resolve method [\#2464](https://github.com/hyperledger/aries-cloudagent-python/pull/2464) [dbluhm](https://github.com/dbluhm)
- ACA-Py as a DIDComm Mediator Updates and Fixes
  - fix: routing behind mediator [\#2536](https://github.com/hyperledger/aries-cloudagent-python/pull/2536) [dbluhm](https://github.com/dbluhm)
  - fix: mediation routing keys as did key [\#2516](https://github.com/hyperledger/aries-cloudagent-python/pull/2516) [dbluhm](https://github.com/dbluhm)
  - refactor: drop mediator_terms and recipient_terms [\#2515](https://github.com/hyperledger/aries-cloudagent-python/pull/2515) [dbluhm](https://github.com/dbluhm)
- Fixes to Upgrades
  - 🐛 fix wallet_update when only extra_settings requested [\#2612](https://github.com/hyperledger/aries-cloudagent-python/pull/2612) [ff137](https://github.com/ff137)
- Hyperledger Indy ledger related updates and fixes
  - fix: taa rough timestamp timezone from datetime [\#2554](https://github.com/hyperledger/aries-cloudagent-python/pull/2554) [dbluhm](https://github.com/dbluhm)
  - 🎨 clarify LedgerError message when TAA is required and not accepted [\#2545](https://github.com/hyperledger/aries-cloudagent-python/pull/2545) [ff137](https://github.com/ff137)
  - Feat: Upgrade from tags and fix issue with legacy IssuerRevRegRecords [<=v0.5.2] [\#2486](https://github.com/hyperledger/aries-cloudagent-python/pull/2486) [shaangill025](https://github.com/shaangill025)
  - Bugfix: Issue with write ledger pool when performing Accumulator sync [\#2480](https://github.com/hyperledger/aries-cloudagent-python/pull/2480) [shaangill025](https://github.com/shaangill025)
  - Issue #2419 InvalidClientTaaAcceptanceError time too precise error if container timezone is not UTC [\#2420](https://github.com/hyperledger/aries-cloudagent-python/pull/2420) [Ennovate-com](https://github.com/Ennovate-com)
- OpenID4VC / SD-JWT Updates
  - chore: point to official sd-jwt lib release [\#2573](https://github.com/hyperledger/aries-cloudagent-python/pull/2573) [dbluhm](https://github.com/dbluhm)
  - Feat/sd jwt implementation [\#2487](https://github.com/hyperledger/aries-cloudagent-python/pull/2487) [cjhowland](https://github.com/cjhowland)
- JSON-LD Verifiable Credential/Presentation updates
  - fix: report presentation result [\#2615](https://github.com/hyperledger/aries-cloudagent-python/pull/2615) [dbluhm](https://github.com/dbluhm)
  - Fix Issue #2589 TypeError When There Are No Nested Requirements [\#2590](https://github.com/hyperledger/aries-cloudagent-python/pull/2590) [Ennovate-com](https://github.com/Ennovate-com)
  - feat: use a local static cache for commonly used contexts [\#2587](https://github.com/hyperledger/aries-cloudagent-python/pull/2587) [chumbert](https://github.com/chumbert)
  - Issue #2488 KeyError raised when Subject ID is not a URI [\#2490](https://github.com/hyperledger/aries-cloudagent-python/pull/2490) [Ennovate-com](https://github.com/Ennovate-com)
- Credential Exchange (Issue, Present) Updates
  - Default connection_id to None to account for Connectionless Proofs [\#2605](https://github.com/hyperledger/aries-cloudagent-python/pull/2605) [popkinj](https://github.com/popkinj)
  - Send Problem report when CredEx not found [\#2577](https://github.com/hyperledger/aries-cloudagent-python/pull/2577) [usingtechnology](https://github.com/usingtechnology)
  - fix: clean up requests and invites [\#2560](https://github.com/hyperledger/aries-cloudagent-python/pull/2560) [dbluhm](https://github.com/dbluhm)
- Multitenancy Updates and Fixes
  - Feat: Support subwallet upgradation using the Upgrade command [\#2529](https://github.com/hyperledger/aries-cloudagent-python/pull/2529) [shaangill025](https://github.com/shaangill025)
- Other Fixes, Demo, DevContainer and Documentation Fixes
  - fix: wallet type help text out of date [\#2618](https://github.com/hyperledger/aries-cloudagent-python/pull/2618) [dbluhm](https://github.com/dbluhm)
  - fix: typos [\#2614](https://github.com/hyperledger/aries-cloudagent-python/pull/2614) [omahs](https://github.com/omahs)
  - black formatter extension configuration update [\#2603](https://github.com/hyperledger/aries-cloudagent-python/pull/2603) [usingtechnology](https://github.com/usingtechnology)
  - Update Devcontainer pytest ruff black [\#2602](https://github.com/hyperledger/aries-cloudagent-python/pull/2602) [usingtechnology](https://github.com/usingtechnology)
  - Issue 2570 devcontainer ruff, black and pytest [\#2595](https://github.com/hyperledger/aries-cloudagent-python/pull/2595) [usingtechnology](https://github.com/usingtechnology)
  - chore: correct type hints on base record [\#2604](https://github.com/hyperledger/aries-cloudagent-python/pull/2604) [dbluhm](https://github.com/dbluhm)
  - Playground needs optionally external network [\#2564](https://github.com/hyperledger/aries-cloudagent-python/pull/2564) [usingtechnology](https://github.com/usingtechnology)
  - Issue 2555 playground scripts readme [\#2563](https://github.com/hyperledger/aries-cloudagent-python/pull/2563) [usingtechnology](https://github.com/usingtechnology)
  - Update demo/playground scripts [\#2562](https://github.com/hyperledger/aries-cloudagent-python/pull/2562) [usingtechnology](https://github.com/usingtechnology)
  - Update .readthedocs.yaml [\#2548](https://github.com/hyperledger/aries-cloudagent-python/pull/2548) [swcurran](https://github.com/swcurran)
  - Update .readthedocs.yaml [\#2547](https://github.com/hyperledger/aries-cloudagent-python/pull/2547) [swcurran](https://github.com/swcurran)
  - fix: correct minor typos [\#2544](https://github.com/hyperledger/aries-cloudagent-python/pull/2544) [Ennovate-com](https://github.com/Ennovate-com)
  - Update steps for Manually Creating Revocation Registries [\#2491](https://github.com/hyperledger/aries-cloudagent-python/pull/2491) [WadeBarnes](https://github.com/WadeBarnes)
- Dependencies and Internal Updates
  - chore: bump pydid version [\#2626](https://github.com/hyperledger/aries-cloudagent-python/pull/2626) [dbluhm](https://github.com/dbluhm)
  - chore: dependency updates [\#2565](https://github.com/hyperledger/aries-cloudagent-python/pull/2565) [dbluhm](https://github.com/dbluhm)
  - chore(deps): Bump urllib3 from 2.0.6 to 2.0.7  dependencies [\#2552](https://github.com/hyperledger/aries-cloudagent-python/pull/2552) [dependabot bot](https://github.com/dependabot)
  - chore(deps): Bump urllib3 from 2.0.6 to 2.0.7 in /demo/playground/scripts  dependencies [\#2551](https://github.com/hyperledger/aries-cloudagent-python/pull/2551) [dependabot bot](https://github.com/dependabot)
  - chore: update pydid [\#2527](https://github.com/hyperledger/aries-cloudagent-python/pull/2527) [dbluhm](https://github.com/dbluhm)
  - chore(deps): Bump urllib3 from 2.0.5 to 2.0.6  dependencies [\#2525](https://github.com/hyperledger/aries-cloudagent-python/pull/2525) [dependabot bot](https://github.com/dependabot)
  - chore(deps): Bump urllib3 from 2.0.2 to 2.0.6 in /demo/playground/scripts  dependencies [\#2524](https://github.com/hyperledger/aries-cloudagent-python/pull/2524) [dependabot bot](https://github.com/dependabot)
  - Avoid multiple open wallet connections [\#2521](https://github.com/hyperledger/aries-cloudagent-python/pull/2521) [andrewwhitehead](https://github.com/andrewwhitehead)
  - Remove unused dependencies [\#2510](https://github.com/hyperledger/aries-cloudagent-python/pull/2510) [andrewwhitehead](https://github.com/andrewwhitehead)
  - Use correct rust log level in dockerfiles [\#2499](https://github.com/hyperledger/aries-cloudagent-python/pull/2499) [loneil](https://github.com/loneil)
  - fix: run tests script copying local env [\#2495](https://github.com/hyperledger/aries-cloudagent-python/pull/2495) [dbluhm](https://github.com/dbluhm)
  - Update devcontainer to read version from aries-cloudagent package [\#2483](https://github.com/hyperledger/aries-cloudagent-python/pull/2483) [usingtechnology](https://github.com/usingtechnology)
  - Update Python image version to 3.9.18 [\#2456](https://github.com/hyperledger/aries-cloudagent-python/pull/2456) [WadeBarnes](https://github.com/WadeBarnes)
  - Remove old routing protocol code [\#2466](https://github.com/hyperledger/aries-cloudagent-python/pull/2466) [dbluhm](https://github.com/dbluhm)
- CI/CD, Testing, and Developer Tools/Productivity Updates
  - fix: drop asynctest  0.11.0 [\#2566](https://github.com/hyperledger/aries-cloudagent-python/pull/2566) [dbluhm](https://github.com/dbluhm)
  - Dockerfile.indy - Include aries_cloudagent code into build [\#2584](https://github.com/hyperledger/aries-cloudagent-python/pull/2584) [usingtechnology](https://github.com/usingtechnology)
  - fix: version should be set by pyproject.toml [\#2471](https://github.com/hyperledger/aries-cloudagent-python/pull/2471) [dbluhm](https://github.com/dbluhm)
  - chore: add black back in as a dev dep [\#2465](https://github.com/hyperledger/aries-cloudagent-python/pull/2465) [dbluhm](https://github.com/dbluhm)
  - Swap out flake8 in favor of Ruff [\#2438](https://github.com/hyperledger/aries-cloudagent-python/pull/2438) [dbluhm](https://github.com/dbluhm)
  - #2289 Migrate to Poetry [\#2436](https://github.com/hyperledger/aries-cloudagent-python/pull/2436) [Gavinok](https://github.com/Gavinok)
- Release management pull requests
  - 0.11.0 [\#2627](https://github.com/hyperledger/aries-cloudagent-python/pull/2627) [swcurran](https://github.com/swcurran)
  - 0.11.0rc2 [\#2613](https://github.com/hyperledger/aries-cloudagent-python/pull/2613) [swcurran](https://github.com/swcurran)
  - 0.11.0-rc1 [\#2576](https://github.com/hyperledger/aries-cloudagent-python/pull/2576) [swcurran](https://github.com/swcurran)
  - 0.11.0-rc0 [\#2575](https://github.com/hyperledger/aries-cloudagent-python/pull/2575) [swcurran](https://github.com/swcurran)

## 0.10.5

### November 21, 2023

Release 0.10.5 is a high priority patch release to correct an issue with the
handling of the JSON-LD presentation verifications, where the status of the
verification of the `presentation.proof` in the Verifiable Presentation was not
included when determining the verification value (`true` or `false`) of the
overall presentation. A forthcoming security advisory will cover the details.

Anyone using JSON-LD presentations is recommended to upgrade to this version
of ACA-Py as soon as possible.

#### 0.10.5 Categorized List of Pull Requests

- JSON-LD Credential Exchange (Issue, Present) Updates
  - fix(backport): report presentation result [\#2622](https://github.com/hyperledger/aries-cloudagent-python/pull/2622) [dbluhm](https://github.com/dbluhm)
- Release management pull requests
  - 0.10.5 [\#2623](https://github.com/hyperledger/aries-cloudagent-python/pull/2623) [swcurran](https://github.com/swcurran)

## 0.10.4

### October 9, 2023

Release 0.10.4 is a patch release to correct an issue with the handling of `did:key` routing
keys in some mediator scenarios, notably with the use of [Aries Framework Kotlin]. See the
details in the PR and [Issue \#2531 Routing for agents behind a aca-py based mediator is broken].

Thanks to [codespree](https://github.com/codespree) for raising the issue and providing the fix.

[Aries Framework Kotlin](https://github.com/hyperledger/aries-framework-kotlin)
[Issue \#2531 Routing for agents behind a aca-py based mediator is broken]: [\#2531](https://github.com/hyperledger/aries-cloudagent-python/issue/2531)

#### 0.10.4 Categorized List of Pull Requests

- DID Handling and Connection Establishment Updates/Fixes
  - fix: routing behind mediator [\#2536](https://github.com/hyperledger/aries-cloudagent-python/pull/2536) [dbluhm](https://github.com/dbluhm)
- Release management pull requests
  - 0.10.4 [\#2539](https://github.com/hyperledger/aries-cloudagent-python/pull/2539) [swcurran](https://github.com/swcurran)

## 0.10.3

### September 29, 2023

Release 0.10.3 is a patch release to add an upgrade process for very old
versions of Aries Cloud Agent Python (circa [0.5.2](#052)). If you have a long
time deployment of an issuer that uses revocation, this release could correct
internal data (tags in secure storage) related to revocation registries.
Details of the about the triggering problem can be found in [Issue \#2485].

[Issue \#2485]: https://github.com/hyperledger/aries-cloudagent-python/issue/2485

The upgrade is applied by running the following command for the ACA-Py
instance to be upgraded:

`./scripts/run_docker upgrade --force-upgrade --named-tag fix_issue_rev_reg`

#### 0.10.3 Categorized List of Pull Requests

- Credential Exchange (Issue, Present) Updates
  - Feat: Upgrade from tags and fix issue with legacy IssuerRevRegRecords [<=v0.5.2] [\#2486](https://github.com/hyperledger/aries-cloudagent-python/pull/2486) [shaangill025](https://github.com/shaangill025)
- Release management pull requests
  - 0.10.3 [\#2522](https://github.com/hyperledger/aries-cloudagent-python/pull/2522) [swcurran](https://github.com/swcurran)

## 0.10.2

### September 22, 2023

Release 0.10.2 is a patch release for 0.10.1 that addresses three specific regressions found
in deploying Release 0.10.1. The regressions are to fix:

- An ACA-Py instance upgraded to 0.10.1 that had an existing connection to another Aries agent
where the connection has both an `http` and `ws` (websocket) service endpoint with the same ID cannot
message that agent. A scenario is an ACA-Py issuer connecting to an Endorser with both `http` and
`ws` service endpoints. The updates made in 0.10.1 to improve ACA-Py DID resolution did not account
for this scenario and needed a tweak to work ([Issue \#2474], [PR \#2475]).
- The "fix revocation registry" endpoint used to fix scenarios an Issuer's local revocation registry
state is out of sync with the ledger was broken by some code being added to support a single
ACA-Py instance writing to different ledgers ([Issue \#2477], [PR \#2480]).
- The version of the [PyDID] library we were using did not handle some
unexpected DID resolution use cases encountered with mediators. The PyDID
library version dependency was updated in [PR \#2500].

[Issue \#2474]: https://github.com/hyperledger/aries-cloudagent-python/issue/2474
[PR \#2475]: https://github.com/hyperledger/aries-cloudagent-python/pull/2476
[Issue \#2477]: https://github.com/hyperledger/aries-cloudagent-python/issue/2477
[PR \#2480]: https://github.com/hyperledger/aries-cloudagent-python/pull/2480
[PyDID]: https://github.com/sicpa-dlab/pydid
[PR \#2500]: https://github.com/hyperledger/aries-cloudagent-python/pull/2500

#### 0.10.2 Categorized List of Pull Requests

- DID Handling and Connection Establishment Updates/Fixes
  - LegacyPeerDIDResolver: erroneously assigning same ID to multiple services [\#2475](https://github.com/hyperledger/aries-cloudagent-python/pull/2475) [dbluhm](https://github.com/dbluhm)
  - fix: update pydid [\#2500](https://github.com/hyperledger/aries-cloudagent-python/pull/2500) [dbluhm](https://github.com/dbluhm)
- Credential Exchange (Issue, Present) Updates
  - Bugfix: Issue with write ledger pool when performing Accumulator sync [\#2480](https://github.com/hyperledger/aries-cloudagent-python/pull/2480) [shaangill025](https://github.com/shaangill025)
- Release management pull requests
  - 0.10.2 [\#2509](https://github.com/hyperledger/aries-cloudagent-python/pull/2509) [swcurran](https://github.com/swcurran)
  - 0.10.2-rc0 [\#2484](https://github.com/hyperledger/aries-cloudagent-python/pull/2484) [swcurran](https://github.com/swcurran)
  - 0.10.2 Patch Release - fix issue #2475, #2477 [\#2482](https://github.com/hyperledger/aries-cloudagent-python/pull/2480) [shaangill025](https://github.com/shaangill025)

## 0.10.1

### August 29, 2023

Release 0.10.1 contains a breaking change, an important fix for a regression
introduced in 0.8.2 that impacts certain deployments, and a number of fixes and
updates. Included in the updates is a significant internal reorganization of the
DID and connection management code that was done to enable more flexible uses of
different DID Methods, such as being able to use `did:web` DIDs for DIDComm
messaging connections. The work also paves the way for coming updates related to
support for `did:peer` DIDs for DIDComm. For details on the change see
[PR \#2409], which includes some of the best pull request documentation ever
created.

Release 0.10.1 has the same contents as 0.10.0. An error on PyPi prevented the
0.10.0 release from being properly uploaded because of an existing file of the same
name. We immediately released 0.10.1 as a replacement.

[PR \#2409]: https://github.com/hyperledger/aries-cloudagent-python/pull/2409

The regression fix is for ACA-Py deployments that use multi-use invitations but
do **NOT** use the `--auto-accept-connection-requests` flag/processing. A change
in [0.8.2](#082) (PR [\#2223]) suppressed an extra webhook event firing during
the processing after receiving a connection request. An unexpected side effect
of that change was that the subsequent webhook event also did not fire, and as a
result, the controller did not get any event signalling a new connection request
had been received via the multi-use invitation. The update in this release
ensures the proper event fires and the controller receives the webhook.

[\#2413]: https://github.com/hyperledger/aries-cloudagent-python/pull/2413
[\#2223]: https://github.com/hyperledger/aries-cloudagent-python/pull/2223

See below for the breaking changes and a categorized list of the pull requests
included in this release.

Updates in the CI/CD area include adding the publishing of a `nightly` container
image that includes any changes in the main branch since the last `nightly` was
published. This allows getting the "latest and greatest" code via a container image
vs. having to install ACA-Py from the repository. In addition, Snyk scanning
was added to the CI pipeline, and Indy SDK tests were removed from the pipeline.

### 0.10.1 Breaking Changes

[\#2352] is a breaking change related to the storage of presentation exchange
records in ACA-Py. In previous releases, presentation exchange protocol state
data records were retained in ACA-Py secure storage after the completion of
protocol instances. With this release the default behavior changes to **deleting
those records by default**, unless the `----preserve-exchange-records` flag is
set in the configuration. This extends the use of that flag that previously
applied only to issue credential records. The extension matches the initial
intention of the flag--that it cover both issue credential and present proof
exchanges. The "best practices" for ACA-Py is that the controller (business
logic) store any long-lasting business information needed for the service that
is using the Aries Agent, and ACA-Py storage should be used only for data
necessary for the operation of the agent. In particular, protocol state data
should be held in ACA-Py only as long as the protocol is running (as it is
needed by ACA-Py), and once a protocol instance completes, the controller should
extract and store the business information from the protocol state before it is
deleted from ACA-Py storage.

[\#2352]: https://github.com/hyperledger/aries-cloudagent-python/pull/2352

#### 0.10.0 Categorized List of Pull Requests

- DIDComm Messaging Improvements/Fixes
  - fix: outbound send status missing on path [\#2393](https://github.com/hyperledger/aries-cloudagent-python/pull/2393) [dbluhm](https://github.com/dbluhm)
  - fix: keylist update response race condition [\#2391](https://github.com/hyperledger/aries-cloudagent-python/pull/2391) [dbluhm](https://github.com/dbluhm)
- DID Handling and Connection Establishment Updates/Fixes
  - fix: handle stored afgo and findy docs in corrections [\#2450](https://github.com/hyperledger/aries-cloudagent-python/pull/2450) [dbluhm](https://github.com/dbluhm)
  - chore: relax connections filter DID format [\#2451](https://github.com/hyperledger/aries-cloudagent-python/pull/2451) [chumbert](https://github.com/chumbert)
  - fix: ignore duplicate record errors on add key [\#2447](https://github.com/hyperledger/aries-cloudagent-python/pull/2447) [dbluhm](https://github.com/dbluhm)
  - fix: ignore duplicate record errors on add key [\#2447](https://github.com/hyperledger/aries-cloudagent-python/pull/2447) [dbluhm](https://github.com/dbluhm)
  - fix: more diddoc corrections [\#2446](https://github.com/hyperledger/aries-cloudagent-python/pull/2446) [dbluhm](https://github.com/dbluhm)
  - feat: resolve connection targets and permit connecting via public DID [\#2409](https://github.com/hyperledger/aries-cloudagent-python/pull/2409) [dbluhm](https://github.com/dbluhm)
  - feat: add legacy peer did resolver [\#2404](https://github.com/hyperledger/aries-cloudagent-python/pull/2404) [dbluhm](https://github.com/dbluhm)
  - Fix: Ensure event/webhook is emitted for multi-use invitations [\#2413](https://github.com/hyperledger/aries-cloudagent-python/pull/2413) [esune](https://github.com/esune)
  - feat: add DID Exchange specific problem reports and reject endpoint [\#2394](https://github.com/hyperledger/aries-cloudagent-python/pull/2394) [dbluhm](https://github.com/dbluhm)
  - fix: additional tweaks for did:web and other methods as public DIDs [\#2392](https://github.com/hyperledger/aries-cloudagent-python/pull/2392) [dbluhm](https://github.com/dbluhm)
  - Fix empty ServiceDecorator in OobRecord causing 422 Unprocessable Entity Error [\#2362](https://github.com/hyperledger/aries-cloudagent-python/pull/2362) [ff137](https://github.com/ff137)
  - Feat: Added support for Ed25519Signature2020 signature type and Ed25519VerificationKey2020 [\#2241](https://github.com/hyperledger/aries-cloudagent-python/pull/2241) [dkulic](https://github.com/dkulic)
- Upgrading to Aries Askar Updates
  - Add symlink to /home/indy/.indy_client for backwards compatibility [\#2443](https://github.com/hyperledger/aries-cloudagent-python/pull/2443) [esune](https://github.com/esune)
- Credential Exchange (Issue, Present) Updates
  - fix: ensure request matches offer in JSON-LD exchanges, if sent [\#2341](https://github.com/hyperledger/aries-cloudagent-python/pull/2341) [dbluhm](https://github.com/dbluhm)
  - BREAKING Extend --preserve-exchange-records to include Presentation Exchange. [\#2352](https://github.com/hyperledger/aries-cloudagent-python/pull/2352) [usingtechnology](https://github.com/usingtechnology)
  - Correct the response type in send_rev_reg_def [\#2355](https://github.com/hyperledger/aries-cloudagent-python/pull/2355) [ff137](https://github.com/ff137)
- Multitenancy Updates and Fixes
  - Multitenant check endorser_info before saving [\#2395](https://github.com/hyperledger/aries-cloudagent-python/pull/2395) [usingtechnology](https://github.com/usingtechnology)
  - Feat: Support Selectable Write Ledger [\#2339](https://github.com/hyperledger/aries-cloudagent-python/pull/2339) [shaangill025](https://github.com/shaangill025)
- Other Fixes, Demo, and Documentation Fixes
  - Redis Plugins [redis_cache & redis_queue] documentation and docker related updates [\#1937](https://github.com/hyperledger/aries-cloudagent-python/pull/1937) [shaangill025](https://github.com/shaangill025)
  - Chore: fix marshmallow warnings [\#2398](https://github.com/hyperledger/aries-cloudagent-python/pull/2398) [ff137](https://github.com/ff137)
  - Upgrade pre-commit and flake8 dependencies; fix flake8 warnings [\#2399](https://github.com/hyperledger/aries-cloudagent-python/pull/2399) [ff137](https://github.com/ff137)
  - Corrected typo on mediator invitation configuration argument [\#2365](https://github.com/hyperledger/aries-cloudagent-python/pull/2365) [jorgefl0](https://github.com/jorgefl0)
  - Add workaround for ARM based macs [\#2313](https://github.com/hyperledger/aries-cloudagent-python/pull/2313) [finnformica](https://github.com/finnformica)
- Dependencies and Internal Updates
  - chore(deps): Bump certifi from 2023.5.7 to 2023.7.22 in /demo/playground/scripts dependencies [\#2354](https://github.com/hyperledger/aries-cloudagent-python/pull/2354) [dependabot bot](https://github.com/dependabot)
- CI/CD and Developer Tools/Productivity Updates
  - Fix for nightly tests failing on Python 3.10 [\#2435](https://github.com/hyperledger/aries-cloudagent-python/pull/2435) [Gavinok](https://github.com/Gavinok)
  - Don't run Snyk on forks [\#2429](https://github.com/hyperledger/aries-cloudagent-python/pull/2429) [ryjones](https://github.com/ryjones)
  - Issue #2250 Nightly publish workflow [\#2421](https://github.com/hyperledger/aries-cloudagent-python/pull/2421) [Gavinok](https://github.com/Gavinok)
  - Enable Snyk scanning [\#2418](https://github.com/hyperledger/aries-cloudagent-python/pull/2418) [ryjones](https://github.com/ryjones)
  - Remove Indy tests from workflows [\#2415](https://github.com/hyperledger/aries-cloudagent-python/pull/2415) [dbluhm](https://github.com/dbluhm)
- Release management pull requests
  - 0.10.1 [\#2454](https://github.com/hyperledger/aries-cloudagent-python/pull/2454) [swcurran](https://github.com/swcurran)
  - 0.10.0 [\#2452](https://github.com/hyperledger/aries-cloudagent-python/pull/2452) [swcurran](https://github.com/swcurran)
  - 0.10.0-rc2 [\#2448](https://github.com/hyperledger/aries-cloudagent-python/pull/2448) [swcurran](https://github.com/swcurran)
  - 0.10.0-rc1 [\#2442](https://github.com/hyperledger/aries-cloudagent-python/pull/2442) [swcurran](https://github.com/swcurran)
  - 0.10.0-rc0 [\#2414](https://github.com/hyperledger/aries-cloudagent-python/pull/2414) [swcurran](https://github.com/swcurran)

## 0.10.0

### August 29, 2023

Release 0.10.1 has the same contents as 0.10.0. An error on PyPi prevented the
0.10.0 release from being properly uploaded because of an existing file of the
same name. We immediately released 0.10.1 as a replacement.

## 0.9.0

### July 24, 2023

Release 0.9.0 is an important upgrade that changes (PR [\#2302]) the dependency
on the now archived Hyperledger Ursa project to its updated, improved
replacement, [AnonCreds CL-Signatures]. This important change is ONLY available
when using [Aries Askar] as the wallet type, which brings in both [Indy VDR] and
the CL-Signatures via the latest version of [CredX from the indy-shared-rs
repository]. The update is **NOT** available to those that are using the [Indy
SDK]. All new deployments of ACA-Py SHOULD use [Aries Askar]. Further, we
**strongly** recommend that all deployments using the [Indy SDK] with ACA-Py
upgrade their installation to use [Aries Askar] and the related components using
the migration scripts available. An [Indy SDK to Askar migration document] added
to the [aca-py.org] documentation site, and a deprecation warning added to the
ACA-Py startup.

[AnonCreds CL-Signatures]: https://github.com/hyperledger/anoncreds-rs
[Aries Askar]: https://github.com/hyperledger/aries-askar
[CredX from the indy-shared-rs repository]: https://github.com/hyperledger/indy-shared-rs
[Indy SDK]: https://github.com/hyperledger/indy-sdk
[Indy SDK to Askar migration document]: https://aca-py.org/main/deploying/IndySDKtoAskarMigration/
[aca-py.org]: https://aca-py.org

The second big change in this release is that we have upgraded the primary
Python version from 3.6 to 3.9 (PR [\#2247]). In this case, primary means that
Python 3.9 is used to run the unit and integration tests on all Pull Requests.
We also do nightly runs of the main branch using Python 3.10. As
of this release we have **dropped** Python 3.6, 3.7 and 3.8, and introduced new
dependencies that are not supported in those versions of Python. For those that
use the published ACA-Py container images, the upgrade should be easily handled.
If you are pulling ACA-Py into your own image, or a non-containerized
environment, this is a breaking change that you will need to address.

Please see the next section for all breaking changes, and the subsequent section
for a categorized list of all pull requests in this release.

### Breaking Changes

In addition to the breaking Python 3.6 to 3.9 upgrade, there are two other
breaking changes that may impact some deployments.

[\#2034] allows for additional flexibility in using public DIDs in invitations,
and adds a restriction that "implicit" invitations must be proactively enabled
using a flag (`--requests-through-public-did`). Previously, such requests
would always be accepted if `--auto-accept` was enabled, which could lead to
unexpected connections being established.

[\#2170] is a change to improve message handling in the face of delivery errors
when using a persistent queue implementation such as the [ACA-Py Redis Plugin].
If you are using the Redis plugin, you **MUST** upgrade to [Redis Plugin Release
0.1.0] in conjunction with deploying this ACA-Py release. For those using their
own persistent queue solution, see the PR [\#2170] comments for information
about changes you might need to make to your deployment.

[ACA-Py Redis Plugin]: https://github.com/bcgov/aries-acapy-plugin-redis-events
[Redis Plugin Release 0.1.0]: https://github.com/bcgov/aries-acapy-plugin-redis-events/releases/tag/v0.1.0

[\#2302]: https://github.com/hyperledger/aries-cloudagent-python/pull/2302
[\#2034]: https://github.com/hyperledger/aries-cloudagent-python/pull/2034
[\#2247]: https://github.com/hyperledger/aries-cloudagent-python/pull/2247
[\#2170]: https://github.com/hyperledger/aries-cloudagent-python/pull/2170

#### Categorized List of Pull Requests

- DIDComm Messaging Improvements/Fixes
  - BREAKING: feat: get queued outbound message in transport handle message [\#2170](https://github.com/hyperledger/aries-cloudagent-python/pull/2170) [dbluhm](https://github.com/dbluhm)
- DID Handling and Connection Establishment Updates/Fixes
  - Allow any did to be public [\#2295](https://github.com/hyperledger/aries-cloudagent-python/pull/2295) [mkempa](https://github.com/mkempa)
  - Feat: Added support for Ed25519Signature2020 signature type and Ed25519VerificationKey2020 [\#2241](https://github.com/hyperledger/aries-cloudagent-python/pull/2241) [dkulic](https://github.com/dkulic)
  - Add Goal and Goal Code to OOB and DIDex Request [\#2294](https://github.com/hyperledger/aries-cloudagent-python/pull/2294) [usingtechnology](https://github.com/usingtechnology)
  - Fix routing in set public did [\#2288](https://github.com/hyperledger/aries-cloudagent-python/pull/2288) [mkempa](https://github.com/mkempa)  - Fix: Do not replace public verkey on mediator [\#2269](https://github.com/hyperledger/aries-cloudagent-python/pull/2269) [mkempa](https://github.com/mkempa)  - BREAKING: Allow multi-use public invites and public invites with metadata [\#2034](https://github.com/hyperledger/aries-cloudagent-python/pull/2034) [mepeltier](https://github.com/mepeltier)
  - fix: public did mediator routing keys as did keys [\#1977](https://github.com/hyperledger/aries-cloudagent-python/pull/1977) [dbluhm](https://github.com/dbluhm)
- Credential Exchange (Issue, Present) Updates
  - Add revocation registry rotate to faber demo [\#2333](https://github.com/hyperledger/aries-cloudagent-python/pull/2333) [usingtechnology](https://github.com/usingtechnology)
  - Update to indy-credx 1.0 [\#2302](https://github.com/hyperledger/aries-cloudagent-python/pull/2302) [andrewwhitehead](https://github.com/andrewwhitehead)
  - feat(anoncreds): Implement automated setup of revocation [\#2292](https://github.com/hyperledger/aries-cloudagent-python/pull/2292) [dbluhm](https://github.com/dbluhm)
  - fix: schema class can set Meta.unknown [\#1885](https://github.com/hyperledger/aries-cloudagent-python/pull/1885) [dbluhm](https://github.com/dbluhm)
  - Respect auto-verify-presentation flag in present proof v1 and v2 [\#2097](https://github.com/hyperledger/aries-cloudagent-python/pull/2097) [dbluhm](https://github.com/dbluhm)
  - Feature: JWT Sign and Verify Admin Endpoints with DID Support [\#2300](https://github.com/hyperledger/aries-cloudagent-python/pull/2300) [burdettadam](https://github.com/burdettadam)
- Multitenancy Updates and Fixes
  - Fix: Track endorser and author roles in per-tenant settings [\#2331](https://github.com/hyperledger/aries-cloudagent-python/pull/2331) [shaangill025](https://github.com/shaangill025)
  - Added base wallet provisioning details to Multitenancy.md [\#2328](https://github.com/hyperledger/aries-cloudagent-python/pull/2328) [esune](https://github.com/esune)
- Other Fixes, Demo, and Documentation Fixes
  - Add more context to the ACA-Py Revocation handling documentation [\#2343](https://github.com/hyperledger/aries-cloudagent-python/pull/2343) [swcurran](https://github.com/swcurran)
  - Document the Indy SDK to Askar Migration process [\#2340](https://github.com/hyperledger/aries-cloudagent-python/pull/2340) [swcurran](https://github.com/swcurran)
  - Add revocation registry rotate to faber demo [\#2333](https://github.com/hyperledger/aries-cloudagent-python/pull/2333) [usingtechnology](https://github.com/usingtechnology)
  - chore: add indy deprecation warnings [\#2332](https://github.com/hyperledger/aries-cloudagent-python/pull/2332) [dbluhm](https://github.com/dbluhm)
  - Fix alice/faber demo execution [\#2305](https://github.com/hyperledger/aries-cloudagent-python/pull/2305) [andrewwhitehead](https://github.com/andrewwhitehead)
  - Add .indy_client folder to Askar only image. [\#2308](https://github.com/hyperledger/aries-cloudagent-python/pull/2308) [WadeBarnes](https://github.com/WadeBarnes)
  - Add build step for indy-base image in run_demo [\#2299](https://github.com/hyperledger/aries-cloudagent-python/pull/2299) [usingtechnology](https://github.com/usingtechnology)
  - Webhook over websocket clarification [\#2287](https://github.com/hyperledger/aries-cloudagent-python/pull/2287) [dbluhm](https://github.com/dbluhm)
- ACA-Py Deployment Upgrade Changes
  - Add Explicit/Offline marking mechanism for Upgrade [\#2204](https://github.com/hyperledger/aries-cloudagent-python/pull/2204) [shaangill025](https://github.com/shaangill025)
- Plugin Handling Updates
  - Feature: Add the ability to deny specific plugins from loading  0.7.4 [\#1737](https://github.com/hyperledger/aries-cloudagent-python/pull/1737) [frostyfrog](https://github.com/frostyfrog)
- Dependencies and Internal Updates
  - upgrade pyjwt to latest; introduce leeway to jwt.decodet [\#2335](https://github.com/hyperledger/aries-cloudagent-python/pull/2335) [ff137](https://github.com/ff137)
  - upgrade requests to latest [\#2336](https://github.com/hyperledger/aries-cloudagent-python/pull/2336) [ff137](https://github.com/ff137)
  - upgrade packaging to latest [\#2334](https://github.com/hyperledger/aries-cloudagent-python/pull/2334) [ff137](https://github.com/ff137)
  - chore: update PyYAML [\#2329](https://github.com/hyperledger/aries-cloudagent-python/pull/2329) [dbluhm](https://github.com/dbluhm)
  - chore(deps): Bump aiohttp from 3.8.4 to 3.8.5 in /demo/playground/scripts dependencies [\#2325](https://github.com/hyperledger/aries-cloudagent-python/pull/2325) [dependabot bot](https://github.com/dependabot)
  - ⬆️ upgrade marshmallow to latest [\#2322](https://github.com/hyperledger/aries-cloudagent-python/pull/2322) [ff137](https://github.com/ff137)
  - fix: use python 3.9 in run_docker [\#2291](https://github.com/hyperledger/aries-cloudagent-python/pull/2291) [dbluhm](https://github.com/dbluhm)
  - BREAKING!: drop python 3.6 support [\#2247](https://github.com/hyperledger/aries-cloudagent-python/pull/2247) [dbluhm](https://github.com/dbluhm)
  - Minor revisions to the README.md and DevReadMe.md [\#2272](https://github.com/hyperledger/aries-cloudagent-python/pull/2272) [swcurran](https://github.com/swcurran)
- ACA-Py Administrative Updates
  - Updating Maintainers list to be accurate and using the TOC format [\#2258](https://github.com/hyperledger/aries-cloudagent-python/pull/2258) [swcurran](https://github.com/swcurran)
- CI/CD and Developer Tools/Productivity Updates
  - Cancel in-progress workflows when PR is updated [\#2303](https://github.com/hyperledger/aries-cloudagent-python/pull/2303) [andrewwhitehead](https://github.com/andrewwhitehead)
  - ci: add gha for pr-tests [\#2058](https://github.com/hyperledger/aries-cloudagent-python/pull/2058) [dbluhm](https://github.com/dbluhm)
  - Add devcontainer for ACA-Py [\#2267](https://github.com/hyperledger/aries-cloudagent-python/pull/2267) [usingtechnology](https://github.com/usingtechnology)
  - Docker images and GHA for publishing images  help wanted [\#2076](https://github.com/hyperledger/aries-cloudagent-python/pull/2076) [dbluhm](https://github.com/dbluhm)
  - ci: test additional versions of python nightly [\#2059](https://github.com/hyperledger/aries-cloudagent-python/pull/2059) [dbluhm](https://github.com/dbluhm)
- Release management pull requests
  - 0.9.0 [\#2344](https://github.com/hyperledger/aries-cloudagent-python/pull/2344) [swcurran](https://github.com/swcurran)
  - 0.9.0-rc0 [\#2338](https://github.com/hyperledger/aries-cloudagent-python/pull/2338) [swcurran](https://github.com/swcurran)

## 0.8.2

### June 29, 2023

Release 0.8.2 contains a number of minor fixes and updates to ACA-Py, including
the correction of a regression in Release 0.8.0 related to the use of plugins
(see [\#2255]). Highlights include making it easier to use tracing in a
development environment to collect detailed performance information about what
is going in within ACA-Py.

This release pulls in [indy-shared-rs] Release 3.3 which fixes a serious issue in AnonCreds verification, as described in issue [\#2036], where the verification of a presentation with multiple revocable credentials fails when using [Aries Askar] and the
other shared components. This issue occurs only when using [Aries Askar] and [indy-credx Release 3.3].

An important new feature in this release is the ability to set some instance
configuration settings at the tenant level of a multi-tenant deployment. See PR
[\#2233].

There are no breaking changes in this release.

[\#2255]: https://github.com/hyperledger/aries-cloudagent-python/pull/2255
[\#2233]: https://github.com/hyperledger/aries-cloudagent-python/pull/2233
[\#2036]: https://github.com/hyperledger/aries-cloudagent-python/issues/2036
[indy-shared-rs]: https://github.com/hyperledger/indy-shared-rs
[Aries Askar]: https://github.com/hyperledger/aries-askar
[indy-credx Release 3.3]: https://github.com/hyperledger/indy-shared-rs/releases/tag/v0.3.3

#### Categorized List of Pull Requests

- Connections Fixes/Updates
  - Resolve definitions.py fix to fix backwards compatibility break in plugins [\#2255](https://github.com/hyperledger/aries-cloudagent-python/pull/2255) [usingtechnology](https://github.com/usingtechnology)
  - Add support for JsonWebKey2020 for the connection invitations [\#2173](https://github.com/hyperledger/aries-cloudagent-python/pull/2173) [dkulic](https://github.com/dkulic)
  - fix: only cache completed connection targets [\#2240](https://github.com/hyperledger/aries-cloudagent-python/pull/2240) [dbluhm](https://github.com/dbluhm)
  - Connection target should not be limited only to indy dids [\#2229](https://github.com/hyperledger/aries-cloudagent-python/pull/2229) [dkulic](https://github.com/dkulic)
  - Disable webhook trigger on initial response to multi-use connection invitation [\#2223](https://github.com/hyperledger/aries-cloudagent-python/pull/2223) [esune](https://github.com/esune)
- Credential Exchange (Issue, Present) Updates
  - Pass document loader to jsonld.expand [\#2175](https://github.com/hyperledger/aries-cloudagent-python/pull/2175) [andrewwhitehead](https://github.com/andrewwhitehead)
- Multi-tenancy fixes/updates
  - Allow Configuration Settings on a per-tenant basis [\#2233](https://github.com/hyperledger/aries-cloudagent-python/pull/2233) [shaangill025](https://github.com/shaangill025)
  - stand up multiple agents (single and multi) for local development and testing [\#2230](https://github.com/hyperledger/aries-cloudagent-python/pull/2230) [usingtechnology](https://github.com/usingtechnology)
  - Multi-tenant self-managed mediation verkey lookup [\#2232](https://github.com/hyperledger/aries-cloudagent-python/pull/2232) [usingtechnology](https://github.com/usingtechnology)
  - fix: route multitenant connectionless oob invitation [\#2243](https://github.com/hyperledger/aries-cloudagent-python/pull/2243) [TimoGlastra](https://github.com/TimoGlastra)
  - Fix multitenant/mediation in demo [\#2075](https://github.com/hyperledger/aries-cloudagent-python/pull/2075) [ianco](https://github.com/ianco)
- Other Bug and Documentation Fixes
  - Assign ~thread.thid with thread_id value [\#2261](https://github.com/hyperledger/aries-cloudagent-python/pull/2261) [usingtechnology](https://github.com/usingtechnology)
  - Fix: Do not replace public verkey on mediator [\#2269](https://github.com/hyperledger/aries-cloudagent-python/pull/2269) [mkempa](https://github.com/mkempa)
  - Provide an optional Profile to the verification key strategy [\#2265](https://github.com/hyperledger/aries-cloudagent-python/pull/2265) [yvgny](https://github.com/yvgny)
  - refactor: Extract verification method ID generation to a separate class [\#2235](https://github.com/hyperledger/aries-cloudagent-python/pull/2235) [yvgny](https://github.com/yvgny)
  - Create .readthedocs.yaml file [\#2268](https://github.com/hyperledger/aries-cloudagent-python/pull/2268) [swcurran](https://github.com/swcurran)
  - feat(did creation route): reject unregistered did methods [\#2262](https://github.com/hyperledger/aries-cloudagent-python/pull/2262) [chumbert](https://github.com/chumbert)
  - ./run_demo performance -c 1 --mediation --timing --trace-log [#2245](https://github.com/hyperledger/aries-cloudagent-python/pull/2245) [usingtechnology](https://github.com/usingtechnology)
  - Fix formatting and grammatical errors in different readme's [\#2222](https://github.com/hyperledger/aries-cloudagent-python/pull/2222) [ff137](https://github.com/ff137)
  - Fix broken link in README [\#2221](https://github.com/hyperledger/aries-cloudagent-python/pull/2221) [ff137](https://github.com/ff137)
  - fix: run only on main, forks ok [\#2166](https://github.com/hyperledger/aries-cloudagent-python/pull/2166) [anwalker293](https://github.com/anwalker293)
  - Update Alice Wants a JSON-LD Credential to fix invocation [\#2219](https://github.com/hyperledger/aries-cloudagent-python/pull/2219) [swcurran](https://github.com/swcurran)
- Dependencies and Internal Updates
  - Bump requests from 2.30.0 to 2.31.0 in /demo/playground/scripts dependenciesPull requests that update a dependency file [\#2238](https://github.com/hyperledger/aries-cloudagent-python/pull/2238) [dependabot bot](https://github.com/dependabot)
  - Upgrade codegen tools in scripts/generate-open-api-spec and publish Swagger 2.0 and OpenAPI 3.0 specs [\#2246](https://github.com/hyperledger/aries-cloudagent-python/pull/2246) [ff137](https://github.com/ff137)
- ACA-Py Administrative Updates
  - Propose adding Jason Sherman [usingtechnology](https://github.com/usingtechnology) as a Maintainer [\#2263](https://github.com/hyperledger/aries-cloudagent-python/pull/2263) [swcurran](https://github.com/swcurran)
  - Updating Maintainers list to be accurate and using the TOC format [\#2258](https://github.com/hyperledger/aries-cloudagent-python/pull/2258) [swcurran](https://github.com/swcurran)
- Message Tracing/Timing Updates
  - Add updated ELK stack for demos. [\#2236](https://github.com/hyperledger/aries-cloudagent-python/pull/2236) [usingtechnology](https://github.com/usingtechnology)
- Release management pull requests
  - 0.8.2 [\#2285](https://github.com/hyperledger/aries-cloudagent-python/pull/2285) [swcurran](https://github.com/swcurran)
  - 0.8.2-rc2 [\#2284](https://github.com/hyperledger/aries-cloudagent-python/pull/2283) [swcurran](https://github.com/swcurran)
  - 0.8.2-rc1 [\#2282](https://github.com/hyperledger/aries-cloudagent-python/pull/2282) [swcurran](https://github.com/swcurran)
  - 0.8.2-rc0 [\#2260](https://github.com/hyperledger/aries-cloudagent-python/pull/2260) [swcurran](https://github.com/swcurran)

## 0.8.1

### April 5, 2023

Version 0.8.1 is an urgent update to Release 0.8.0 to address an inability to
execute the `upgrade` command. The `upgrade` command is needed for 0.8.0 Pull
Request [\#2116] - "UPGRADE: Fix multi-use invitation performance", which is
useful for (at least) deployments of ACA-Py as a mediator. In the release, the
upgrade process is revamped, and documented in [Upgrading ACA-Py].

Key points about upgrading for those with production, pre-0.8.1 ACA-Py deployments:

- Upgrades now happen **automatically** on startup, when needed.
- The version of the last executed upgrade, even if it is a "no change" upgrade,
  is put into secure storage and is used to detect when future upgrades are needed.
  - Upgrades are needed when the running version is greater than the version is
    secure storage.
- If you have an existing, pre-0.8.1 deployment with many connection records,
there may be a delay in starting as an upgrade will be run that loads and saves
every connection record, updating the data in the record in the process.
  - A mechanism is to be added (see [Issue #2201]) for preventing an upgrade
  running if it should not be run automatically, and requires using the
  `upgrade` command. To date, there has been no need for this feature.
- See the [Upgrading ACA-Py] document for more details.

#### Postgres Support with Aries Askar

Recent changes to [Aries Askar] have resulted in Askar supporting Postgres
version 11 and greater. If you are on Postgres 10 or earlier and want to upgrade
to use Askar, you must migrate your database to Postgres 10.

We have also noted that in some container orchestration environments such as
[Red Hat's OpenShift] and possibly other [Kubernetes] distributions, Askar using
[Postgres] versions greater than 14 do not install correctly. Please monitor
[Issue \#2199] for an update to this limitation. We have found that Postgres 15 does
install correctly in other environments (such as in `docker compose` setups).

[\#2116]: https://github.com/hyperledger/aries-cloudagent-python/issues/2116
[Upgrading ACA-Py]: docs/deploying/UpgradingACA-Py.md
[Issue #2201]: https://github.com/hyperledger/aries-cloudagent-python/issues/2201
[Aries Askar]: https://github.com/hyperledger/aries-askar
[Red Hat's OpenShift]: https://www.openshift.com/products/container-platform/
[Kubernetes]: https://kubernetes.io/
[Postgres]: https://www.postgresql.org/
[Issue \#2199]: https://github.com/hyperledger/aries-cloudagent-python/issues/2199

#### Categorized List of Pull Requests

- Fixes for the `upgrade` Command
  - Change upgrade definition file entry from 0.8.0 to 0.8.1 [\#2203](https://github.com/hyperledger/aries-cloudagent-python/pull/2203) [swcurran](https://github.com/swcurran)
  - Add Upgrading ACA-Py document [\#2200](https://github.com/hyperledger/aries-cloudagent-python/pull/2200) [swcurran](https://github.com/swcurran)
  - Fix: Indy WalletAlreadyOpenedError during upgrade process [\#2196](https://github.com/hyperledger/aries-cloudagent-python/pull/2196) [shaangill025](https://github.com/shaangill025)
  - Fix: Resolve Upgrade Config file in Container [\#2193](https://github.com/hyperledger/aries-cloudagent-python/pull/2193) [shaangill025](https://github.com/shaangill025)
  - Update and automate ACA-Py upgrade process [\#2185](https://github.com/hyperledger/aries-cloudagent-python/pull/2185) [shaangill025](https://github.com/shaangill025)
  - Adds the upgrade command YML file to the PyPi Release [\#2179](https://github.com/hyperledger/aries-cloudagent-python/pull/2179) [swcurran](https://github.com/swcurran)
- Test and Documentation
  - 3.7 and 3.10 unittests fix [\#2187](https://github.com/hyperledger/aries-cloudagent-python/pull/2187) [Jsyro](https://github.com/Jsyro)
  - Doc update and some test scripts [\#2189](https://github.com/hyperledger/aries-cloudagent-python/pull/2189) [ianco](https://github.com/ianco)
  - Create UnitTests.md [\#2183](https://github.com/hyperledger/aries-cloudagent-python/pull/2183) [swcurran](https://github.com/swcurran)
  - Add link to recorded session about the ACA-Py Integration tests [\#2184](https://github.com/hyperledger/aries-cloudagent-python/pull/2184) [swcurran](https://github.com/swcurran)
- Release management pull requests
  - 0.8.1 [\#2207](https://github.com/hyperledger/aries-cloudagent-python/pull/2207) [swcurran](https://github.com/swcurran)
  - 0.8.1-rc2 [\#2198](https://github.com/hyperledger/aries-cloudagent-python/pull/2198) [swcurran](https://github.com/swcurran)
  - 0.8.1-rc1 [\#2194](https://github.com/hyperledger/aries-cloudagent-python/pull/2194) [swcurran](https://github.com/swcurran)
  - 0.8.1-rc0 [\#2190](https://github.com/hyperledger/aries-cloudagent-python/pull/2190) [swcurran](https://github.com/swcurran)

## 0.8.0

### March 14, 2023

0.8.0 is a breaking change that contains all updates since release 0.7.5. It
extends the previously tagged `1.0.0-rc1` release because it is not clear when
the 1.0.0 release will be finalized. Many of the PRs in this release were previously
included in the `1.0.0-rc1` release. The categorized list of PRs separates those
that are new from those in the `1.0.0-rc1` release candidate.

There are not a lot of new Aries Framework features in this release, as the
focus has been on cleanup and optimization. The biggest addition is the
inclusion with ACA-Py of a universal resolver interface, allowing an instance to
have both local resolvers for some DID Methods and a call out to an external
universal resolver for other DID Methods. Another significant new capability is
full support for Hyperledger Indy transaction endorsement for Authors and
Endorsers. A new repo
[aries-endorser-service](https://github.com/hyperledger/aries-endorser-service)
has been created that is a pre-configured instance of ACA-Py for use as an
Endorser service.

A recently completed feature that is outside of ACA-Py is a script to migrate
existing ACA-Py storage from Indy SDK format to Aries Askar format. This
enables existing deployments to switch to using the newer Aries Askar
components. For details see the converter in the
[aries-acapy-tools](https://github.com/hyperledger/aries-acapy-tools) repository.

#### Container Publishing Updated

With this release, a new automated process publishes container images in the
Hyperledger container image repository. New images for the release are
automatically published by the GitHubAction Workflows: [publish.yml] and
[publish-indy.yml]. The actions are triggered when a release is tagged, so no
manual action is needed. The images are published in the [Hyperledger Package
Repository under aries-cloudagent-python] and a link to the packages added to
the repositories main page (under "Packages"). Additional information about the
container image publication process can be found in the document [Container
Images and Github Actions].

The ACA-Py container images are based on [Python 3.6 and 3.9 `slim-bullseye`
images](https://hub.docker.com/_/python), and are designed to support `linux/386
(x86)`, `linux/amd64 (x64)`, and `linux/arm64`. However, for this release, the
publication of multi-architecture containers is disabled. We are working to
enable that through the updating of some dependencies that lack that capability.
There are two flavors of image built for each Python version. One contains only
the Indy/Aries Shared Libraries only ([Aries
Askar](https://github.com/hyperledger/aries-askar), [Indy
VDR](https://github.com/hyperledger/indy-vdr) and [Indy Shared
RS](https://github.com/hyperledger/indy-shared-rs), supporting only the use of
`--wallet-type askar`). The other (labelled `indy`) contains the Indy/Aries
shared libraries and the Indy SDK (considered deprecated). For new deployments,
we recommend using the Python 3.9 Shared Library images. For existing
deployments, we recommend migrating to those images.

Those currently using the container images published by [BC Gov on Docker
Hub](https://hub.docker.com/r/bcgovimages/aries-cloudagent) should change to use
those published to the [Hyperledger Package Repository under
aries-cloudagent-python].

[Hyperledger Package Repository under aries-cloudagent-python]: https://github.com/orgs/hyperledger/packages?repo_name=aries-cloudagent-python
[publish.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish.yml
[publish-indy.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish-indy.yml
[Container Images and Github Actions]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/ContainerImagesAndGithubActions.md

### Breaking Changes and Upgrades

#### PR [\#2034](https://github.com/hyperledger/aries-cloudagent-python/pull/2034) -- Implicit connections

The break impacts existing deployments that support implicit connections, those
initiated by another agent using a Public DID for this instance instead of an
explicit invitation. Such deployments need to add the configuration parameter
`--requests-through-public-did` to continue to support that feature. The use
case is that an ACA-Py instance publishes a public DID on a ledger with a
DIDComm `service` in the DIDDoc. Other agents resolve that DID, and attempt to
establish a connection with the ACA-Py instance using the `service` endpoint.
This is called an "implicit" connection in [RFC 0023 DID
Exchange](https://github.com/hyperledger/aries-rfcs/blob/main/features/0023-did-exchange/README.md).

#### PR [\#1913](https://github.com/hyperledger/aries-cloudagent-python/pull/1913) -- Unrevealed attributes in presentations

Updates the handling of "unrevealed attributes" during verification of AnonCreds
presentations, allowing them to be used in a presentation, with additional data
that can be checked if for unrevealed attributes. As few implementations of
Aries wallets support unrevealed attributes in an AnonCreds presentation, this
is unlikely to impact any deployments.

#### PR [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) - Update webhook message to terse form by default, added startup flag --debug-webhooks for full form

The default behavior in ACA-Py has been to keep the full text of all messages in
the protocol state object, and include the full protocol state object in the
webhooks sent to the controller. When the messages include an object that is
very large in all the messages, the webhook may become too big to be passed via
HTTP. For example, issuing a credential with a photo as one of the claims may
result in a number of copies of the photo in the protocol state object and
hence, very large webhooks. This change reduces the size of the webhook message
by eliminating redundant data in the protocol state of the "Issue Credential"
message as the default, and adds a new parameter to use the old behavior.

#### UPGRADE PR [\#2116](https://github.com/hyperledger/aries-cloudagent-python/pull/2116) - UPGRADE: Fix multi-use invitation performance

The way that multiuse invitations in previous versions of ACA-Py caused
performance to degrade over time. An update was made to add state into the tag
names that eliminated the need to scan the tags when querying storage for the
invitation.

If you are using multiuse invitations in your existing (pre-`0.8.0` deployment
of ACA-Py, you can run an `upgrade` to apply this change. To run upgrade from
previous versions, use the following command using the `0.8.0` version of
ACA-Py, adding you wallet settings:

`aca-py upgrade <other wallet config settings> --from-version=v0.7.5 --upgrade-config-path ./upgrade.yml`

#### Categorized List of Pull Requests

- Verifiable credential, presentation and revocation handling updates
  - **BREAKING:** Update webhook message to terse form [default, added startup flag --debug-webhooks for full form [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) by [victorlee0505](https://github.com/victorlee0505)
  - Add startup flag --light-weight-webhook to trim down outbound webhook payload [\#1941](https://github.com/hyperledger/aries-cloudagent-python/pull/1941) [victorlee0505](https://github.com/victorlee0505)
  - feat: add verification method issue-credentials-2.0/send endpoint [\#2135](https://github.com/hyperledger/aries-cloudagent-python/pull/2135) [chumbert](https://github.com/chumbert)
  - Respect auto-verify-presentation flag in present proof v1 and v2 [\#2097](https://github.com/hyperledger/aries-cloudagent-python/pull/2097) [dbluhm](https://github.com/dbluhm)
  - Feature: enabled handling VPs (request, creation, verification) with different VCs [\#1956](https://github.com/hyperledger/aries-cloudagent-python/pull/1956) ([teanas](https://github.com/teanas))
  - fix: update issue-credential endpoint summaries [\#1997](https://github.com/hyperledger/aries-cloudagent-python/pull/1997) ([PeterStrob](https://github.com/PeterStrob))
  - fix claim format designation in presentation submission [\#2013](https://github.com/hyperledger/aries-cloudagent-python/pull/2013) ([rmnre](https://github.com/rmnre))
  - \#2041 - Issue JSON-LD has invalid Admin API documentation [\#2046](https://github.com/hyperledger/aries-cloudagent-python/pull/2046) ([jfblier-amplitude](https://github.com/jfblier-amplitude))
  - Previously flagged in release 1.0.0-rc1
    - Refactor ledger correction code and insert into revocation error handling [\#1892](https://github.com/hyperledger/aries-cloudagent-python/pull/1892) ([ianco](https://github.com/ianco))
    - Indy ledger fixes and cleanups [\#1870](https://github.com/hyperledger/aries-cloudagent-python/pull/1870) ([andrewwhitehead](https://github.com/andrewwhitehead))
    - Refactoring of revocation registry creation [\#1813](https://github.com/hyperledger/aries-cloudagent-python/pull/1813) ([andrewwhitehead](https://github.com/andrewwhitehead))
    - Fix: the type of tails file path to string. [\#1925](https://github.com/hyperledger/aries-cloudagent-python/pull/1925) ([baegjae](https://github.com/baegjae))
    - Pre-populate revoc\_reg\_id on IssuerRevRegRecord [\#1924](https://github.com/hyperledger/aries-cloudagent-python/pull/1924) ([andrewwhitehead](https://github.com/andrewwhitehead))
    - Leave credentialStatus element in the LD credential [\#1921](https://github.com/hyperledger/aries-cloudagent-python/pull/1921) ([tsabolov](https://github.com/tsabolov))
    - **BREAKING:** Remove aca-py check for unrevealed revealed attrs on proof validation [\#1913](https://github.com/hyperledger/aries-cloudagent-python/pull/1913) ([ianco](https://github.com/ianco))
    - Send webhooks upon record/credential deletion [\#1906](https://github.com/hyperledger/aries-cloudagent-python/pull/1906) ([frostyfrog](https://github.com/frostyfrog))

- Out of Band (OOB) and DID Exchange / Connection Handling / Mediator
  - UPGRADE: Fix multi-use invitation performance [\#2116](https://github.com/hyperledger/aries-cloudagent-python/pull/2116) [reflectivedevelopment](https://github.com/reflectivedevelopment)
  - fix: public did mediator routing keys as did keys [\#1977](https://github.com/hyperledger/aries-cloudagent-python/pull/1977) ([dbluhm](https://github.com/dbluhm))
  - Fix for mediator load testing race condition when scaling horizontally [\#2009](https://github.com/hyperledger/aries-cloudagent-python/pull/2009) ([ianco](https://github.com/ianco))
  - **BREAKING:** Allow multi-use public invites and public invites with metadata [\#2034](https://github.com/hyperledger/aries-cloudagent-python/pull/2034) ([mepeltier](https://github.com/mepeltier))
  - Do not reject OOB invitation with unknown handshake protocol\(s\) [\#2060](https://github.com/hyperledger/aries-cloudagent-python/pull/2060) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - fix: fix connection timing bug [\#2099](https://github.com/hyperledger/aries-cloudagent-python/pull/2099) ([reflectivedevelopment](https://github.com/reflectivedevelopment))
  - Previously flagged in release 1.0.0-rc1
    - Fix: `--mediator-invitation` with OOB invitation + cleanup  [\#1970](https://github.com/hyperledger/aries-cloudagent-python/pull/1970) ([shaangill025](https://github.com/shaangill025))
    - include image\_url in oob invitation [\#1966](https://github.com/hyperledger/aries-cloudagent-python/pull/1966) ([Zzocker](https://github.com/Zzocker))
    - feat: 00B v1.1 support [\#1962](https://github.com/hyperledger/aries-cloudagent-python/pull/1962) ([shaangill025](https://github.com/shaangill025))
    - Fix: OOB - Handling of minor versions [\#1940](https://github.com/hyperledger/aries-cloudagent-python/pull/1940) ([shaangill025](https://github.com/shaangill025))
    - fix: failed connectionless proof request on some case [\#1933](https://github.com/hyperledger/aries-cloudagent-python/pull/1933) ([kukgini](https://github.com/kukgini))
    - fix: propagate endpoint from mediation record [\#1922](https://github.com/hyperledger/aries-cloudagent-python/pull/1922) ([cjhowland](https://github.com/cjhowland))
    - Feat/public did endpoints for agents behind mediators [\#1899](https://github.com/hyperledger/aries-cloudagent-python/pull/1899) ([cjhowland](https://github.com/cjhowland))

- DID Registration and Resolution related updates
  - feat: allow marking non-SOV DIDs as public [\#2144](https://github.com/hyperledger/aries-cloudagent-python/pull/2144) [chumbert](https://github.com/chumbert)
  - fix: askar exception message always displaying null DID [\#2155](https://github.com/hyperledger/aries-cloudagent-python/pull/2155) [chumbert](https://github.com/chumbert)
  - feat: enable creation of DIDs for all registered methods [\#2067](https://github.com/hyperledger/aries-cloudagent-python/pull/2067) ([chumbert](https://github.com/chumbert))
  - fix: create local DID return schema [\#2086](https://github.com/hyperledger/aries-cloudagent-python/pull/2086) ([chumbert](https://github.com/chumbert))
  - feat: universal resolver - configurable authentication [\#2095](https://github.com/hyperledger/aries-cloudagent-python/pull/2095) ([chumbert](https://github.com/chumbert))
  - Previously flagged in release 1.0.0-rc1
    - feat: add universal resolver [\#1866](https://github.com/hyperledger/aries-cloudagent-python/pull/1866) ([dbluhm](https://github.com/dbluhm))
    - fix: resolve dids following new endpoint rules [\#1863](https://github.com/hyperledger/aries-cloudagent-python/pull/1863) ([dbluhm](https://github.com/dbluhm))
    - fix: didx request cannot be accepted [\#1881](https://github.com/hyperledger/aries-cloudagent-python/pull/1881) ([rmnre](https://github.com/rmnre))
    - did method & key type registry [\#1986](https://github.com/hyperledger/aries-cloudagent-python/pull/1986) ([burdettadam](https://github.com/burdettadam))
    - Fix/endpoint attrib structure [\#1934](https://github.com/hyperledger/aries-cloudagent-python/pull/1934) ([cjhowland](https://github.com/cjhowland))
    - Simple did registry [\#1920](https://github.com/hyperledger/aries-cloudagent-python/pull/1920) ([burdettadam](https://github.com/burdettadam))
    - Use did:key for recipient keys [\#1886](https://github.com/hyperledger/aries-cloudagent-python/pull/1886) ([frostyfrog](https://github.com/frostyfrog))

- Hyperledger Indy Endorser/Author Transaction Handling
  - Update some of the demo Readme and Endorser instructions [\#2122](https://github.com/hyperledger/aries-cloudagent-python/pull/2122) [swcurran](https://github.com/swcurran)
  - Special handling for the write ledger [\#2030](https://github.com/hyperledger/aries-cloudagent-python/pull/2030) ([ianco](https://github.com/ianco))
  - Previously flagged in release 1.0.0-rc1
    - Fix/txn job setting [\#1994](https://github.com/hyperledger/aries-cloudagent-python/pull/1994) ([ianco](https://github.com/ianco))
    - chore: fix ACAPY\_PROMOTE-AUTHOR-DID flag  [\#1978](https://github.com/hyperledger/aries-cloudagent-python/pull/1978) ([morrieinmaas](https://github.com/morrieinmaas))
    - Endorser write DID transaction [\#1938](https://github.com/hyperledger/aries-cloudagent-python/pull/1938) ([ianco](https://github.com/ianco))
    - Endorser doc updates and some bug fixes [\#1926](https://github.com/hyperledger/aries-cloudagent-python/pull/1926) ([ianco](https://github.com/ianco))

- Admin API Additions
  - fix: response type on delete-tails-files endpoint [\#2133](https://github.com/hyperledger/aries-cloudagent-python/pull/2133) [chumbert](https://github.com/chumbert)
  - OpenAPI validation fixes [\#2127](https://github.com/hyperledger/aries-cloudagent-python/pull/2127) [loneil](https://github.com/loneil)
  - Delete tail files [\#2103](https://github.com/hyperledger/aries-cloudagent-python/pull/2103) [ramreddychalla94](https://github.com/ramreddychalla94)

- Startup Command Line / Environment / YAML Parameter Updates
  - Update webhook message to terse form [default, added startup flag --debug-webhooks for full form [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) by [victorlee0505](https://github.com/victorlee0505)
  - Add startup flag --light-weight-webhook to trim down outbound webhook payload [\#1941](https://github.com/hyperledger/aries-cloudagent-python/pull/1941) [victorlee0505](https://github.com/victorlee0505)
  - Add missing --mediator-connections-invite cmd arg info to docs [\#2051](https://github.com/hyperledger/aries-cloudagent-python/pull/2051) ([matrixik](https://github.com/matrixik))
  - Issue \#2068 boolean flag change to support HEAD requests to default route [\#2077](https://github.com/hyperledger/aries-cloudagent-python/pull/2077) ([johnekent](https://github.com/johnekent))
  - Previously flagged in release 1.0.0-rc1
    - Add seed command line parameter but use only if also an "allow insecure seed" parameter is set [\#1714](https://github.com/hyperledger/aries-cloudagent-python/pull/1714) ([DaevMithran](https://github.com/DaevMithran))

- Internal Aries framework data handling updates
  - fix: resolver api schema inconsistency [\#2112](https://github.com/hyperledger/aries-cloudagent-python/pull/2112) ([TimoGlastra](https://github.com/chumbert))
  - fix: return if return route but no response [\#1853](https://github.com/hyperledger/aries-cloudagent-python/pull/1853) ([TimoGlastra](https://github.com/TimoGlastra))
  - Multi-ledger/Multi-tenant issues [\#2022](https://github.com/hyperledger/aries-cloudagent-python/pull/2022) ([ianco](https://github.com/ianco))
  - fix: Correct typo in model -- required spelled incorrectly [\#2031](https://github.com/hyperledger/aries-cloudagent-python/pull/2031) ([swcurran](https://github.com/swcurran))
  - Code formatting [\#2053](https://github.com/hyperledger/aries-cloudagent-python/pull/2053) ([ianco](https://github.com/ianco))
  - Improved validation of record state attributes [\#2071](https://github.com/hyperledger/aries-cloudagent-python/pull/2071) ([rmnre](https://github.com/rmnre))
  - Previously flagged in release 1.0.0-rc1
    - fix: update RouteManager methods use to pass profile as parameter [\#1902](https://github.com/hyperledger/aries-cloudagent-python/pull/1902) ([chumbert](https://github.com/chumbert))
    - Allow fully qualified class names for profile managers [\#1880](https://github.com/hyperledger/aries-cloudagent-python/pull/1880) ([chumbert](https://github.com/chumbert))
    - fix: unable to use askar with in memory db [\#1878](https://github.com/hyperledger/aries-cloudagent-python/pull/1878) ([dbluhm](https://github.com/dbluhm))
    - Enable manually triggering keylist updates during connection [\#1851](https://github.com/hyperledger/aries-cloudagent-python/pull/1851) ([dbluhm](https://github.com/dbluhm))
    - feat: make base wallet route access configurable [\#1836](https://github.com/hyperledger/aries-cloudagent-python/pull/1836) ([dbluhm](https://github.com/dbluhm))
    - feat: event and webhook on keylist update stored [\#1769](https://github.com/hyperledger/aries-cloudagent-python/pull/1769) ([dbluhm](https://github.com/dbluhm))
    - fix: Safely shutdown when root\_profile uninitialized [\#1960](https://github.com/hyperledger/aries-cloudagent-python/pull/1960) ([frostyfrog](https://github.com/frostyfrog))
    - feat: include connection ids in keylist update webhook [\#1914](https://github.com/hyperledger/aries-cloudagent-python/pull/1914) ([dbluhm](https://github.com/dbluhm))
    - fix: incorrect response schema for discover features [\#1912](https://github.com/hyperledger/aries-cloudagent-python/pull/1912) ([dbluhm](https://github.com/dbluhm))
    - Fix: SchemasInputDescriptorFilter: broken deserialization renders generated clients unusable [\#1894](https://github.com/hyperledger/aries-cloudagent-python/pull/1894) ([rmnre](https://github.com/rmnre))
    - fix: schema class can set Meta.unknown [\#1885](https://github.com/hyperledger/aries-cloudagent-python/pull/1885) ([dbluhm](https://github.com/dbluhm))

- Unit, Integration, and Aries Agent Test Harness Test updates
  - Additional integration tests for revocation scenarios [\#2055](https://github.com/hyperledger/aries-cloudagent-python/pull/2055) ([ianco](https://github.com/ianco))
  - Previously flagged in release 1.0.0-rc1
    - Fixes a few AATH failures [\#1897](https://github.com/hyperledger/aries-cloudagent-python/pull/1897) ([ianco](https://github.com/ianco))
    - fix: warnings in tests from IndySdkProfile [\#1865](https://github.com/hyperledger/aries-cloudagent-python/pull/1865) ([dbluhm](https://github.com/dbluhm))
    - Unit test fixes for python 3.9 [\#1858](https://github.com/hyperledger/aries-cloudagent-python/pull/1858) ([andrewwhitehead](https://github.com/andrewwhitehead))
    - Update pip-audit.yml [\#1945](https://github.com/hyperledger/aries-cloudagent-python/pull/1945) ([ryjones](https://github.com/ryjones))
    - Update pip-audit.yml [\#1944](https://github.com/hyperledger/aries-cloudagent-python/pull/1944) ([ryjones](https://github.com/ryjones))

- Dependency, Python version, GitHub Actions and Container Image Changes
  - Remove CircleCI Status since we aren't using CircleCI anymore [\#2163](https://github.com/hyperledger/aries-cloudagent-python/pull/2163) [swcurran](https://github.com/swcurran)
  - Update ACA-Py docker files to produce OpenShift compatible images [\#2130](https://github.com/hyperledger/aries-cloudagent-python/pull/2130) [WadeBarnes](https://github.com/WadeBarnes)
  - Temporarily disable multi-architecture image builds [\#2125](https://github.com/hyperledger/aries-cloudagent-python/pull/2125) [WadeBarnes](https://github.com/WadeBarnes)
  - Fix ACA-py image builds [\#2123](https://github.com/hyperledger/aries-cloudagent-python/pull/2123) [WadeBarnes](https://github.com/WadeBarnes)
  - Fix publish workflows [\#2117](https://github.com/hyperledger/aries-cloudagent-python/pull/2117) [WadeBarnes](https://github.com/WadeBarnes)
  - fix: indy dependency version format [\#2054](https://github.com/hyperledger/aries-cloudagent-python/pull/2054) ([chumbert](https://github.com/chumbert))
  - ci: add gha for pr-tests [\#2058](https://github.com/hyperledger/aries-cloudagent-python/pull/2058) ([dbluhm](https://github.com/dbluhm))
  - ci: test additional versions of python nightly [\#2059](https://github.com/hyperledger/aries-cloudagent-python/pull/2059) ([dbluhm](https://github.com/dbluhm))
  - Update github actions dependencies \(for node16 support\) [\#2066](https://github.com/hyperledger/aries-cloudagent-python/pull/2066) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Docker images and GHA for publishing images [\#2076](https://github.com/hyperledger/aries-cloudagent-python/pull/2076) ([dbluhm](https://github.com/dbluhm))
  - Update dockerfiles to use python 3.9 [\#2109](https://github.com/hyperledger/aries-cloudagent-python/pull/2109) ([ianco](https://github.com/ianco))
  - Updating base images from slim-buster to slim-bullseye [\#2105](https://github.com/hyperledger/aries-cloudagent-python/pull/2105) ([pradeepp88](https://github.com/pradeepp88))
  - Previously flagged in release 1.0.0-rc1
    - feat: update pynacl version from 1.4.0 to 1.50 [\#1981](https://github.com/hyperledger/aries-cloudagent-python/pull/1981) ([morrieinmaas](https://github.com/morrieinmaas))
    - Fix: web.py dependency - integration tests & demos [\#1973](https://github.com/hyperledger/aries-cloudagent-python/pull/1973) ([shaangill025](https://github.com/shaangill025))
    - chore: update pydid [\#1915](https://github.com/hyperledger/aries-cloudagent-python/pull/1915) ([dbluhm](https://github.com/dbluhm))

- Demo and Documentation Updates
  - [fix] Removes extra comma that prevents swagger from accepting the presentation request [\#2149](https://github.com/hyperledger/aries-cloudagent-python/pull/2149) [swcurran](https://github.com/swcurran)
  - Initial plugin docs [\#2138](https://github.com/hyperledger/aries-cloudagent-python/pull/2138) [ianco](https://github.com/ianco)
  - Acme workshop [\#2137](https://github.com/hyperledger/aries-cloudagent-python/pull/2137) [ianco](https://github.com/ianco)
  - Fix: Performance Demo [no --revocation] [\#2151](https://github.com/hyperledger/aries-cloudagent-python/pull/2151) [shaangill025](https://github.com/shaangill025)
  - Fix typos in alice-local.sh & faber-local.sh [\#2010](https://github.com/hyperledger/aries-cloudagent-python/pull/2010) ([naonishijima](https://github.com/naonishijima))
  - Added a bit about manually creating a revoc reg tails file [\#2012](https://github.com/hyperledger/aries-cloudagent-python/pull/2012) ([ianco](https://github.com/ianco))
  - Add ability to set docker container name [\#2024](https://github.com/hyperledger/aries-cloudagent-python/pull/2024) ([matrixik](https://github.com/matrixik))
  - Doc updates for json demo [\#2026](https://github.com/hyperledger/aries-cloudagent-python/pull/2026) ([ianco](https://github.com/ianco))
  - Multitenancy demo \(docker-compose with postgres and ngrok\) [\#2089](https://github.com/hyperledger/aries-cloudagent-python/pull/2089) ([ianco](https://github.com/ianco))
  - Allow using YAML configuration file with run\_docker [\#2091](https://github.com/hyperledger/aries-cloudagent-python/pull/2091) ([matrixik](https://github.com/matrixik))
  - Previously flagged in release 1.0.0-rc1
    - Fixes to acme exercise code [\#1990](https://github.com/hyperledger/aries-cloudagent-python/pull/1990) ([ianco](https://github.com/ianco))
    - Fixed bug in run\_demo script [\#1982](https://github.com/hyperledger/aries-cloudagent-python/pull/1982) ([pasquale95](https://github.com/pasquale95))
    - Transaction Author with Endorser demo [\#1975](https://github.com/hyperledger/aries-cloudagent-python/pull/1975) ([ianco](https://github.com/ianco))
    - Redis Plugins \[redis\_cache & redis\_queue\] related updates [\#1937](https://github.com/hyperledger/aries-cloudagent-python/pull/1937) ([shaangill025](https://github.com/shaangill025))

- Release management pull requests
  - 0.8.0 release [\#2169](https://github.com/hyperledger/aries-cloudagent-python/pull/2169) ([swcurran](https://github.com/swcurran))
  - 0.8.0-rc0 release updates [\#2115](https://github.com/hyperledger/aries-cloudagent-python/pull/2115) ([swcurran](https://github.com/swcurran))
  - Previously flagged in release 1.0.0-rc1
    - Release 1.0.0-rc0 [\#1904](https://github.com/hyperledger/aries-cloudagent-python/pull/1904) ([swcurran](https://github.com/swcurran))
    - Add 0.7.5 patch Changelog entry to main branch Changelog [\#1996](https://github.com/hyperledger/aries-cloudagent-python/pull/1996) ([swcurran](https://github.com/swcurran))
    - Release 1.0.0-rc1 [\#2005](https://github.com/hyperledger/aries-cloudagent-python/pull/2005) ([swcurran](https://github.com/swcurran))

## 0.7.5

### October 26, 2022

0.7.5 is a patch release to deal primarily to add [PR #1881 DID Exchange in
ACA-Py 0.7.4 with explicit invitations and without auto-accept
broken](https://github.com/hyperledger/aries-cloudagent-python/pull/1881). A
couple of other PRs were added to the release, as listed below, and in
[Milestone 0.7.5](https://github.com/hyperledger/aries-cloudagent-python/milestone/6).

#### List of Pull Requests

- Changelog and version updates for version 0.7.5-rc1 [\#1985](https://github.com/hyperledger/aries-cloudagent-python/pull/1985) ([swcurran](https://github.com/swcurran))
- Endorser doc updates and some bug fixes [\#1926](https://github.com/hyperledger/aries-cloudagent-python/pull/1926) ([ianco](https://github.com/ianco))
- Fix: web.py dependency - integration tests & demos [\#1973](https://github.com/hyperledger/aries-cloudagent-python/pull/1973) ([shaangill025](https://github.com/shaangill025))
- Endorser write DID transaction [\#1938](https://github.com/hyperledger/aries-cloudagent-python/pull/1938) ([ianco](https://github.com/ianco))
- fix: didx request cannot be accepted [\#1881](https://github.com/hyperledger/aries-cloudagent-python/pull/1881) ([rmnre](https://github.com/rmnre))
- Fix: OOB - Handling of minor versions [\#1940](https://github.com/hyperledger/aries-cloudagent-python/pull/1940) ([shaangill025](https://github.com/shaangill025))
- fix: Safely shutdown when root_profile uninitialized [\#1960](https://github.com/hyperledger/aries-cloudagent-python/pull/1960) ([frostyfrog](https://github.com/frostyfrog))
- feat: 00B v1.1 support [\#1962](https://github.com/hyperledger/aries-cloudagent-python/pull/1962) ([shaangill025](https://github.com/shaangill025))
- 0.7.5 Cherry Picks [\#1967](https://github.com/hyperledger/aries-cloudagent-python/pull/1967) ([frostyfrog](https://github.com/frostyfrog))
- Changelog and version updates for version 0.7.5-rc0 [\#1969](https://github.com/hyperledger/aries-cloudagent-python/pull/1969) ([swcurran](https://github.com/swcurran))
- Final 0.7.5 changes [\#1991](https://github.com/hyperledger/aries-cloudagent-python/pull/1991) ([swcurran](https://github.com/swcurran))

## 0.7.4

### June 30, 2022

> :warning: **Existing multitenant JWTs invalidated when a new JWT is
generated**: If you have a pre-existing implementation with existing Admin API
authorization JWTs, invoking the endpoint to get a JWT now invalidates the
existing JWT. Previously an identical JWT would be created. Please see this
[comment on PR \#1725](https://github.com/hyperledger/aries-cloudagent-python/pull/1725#issuecomment-1096172144)
for more details.

0.7.4 is a significant release focused on stability and production deployments.
As the "patch" release number indicates, there were no breaking changes in the
Admin API, but a huge volume of updates and improvements.  Highlights of this
release include:

- A major performance and stability improvement resulting from the now
recommended use of [Aries Askar](https://github.com/bcgov/aries-askar) instead
of the Indy-SDK.
- There are significant improvements and tools for dealing with
revocation-related issues.
- A lot of work has been on the handling of Hyperledger Indy transaction
endorsements.
- ACA-Py now has a pluggable persistent queues mechanism in place, with Redis
and Kafka support available (albeit with work still to come on documentation).

In addition, there are a significant number of general enhancements, bug fixes,
documentation updates and code management improvements.

This release is a reflection of the many groups stressing ACA-Py in production
environments, reporting issues and the resulting solutions. We also have a very
large number of contributors to ACA-Py, with this release having PRs from 22
different individuals. A big thank you to all of those using ACA-Py, raising
issues and providing solutions.

#### Major Enhancements

A lot of work has been put into this release related to performance and load
testing, with significant updates being made to the key "shared component"
ACA-Py dependencies ([Aries Askar](https://github.com/bcgov/aries-askar), [Indy
VDR](https://github.comyperledger/indy-vdr)) and [Indy Shared RS (including
CredX)](https://github.com/hyperledger/indy-shared-rs). We now recommend using
those components (by using `--wallet-type askar` in the ACA-Py startup
parameters) for new ACA-Py deployments. A wallet migration tool from indy-sdk
storage to Askar storage is still needed before migrating existing deployment to
Askar. A big thanks to those creating/reporting on stress test scenarios, and
especially the team at LISSI for creating the
[aries-cloudagent-loadgenerator](https://github.com/lissi-id/aries-cloudagent-loadgenerator)
to make load testing so easy! And of course to the core ACA-Py team for
addressing the findings.

The largest enhancement is in the area of the endorsing of Hyperledger Indy
ledger transactions, enabling an instance of ACA-Py to act as an Endorser for
Indy authors needing endorsements to write objects to an Indy ledger. We're
working on an [Aries Endorser
Service](https://github.com/bcgov/aries-endorser-service) based on the new
capabilities in ACA-Py, an Endorser to be easily operated by an organization,
ideally with a controller starter kit supporting a basic human and automated
approvals business workflow. Contributions welcome!

A focus towards the end of the 0.7.4 development and release cycle was on the
handling of AnonCreds revocation in ACA-Py. Most important, a production issue
was uncovered where by an ACA-Py issuer's local Revocation Registry data could
get out of sync with what was published on an Indy ledger, resulting in an
inability to publish new RevRegEntry transactions -- making new revocations
impossible. As a result, we have added some new endpoints to enable an update to
the RevReg storage such that RevRegEntry transactions can again be published to
the ledger. Other changes were added related to revocation in general
and in the handling of tails files in particular.

The team has worked a lot on evolving the persistent queue (PQ) approach
available in ACA-Py. We have landed on a design for the queues for inbound and
outbound messages using a default in-memory implementation, and the ability to
replace the default method with implementations created via an ACA-Py plugin.
There are two concrete, out-of-the-box external persistent queuing solutions
available for [Redis](https://github.com/bcgov/aries-acapy-plugin-redis-events)
and [Kafka](https://github.com/sicpa-dlab/aries-acapy-plugin-kafka-events).
Those ACA-Py persistent queue implementation repositories will soon be migrated
to the Aries project within the Hyperledger Foundation's GitHub organization.
Anyone else can implement their own queuing plugin as long as it uses the same
interface.

Several new ways to control ACA-Py configurations were added, including new
startup parameters, Admin API parameters to control instances of protocols, and
additional web hook notifications.

A number of fixes were made to the Credential Exchange protocols, both for V1
and V2, and for both AnonCreds and W3C format VCs. Nothing new was added and
there no changes in the APIs.

As well there were a number of internal fixes, dependency updates, documentation
and demo changes, developer tools and release management updates. All the usual
stuff needed for a healthy, growing codebase.

#### Categorized List of Pull Requests

- Hyperledger Indy Endorser related updates:
  - Fix order of operations connecting faber to endorser [\#1716](https://github.com/hyperledger/aries-cloudagent-python/pull/1716) ([ianco](https://github.com/ianco))
  - Endorser support for updating DID endpoints on ledger [\#1696](https://github.com/hyperledger/aries-cloudagent-python/pull/1696) ([frostyfrog](https://github.com/frostyfrog))
  - Add "sent" key to both Schema and Cred Defs when using Endorsers [\#1663](https://github.com/hyperledger/aries-cloudagent-python/pull/1663) ([frostyfrog](https://github.com/frostyfrog))
  - Add cred_def_id to metadata when using an Endorser [\#1655](https://github.com/hyperledger/aries-cloudagent-python/pull/1655) ([frostyfrog](https://github.com/frostyfrog))
  - Update Endorser documentation [\#1646](https://github.com/hyperledger/aries-cloudagent-python/pull/1646) ([chumbert](https://github.com/chumbert))
  - Auto-promote author did to public after endorsing [\#1607](https://github.com/hyperledger/aries-cloudagent-python/pull/1607) ([ianco](https://github.com/ianco))
  - DID updates for endorser [\#1601](https://github.com/hyperledger/aries-cloudagent-python/pull/1601) ([ianco](https://github.com/ianco))
  - Qualify did exch connection lookup by role [\#1670](https://github.com/hyperledger/aries-cloudagent-python/pull/1670) ([ianco](https://github.com/ianco))
  - Use provided connection_id if provided [\#1726](https://github.com/hyperledger/aries-cloudagent-python/pull/1726) ([ianco](https://github.com/ianco))

- Additions to the startup parameters, Admin API and Web Hooks
  - Improve typing of settings and add plugin settings object [\#1833](https://github.com/hyperledger/aries-cloudagent-python/pull/1833) ([dbluhm](https://github.com/dbluhm))
  - feat: accept taa using startup parameter --accept-taa [\#1643](https://github.com/hyperledger/aries-cloudagent-python/pull/1643) ([TimoGlastra](https://github.com/TimoGlastra))
  - Add auto_verify flag in present-proof protocol [\#1702](https://github.com/hyperledger/aries-cloudagent-python/pull/1702) ([DaevMithran](https://github.com/DaevMithran))
  - feat: query connections by their_public_did [\#1637](https://github.com/hyperledger/aries-cloudagent-python/pull/1637) ([TimoGlastra](https://github.com/TimoGlastra))
  - feat: enable webhook events for mediation records [\#1614](https://github.com/hyperledger/aries-cloudagent-python/pull/1614) ([TimoGlastra](https://github.com/TimoGlastra))
  - Feature/undelivered events [\#1694](https://github.com/hyperledger/aries-cloudagent-python/pull/1694) ([mepeltier](https://github.com/mepeltier))
  - Allow use of SEED when creating local wallet DID Issue-1682 Issue-1682 [\#1705](https://github.com/hyperledger/aries-cloudagent-python/pull/1705) ([DaevMithran](https://github.com/DaevMithran))
  - Feature: Add the ability to deny specific plugins from loading [\#1737](https://github.com/hyperledger/aries-cloudagent-python/pull/1737) ([frostyfrog](https://github.com/frostyfrog))
  - feat: Add filter param to connection list for invitations [\#1797](https://github.com/hyperledger/aries-cloudagent-python/pull/1797) ([frostyfrog](https://github.com/frostyfrog))
  - Fix missing webhook handler [\#1816](https://github.com/hyperledger/aries-cloudagent-python/pull/1816) ([ianco](https://github.com/ianco))

- Persistent Queues
  - Redis PQ Cleanup in preparation for enabling the uses of plugin PQ implementations \[Issue\#1659\] [\#1659](https://github.com/hyperledger/aries-cloudagent-python/pull/1690) ([shaangill025](https://github.com/shaangill025))

- Credential Revocation and Tails File Handling
  - Fix handling of non-revocable credential when timestamp is specified \(askar/credx\) [\#1847](https://github.com/hyperledger/aries-cloudagent-python/pull/1847) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Additional endpoints to get revocation details and fix "published" status [\#1783](https://github.com/hyperledger/aries-cloudagent-python/pull/1783) ([ianco](https://github.com/ianco))
  - Fix IssuerCredRevRecord state update on revocation publish [\#1827](https://github.com/hyperledger/aries-cloudagent-python/pull/1827) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix put_file when the server returns a redirect [\#1808](https://github.com/hyperledger/aries-cloudagent-python/pull/1808) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Adjust revocation registry update procedure to shorten transactions [\#1804](https://github.com/hyperledger/aries-cloudagent-python/pull/1804) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - fix: Resolve Revocation Notification environment variable name collision [\#1751](https://github.com/hyperledger/aries-cloudagent-python/pull/1751) ([frostyfrog](https://github.com/frostyfrog))
  - fix: always notify if revocation notification record exists [\#1665](https://github.com/hyperledger/aries-cloudagent-python/pull/1665) ([TimoGlastra](https://github.com/TimoGlastra))
  - Fix for AnonCreds non-revoc proof with no timestamp [\#1628](https://github.com/hyperledger/aries-cloudagent-python/pull/1628) ([ianco](https://github.com/ianco))
  - Fixes for v7.3.0 - Issue [\#1597](https://github.com/hyperledger/aries-cloudagent-python/issues/1597) [\#1711](https://github.com/hyperledger/aries-cloudagent-python/pull/1711) ([shaangill025](https://github.com/shaangill025))
    - Fixes Issue 1 from [\#1597](https://github.com/hyperledger/aries-cloudagent-python/issues/1597): Tails file upload fails when a credDef is created and multi ledger support is enabled
  - Fix tails server upload multi-ledger mode [\#1785](https://github.com/hyperledger/aries-cloudagent-python/pull/1785) ([ianco](https://github.com/ianco))
  - Feat/revocation notification v2 [\#1734](https://github.com/hyperledger/aries-cloudagent-python/pull/1734) ([frostyfrog](https://github.com/frostyfrog))

- Issue Credential, Present Proof updates/fixes
  - Fix: Present Proof v2 - check_proof_vs_proposal update to support proof request with restrictions [\#1820](https://github.com/hyperledger/aries-cloudagent-python/pull/1820) ([shaangill025](https://github.com/shaangill025))
  - Fix: present-proof v1 send-proposal flow [\#1811](https://github.com/hyperledger/aries-cloudagent-python/pull/1811) ([shaangill025](https://github.com/shaangill025))
  - Prover - verification outcome from presentation ack message [\#1757](https://github.com/hyperledger/aries-cloudagent-python/pull/1757) ([shaangill025](https://github.com/shaangill025))
  - feat: support connectionless exchange [\#1710](https://github.com/hyperledger/aries-cloudagent-python/pull/1710) ([TimoGlastra](https://github.com/TimoGlastra))
  - Fix: DIF proof proposal when creating bound presentation request \[Issue\#1687\] [\#1690](https://github.com/hyperledger/aries-cloudagent-python/pull/1690) ([shaangill025](https://github.com/shaangill025))
  - Fix DIF PresExch and OOB request_attach delete unused connection [\#1676](https://github.com/hyperledger/aries-cloudagent-python/pull/1676) ([shaangill025](https://github.com/shaangill025))
  - Fix DIFPresFormatHandler returning invalid V20PresExRecord on presentation verification [\#1645](https://github.com/hyperledger/aries-cloudagent-python/pull/1645) ([rmnre](https://github.com/rmnre))
  - Update aries-askar patch version to at least 0.2.4 as 0.2.3 does not include backward compatibility [\#1603](https://github.com/hyperledger/aries-cloudagent-python/pull/1603) ([acuderman](https://github.com/acuderman))
  - Fixes for credential details in issue-credential webhook responses [\#1668](https://github.com/hyperledger/aries-cloudagent-python/pull/1668) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix: present-proof v2 send-proposal [issue\#1474](https://github.com/hyperledger/aries-cloudagent-python/issues/1474) [\#1667](https://github.com/hyperledger/aries-cloudagent-python/pull/1667) ([shaangill025](https://github.com/shaangill025))
    - Fixes Issue 3b from [\#1597](https://github.com/hyperledger/aries-cloudagent-python/issues/1597): V2 Credential exchange ignores the auto-respond-credential-request
  - Revert change to send_credential_ack return value [\#1660](https://github.com/hyperledger/aries-cloudagent-python/pull/1660) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix usage of send_credential_ack [\#1653](https://github.com/hyperledger/aries-cloudagent-python/pull/1653) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Replace blank credential/presentation exchange states with abandoned state [\#1605](https://github.com/hyperledger/aries-cloudagent-python/pull/1605) ([andrewwhitehead](https://github.com/andrewwhitehead))
    - Fixes Issue 4 from [\#1597](https://github.com/hyperledger/aries-cloudagent-python/issues/1597): Wallet type askar has issues when receiving V1 credentials
  - Fixes and cleanups for issue-credential 1.0 [\#1619](https://github.com/hyperledger/aries-cloudagent-python/pull/1619) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix: Duplicated schema and cred_def - Askar and Postgres [\#1800](https://github.com/hyperledger/aries-cloudagent-python/pull/1800) ([shaangill025](https://github.com/shaangill025))

- Mediator updates and fixes
  - feat: allow querying default mediator from base wallet [\#1729](https://github.com/hyperledger/aries-cloudagent-python/pull/1729) ([dbluhm](https://github.com/dbluhm))
  - Added async with for mediator record delete [\#1749](https://github.com/hyperledger/aries-cloudagent-python/pull/1749) ([dejsenlitro](https://github.com/dejsenlitro))

- Multitenacy updates and fixes
  - feat: create new JWT tokens and invalidate older for multitenancy [\#1725](https://github.com/hyperledger/aries-cloudagent-python/pull/1725) ([TimoGlastra](https://github.com/TimoGlastra))
  - Multi-tenancy stale wallet clean up [\#1692](https://github.com/hyperledger/aries-cloudagent-python/pull/1692) ([dbluhm](https://github.com/dbluhm))
  
- Dependencies and internal code updates/fixes
  - Update pyjwt to 2.4 [\#1829](https://github.com/hyperledger/aries-cloudagent-python/pull/1829) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix external Outbound Transport loading code [\#1812](https://github.com/hyperledger/aries-cloudagent-python/pull/1812) ([frostyfrog](https://github.com/frostyfrog))
  - Fix iteration over key list, update Askar to 0.2.5 [\#1740](https://github.com/hyperledger/aries-cloudagent-python/pull/1740) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Fix: update IndyLedgerRequestsExecutor logic - multitenancy and basic base wallet type  [\#1700](https://github.com/hyperledger/aries-cloudagent-python/pull/1700) ([shaangill025](https://github.com/shaangill025))
  - Move database operations inside the session context [\#1633](https://github.com/hyperledger/aries-cloudagent-python/pull/1633) ([acuderman](https://github.com/acuderman))
  - Upgrade ConfigArgParse to version 1.5.3 [\#1627](https://github.com/hyperledger/aries-cloudagent-python/pull/1627) ([WadeBarnes](https://github.com/WadeBarnes))
  - Update aiohttp dependency [\#1606](https://github.com/hyperledger/aries-cloudagent-python/pull/1606) ([acuderman](https://github.com/acuderman))
  - did-exchange implicit request pthid update & invitation key verification [\#1599](https://github.com/hyperledger/aries-cloudagent-python/pull/1599) ([shaangill025](https://github.com/shaangill025))
  - Fix auto connection response not being properly mediated [\#1638](https://github.com/hyperledger/aries-cloudagent-python/pull/1638) ([dbluhm](https://github.com/dbluhm))
  - platform target in run tests. [\#1697](https://github.com/hyperledger/aries-cloudagent-python/pull/1697) ([burdettadam](https://github.com/burdettadam))
  - Add an integration test for mixed proof with a revocable cred and a n… [\#1672](https://github.com/hyperledger/aries-cloudagent-python/pull/1672) ([ianco](https://github.com/ianco))
  - Fix: Inbound Transport is_external attribute [\#1802](https://github.com/hyperledger/aries-cloudagent-python/pull/1802) ([shaangill025](https://github.com/shaangill025))
  - fix: add a close statement to ensure session is closed on error [\#1777](https://github.com/hyperledger/aries-cloudagent-python/pull/1777) ([reflectivedevelopment](https://github.com/reflectivedevelopment))
  - Adds `transport_id` variable assignment back to outbound enqueue method [\#1776](https://github.com/hyperledger/aries-cloudagent-python/pull/1776) ([amanji](https://github.com/amanji))
  - Replace async workaround within document loader [\#1774](https://github.com/hyperledger/aries-cloudagent-python/pull/1774) ([frostyfrog](https://github.com/frostyfrog))

- Documentation and Demo Updates
  - Use default wallet type askar for alice/faber demo and bdd tests [\#1761](https://github.com/hyperledger/aries-cloudagent-python/pull/1761) ([ianco](https://github.com/ianco))
  - Update the Supported RFCs document for 0.7.4 release [\#1846](https://github.com/hyperledger/aries-cloudagent-python/pull/1846) ([swcurran](https://github.com/swcurran))
  - Fix a typo in DevReadMe.md [\#1844](https://github.com/hyperledger/aries-cloudagent-python/pull/1844) ([feknall](https://github.com/feknall))
  - Add troubleshooting document, include initial examples - ledger connection, out-of-sync RevReg [\#1818](https://github.com/hyperledger/aries-cloudagent-python/pull/1818) ([swcurran](https://github.com/swcurran))
  - Update POST /present-proof/send-request to POST /present-proof-2.0/send-request [\#1824](https://github.com/hyperledger/aries-cloudagent-python/pull/1824) ([lineko](https://github.com/lineko))
  - Fetch from --genesis-url likely to fail in composed container [\#1746](https://github.com/hyperledger/aries-cloudagent-python/pull/1739) ([tdiesler](https://github.com/tdiesler))
  - Fixes logic for web hook formatter in Faber demo [\#1739](https://github.com/hyperledger/aries-cloudagent-python/pull/1739) ([amanji](https://github.com/amanji))
  - Multitenancy Docs Update [\#1706](https://github.com/hyperledger/aries-cloudagent-python/pull/1706) ([MonolithicMonk](https://github.com/MonolithicMonk))
  - [\#1674](https://github.com/hyperledger/aries-cloudagent-python/issue/1674) Add basic DOCKER_ENV logging for run_demo [\#1675](https://github.com/hyperledger/aries-cloudagent-python/pull/1675) ([tdiesler](https://github.com/tdiesler))
  - Performance demo updates [\#1647](https://github.com/hyperledger/aries-cloudagent-python/pull/1647) ([ianco](https://github.com/ianco))
  - docs: supported features attribution [\#1654](https://github.com/hyperledger/aries-cloudagent-python/pull/1654) ([TimoGlastra](https://github.com/TimoGlastra))
  - Documentation on existing language wrappers for aca-py [\#1738](https://github.com/hyperledger/aries-cloudagent-python/pull/1738) ([etschelp](https://github.com/etschelp))
  - Document impact of multi-ledger on TAA acceptance [\#1778](https://github.com/hyperledger/aries-cloudagent-python/pull/1778) ([ianco](https://github.com/ianco))

- Code management and contributor/developer support updates
  - Set prefix for integration test demo agents; some code cleanup [\#1840](https://github.com/hyperledger/aries-cloudagent-python/pull/1840) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - Pin markupsafe at version 2.0.1 [\#1642](https://github.com/hyperledger/aries-cloudagent-python/pull/1642) ([andrewwhitehead](https://github.com/andrewwhitehead))
  - style: format with stable black release [\#1615](https://github.com/hyperledger/aries-cloudagent-python/pull/1615) ([TimoGlastra](https://github.com/TimoGlastra))
  - Remove references to play with von [\#1688](https://github.com/hyperledger/aries-cloudagent-python/pull/1688) ([ianco](https://github.com/ianco))
  - Add pre-commit as optional developer tool [\#1671](https://github.com/hyperledger/aries-cloudagent-python/pull/1671) ([dbluhm](https://github.com/dbluhm))
  - run_docker start - pass environment variables [\#1715](https://github.com/hyperledger/aries-cloudagent-python/pull/1715) ([shaangill025](https://github.com/shaangill025))
  - Use local deps only [\#1834](https://github.com/hyperledger/aries-cloudagent-python/pull/1834) ([ryjones](https://github.com/ryjones))
  - Enable pip-audit [\#1831](https://github.com/hyperledger/aries-cloudagent-python/pull/1831) ([ryjones](https://github.com/ryjones))
  - Only run pip-audit on main repo [\#1845](https://github.com/hyperledger/aries-cloudagent-python/pull/1845) ([ryjones](https://github.com/ryjones))

- Release management pull requests
  - 0.7.4 Release Changelog and version update [\#1849](https://github.com/hyperledger/aries-cloudagent-python/pull/1849) ([swcurran](https://github.com/swcurran))
  - 0.7.4-rc5 changelog, version and ReadTheDocs updates [\#1838](https://github.com/hyperledger/aries-cloudagent-python/pull/1838) ([swcurran](https://github.com/swcurran))
  - Update changelog and version for 0.7.4-rc4 [\#1830](https://github.com/hyperledger/aries-cloudagent-python/pull/1830) ([swcurran](https://github.com/swcurran))
  - Changelog, version and ReadTheDocs updates for 0.7.4-rc3 release [\#1817](https://github.com/hyperledger/aries-cloudagent-python/pull/1817) ([swcurran](https://github.com/swcurran))
  - 0.7.4-rc2 update [\#1771](https://github.com/hyperledger/aries-cloudagent-python/pull/1771) ([swcurran](https://github.com/swcurran))
  - Some ReadTheDocs File updates [\#1770](https://github.com/hyperledger/aries-cloudagent-python/pull/1770) ([swcurran](https://github.com/swcurran))
  - 0.7.4-RC1 Changelog intro paragraph - fix copy/paste error [\#1753](https://github.com/hyperledger/aries-cloudagent-python/pull/1753) ([swcurran](https://github.com/swcurran))
  - Fixing the intro paragraph and heading in the changelog of this 0.7.4RC1 [\#1752](https://github.com/hyperledger/aries-cloudagent-python/pull/1752) ([swcurran](https://github.com/swcurran))
  - Updates to Changelog for 0.7.4. RC1 release [\#1747](https://github.com/hyperledger/aries-cloudagent-python/pull/1747) ([swcurran](https://github.com/swcurran))
  - Prep for adding the 0.7.4-rc0 tag [\#1722](https://github.com/hyperledger/aries-cloudagent-python/pull/1722) ([swcurran](https://github.com/swcurran))
  - Added missed new module -- upgrade -- to the RTD generated docs [\#1593](https://github.com/hyperledger/aries-cloudagent-python/pull/1593) ([swcurran](https://github.com/swcurran))
  - Doh....update the date in the Changelog for 0.7.3 [\#1592](https://github.com/hyperledger/aries-cloudagent-python/pull/1592) ([swcurran](https://github.com/swcurran))

## 0.7.3

### January 10, 2022

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

The [Supported RFCs document](docs/features/SupportedRFCs.md) has been updated to reflect the addition of the
AIP 2.0 RFCs for which support was added.

The following is an annotated list of PRs in the release, including a link to each PR.

- **AIP 2.0 Features**
  - Discover Features Protocol: v1_0 refactoring and v2_0 implementation [#1500](https://github.com/hyperledger/aries-cloudagent-python/pull/1500)
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
  
## 0.7.2

### November 15, 2021

A mostly maintenance release with some key updates and cleanups based on community deployments and discovery.
With usage in the field increasing, we're cleaning up edge cases and issues related to volume deployments.

The most significant new feature for users of Indy ledgers is a simplified approach for transaction authors getting their transactions
signed by an endorser. Transaction author controllers now do almost nothing other than configuring their instance to use an Endorser,
and ACA-Py takes care of the rest. Documentation of that feature is [here](docs/features/Endorser.md).

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

## 0.7.1

### August 31, 2021

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

## 0.7.0

### July 14, 2021

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

## 0.6.0

### February 25, 2021

This is a significant release of ACA-Py with several new features, as well as changes to the internal architecture in order to set the groundwork for using the new shared component libraries: [indy-vdr](https://github.com/hyperledger/indy-vdr), [indy-credx](https://github.com/hyperledger/indy-shared-rs), and [aries-askar](https://github.com/hyperledger/aries-askar).

#### Mediator support

While ACA-Py had previous support for a basic routing protocol, this was never fully developed or used in practice. Starting with this release, inbound and outbound connections can be established through a mediator agent using the Aries [Mediator Coordination Protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0211-route-coordination). This work was initially contributed by Adam Burdett and Daniel Bluhm of [Indicio](https://indicio.tech/) on behalf of [SICPA](https://sicpa.com/). [Read more about mediation support](docs/features/Mediation.md).

#### Multi-Tenancy support

Started by [BMW](https://bmw.com/) and completed by [Animo Solutions](https://animo.id/) and [Anon Solutions](https://anon-solutions.ca/) on behalf of [SICPA](https://sicpa.com/), this feature allows for a single ACA-Py instance to host multiple wallet instances. This can greatly reduce the resources required when many identities are being handled. [Read more about multi-tenancy support](docs/features/Multitenancy.md).

#### New connection protocol(s)

In addition to the Aries 0160 Connections RFC, ACA-Py now supports the Aries [DID Exchange Protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0023-did-exchange) for connection establishment and reuse, as well as the Aries [Out-of-Band Protocol](https://github.com/hyperledger/aries-rfcs/tree/master/features/0434-outofband) for representing connection invitations and other pre-connection requests.

#### Issue-Credential v2

This release includes an initial implementation of the Aries [Issue Credential v2](https://github.com/hyperledger/aries-rfcs/tree/master/features/0453-issue-credential-v2) protocol.

#### Notable changes for administrators

- There are several new endpoints available for controllers as well as new startup parameters related to the multi-tenancy and mediator features, see the feature description pages above in order to make use of these features. Additional admin endpoints are introduced for the DID Exchange, Issue Credential v2, and Out-of-Band protocols.

- When running `aca-py start`, a new wallet will no longer be created unless the `--auto-provision` argument is provided. It is recommended to always use `aca-py provision` to initialize the wallet rather than relying on automatic behaviour, as this removes the need for repeatedly providing the wallet seed value (if any). This is a breaking change from previous versions.

- When running `aca-py provision`, an existing wallet will not be removed and re-created unless the `--recreate-wallet` argument is provided. This is a breaking change from previous versions.

- The logic around revocation intervals has been tightened up in accordance with [Present Proof Best Practices](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0441-present-proof-best-practices).

#### Notable changes for plugin writers

The following are breaking changes to the internal APIs which may impact Python code extensions.

- Manager classes generally accept a `Profile` instance, where previously they accepted a `RequestContext`.

- Admin request handlers now receive an `AdminRequestContext` as `app["context"]`. The current profile is available as `app["context"].profile`. The admin server now generates a unique context instance per request in order to facilitate multi-tenancy, rather than reusing the same instance for each handler.

- In order to inject the `BaseStorage` or `BaseWallet` interfaces, a `ProfileSession` must be used. Other interfaces can be injected at the `Profile` or `ProfileSession` level. This is obtained by awaiting `profile.session()` for the current `Profile` instance, or (preferably) using it as an async context manager:

```python=
async with profile.session() as session:
   storage = session.inject(BaseStorage)
```

- The `inject` method of a context is no longer `async`.

## 0.5.6

### October 19, 2020

- Fix an attempt to update the agent endpoint when configured with a read-only ledger [#758](https://github.com/hyperledger/aries-cloudagent-python/pull/758)

## 0.5.5

### October 9, 2020

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

## 0.5.4

### August 24, 2020

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

## 0.5.3

### July 23, 2020

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

## 0.5.2

### June 26, 2020

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

## 0.5.1

### April 23, 2020

- Restore previous response format for the `/credential/{id}` admin route [#474](https://github.com/hyperledger/aries-cloudagent-python/pull/474)

## 0.5.0

### April 21, 2020

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

## 0.4.5

### March 3, 2020

- Added NOTICES file with license information for dependencies [#398](https://github.com/hyperledger/aries-cloudagent-python/pull/398)
- Updated documentation for administration API demo [#397](https://github.com/hyperledger/aries-cloudagent-python/pull/397)
- Accept self-attested attributes in presentation verification, only when no restrictions are present on the requested attribute [#394](https://github.com/hyperledger/aries-cloudagent-python/pull/394), [#396](https://github.com/hyperledger/aries-cloudagent-python/pull/396)

## 0.4.4

### February 28, 2020

- Update docker image used in demo and test containers [#391](https://github.com/hyperledger/aries-cloudagent-python/pull/391)
- Fix pre-verify check on received presentations [#390](https://github.com/hyperledger/aries-cloudagent-python/pull/390)
- Do not canonicalize attribute names in credential previews [#389](https://github.com/hyperledger/aries-cloudagent-python/pull/389)

## 0.4.3

### February 26, 2020

- Fix the application of transaction author agreement acceptance to signed ledger requests [#385](https://github.com/hyperledger/aries-cloudagent-python/pull/385)
- Add a command line argument to preserve connection exchange records [#355](https://github.com/hyperledger/aries-cloudagent-python/pull/355)
- Allow custom credential IDs to be specified by the controller in the issue-credential protocol [#384](https://github.com/hyperledger/aries-cloudagent-python/pull/384)
- Handle send timeouts in the admin server websocket implementation [#377](https://github.com/hyperledger/aries-cloudagent-python/pull/377)
- [Aries RFC 0348](https://github.com/hyperledger/aries-rfcs/tree/master/features/0348-transition-msg-type-to-https): Support the 'didcomm.org' message type prefix for incoming messages [#379](https://github.com/hyperledger/aries-cloudagent-python/pull/379)
- Add support for additional postgres wallet schemes such as "MultiWalletDatabase" [#378](https://github.com/hyperledger/aries-cloudagent-python/pull/378)
- Updates to the demo agents and documentation to support demos using the OpenAPI interface [#371](https://github.com/hyperledger/aries-cloudagent-python/pull/371), [#375](https://github.com/hyperledger/aries-cloudagent-python/pull/375), [#376](https://github.com/hyperledger/aries-cloudagent-python/pull/376), [#382](https://github.com/hyperledger/aries-cloudagent-python/pull/382), [#383](https://github.com/hyperledger/aries-cloudagent-python/pull/376), [#382](https://github.com/hyperledger/aries-cloudagent-python/pull/383)
- Add a new flag for preventing writes to the ledger [#364](https://github.com/hyperledger/aries-cloudagent-python/pull/364)

## 0.4.2

### February 8, 2020

- Adjust logging on HTTP request retries [#363](https://github.com/hyperledger/aries-cloudagent-python/pull/363)
- Tweaks to `run_docker`/`run_demo` scripts for Windows [#357](https://github.com/hyperledger/aries-cloudagent-python/pull/357)
- Avoid throwing exceptions on invalid or incomplete received presentations [#359](https://github.com/hyperledger/aries-cloudagent-python/pull/359)
- Restore the `present-proof/create-request` admin endpoint for creating connectionless presentation requests [#356](https://github.com/hyperledger/aries-cloudagent-python/pull/356)
- Activate the `connections/create-static` admin endpoint for creating static connections [#354](https://github.com/hyperledger/aries-cloudagent-python/pull/354)

## 0.4.1

### January 31, 2020

- Update Forward messages and handlers to align with RFC 0094 for compatibility with libvcx and Streetcred [#240](https://github.com/hyperledger/aries-cloudagent-python/pull/240), [#349](https://github.com/hyperledger/aries-cloudagent-python/pull/349)
- Verify encoded attributes match raw attributes on proof presentation [#344](https://github.com/hyperledger/aries-cloudagent-python/pull/344)
- Improve checks for existing credential definitions in the wallet and on ledger when publishing [#333](https://github.com/hyperledger/aries-cloudagent-python/pull/333), [#346](https://github.com/hyperledger/aries-cloudagent-python/pull/346)
- Accommodate referents in presentation proposal preview attribute specifications [#333](https://github.com/hyperledger/aries-cloudagent-python/pull/333)
- Make credential proposal optional in issue-credential protocol [#336](https://github.com/hyperledger/aries-cloudagent-python/pull/336)
- Handle proofs with repeated credential definition IDs [#330](https://github.com/hyperledger/aries-cloudagent-python/pull/330)
- Allow side-loading of alternative inbound transports [#322](https://github.com/hyperledger/aries-cloudagent-python/pull/322)
- Various fixes to documentation and message schemas, and improved unit test coverage

## 0.4.0

### December 10, 2019

- Improved unit test coverage (actionmenu, basicmessage, connections, introduction, issue-credential, present-proof, routing protocols)
- Various documentation and bug fixes
- Add admin routes for fetching and accepting the ledger transaction author agreement [#144](https://github.com/hyperledger/aries-cloudagent-python/pull/144)
- Add support for receiving connection-less proof presentations [#296](https://github.com/hyperledger/aries-cloudagent-python/pull/296)
- Set attachment id explicitly in unbound proof request [#289](https://github.com/hyperledger/aries-cloudagent-python/pull/289)
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

## 0.3.5

### November 1, 2019

- Switch performance demo to the newer issue-credential protocol [#243](https://github.com/hyperledger/aries-cloudagent-python/pull/243)
- Remove old method for reusing credential requests and replace with local caching for credential offers and requests [#238](https://github.com/hyperledger/aries-cloudagent-python/pull/238), [#242](https://github.com/hyperledger/aries-cloudagent-python/pull/242)
- Add statistics on HTTP requests to timing output [#237](https://github.com/hyperledger/aries-cloudagent-python/pull/237)
- Reduce the number of tags on non-secrets records to reduce storage requirements and improve performance [#235](https://github.com/hyperledger/aries-cloudagent-python/pull/235)

## 0.3.4

### October 23, 2019

- Clean up base64 handling in wallet utils and add tests [#224](https://github.com/hyperledger/aries-cloudagent-python/pull/224)
- Support schema sequence numbers for lookups and caching and allow credential definition tag override via admin API [#223](https://github.com/hyperledger/aries-cloudagent-python/pull/223)
- Support multiple proof referents in the present-proof protocol [#222](https://github.com/hyperledger/aries-cloudagent-python/pull/222)
- Group protocol command line arguments appropriately [#217](https://github.com/hyperledger/aries-cloudagent-python/pull/217)
- Don't require a signature for get_txn_request in credential_definition_id2schema_id and reduce public DID lookups [#215](https://github.com/hyperledger/aries-cloudagent-python/pull/215)
- Add a role property to credential exchange and presentation exchange records [#214](https://github.com/hyperledger/aries-cloudagent-python/pull/214), [#218](https://github.com/hyperledger/aries-cloudagent-python/pull/218)
- Improve attachment decorator handling [#210](https://github.com/hyperledger/aries-cloudagent-python/pull/210)
- Expand and correct documentation of the OpenAPI interface [#208](https://github.com/hyperledger/aries-cloudagent-python/pull/208), [#212](https://github.com/hyperledger/aries-cloudagent-python/pull/212)

## 0.3.3

### September 27, 2019

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

## 0.3.2

### September 3, 2019

- Merge support for Aries #36 (issue-credential) and Aries #37 (present-proof) protocols [#164](https://github.com/hyperledger/aries-cloudagent-python/pull/164), [#167](https://github.com/hyperledger/aries-cloudagent-python/pull/167)
- Add `initiator` to connection record queries to ensure uniqueness in the case of a self-connection [#161](https://github.com/hyperledger/aries-cloudagent-python/pull/161)
- Add connection aliases [#149](https://github.com/hyperledger/aries-cloudagent-python/pull/149)
- Misc documentation updates

## 0.3.1

### August 15, 2019

- Do not fail with an error when no ledger is configured [#145](https://github.com/hyperledger/aries-cloudagent-python/pull/145)
- Switch to PyNaCl instead of pysodium; update dependencies [#143](https://github.com/hyperledger/aries-cloudagent-python/pull/143)
- Support reusable connection invitations [#142](https://github.com/hyperledger/aries-cloudagent-python/pull/142)
- Fix --version option and optimize Docker builds [#136](https://github.com/hyperledger/aries-cloudagent-python/pull/136)
- Add connection_id to basicmessage webhooks [#134](https://github.com/hyperledger/aries-cloudagent-python/pull/134)
- Fixes for transaction author agreements [#133](https://github.com/hyperledger/aries-cloudagent-python/pull/133)

## 0.3.0

### August 9, 2019

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

## 0.2.1

### July 16, 2019

- Add missing MANIFEST file [#78](https://github.com/hyperledger/aries-cloudagent-python/pull/78)

## 0.2.0

### July 16, 2019

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
