# 0.8.1

## April 5, 2023

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

### Postgres Support with Aries Askar

Recent changes to [Aries Askar] have resulted in Askar supporting Postgres
version 11 and greater. If you are on Postgres 10 or earlier and want to upgrade
to use Askar, you must migrate your database to Postgres 10.

We have also noted that in some container orchestration environments such as
[Red Hat's OpenShift] and possibly other [Kubernetes] distributions, Askar using
[Postgres] versions greater than 14 do not install correctly. Please monitor
[Issue \#2199] for an update to this limitation. We have found that Postgres 15 does
install correctly in other environments (such as in `docker compose` setups).

[\#2116]: https://github.com/hyperledger/aries-cloudagent-python/issues/2116
[Upgrading ACA-Py]: ./UpgradingACA-Py.md
[Issue #2201]: https://github.com/hyperledger/aries-cloudagent-python/issues/2201
[Aries Askar]: https://github.com/hyperledger/aries-askar
[Red Hat's OpenShift]: https://www.openshift.com/products/container-platform/
[Kubernetes]: https://kubernetes.io/
[Postgres]: https://www.postgresql.org/
[Issue \#2199]: https://github.com/hyperledger/aries-cloudagent-python/issues/2199

### Categorized List of Pull Requests

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

# 0.8.0

## March 14, 2023

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

### Container Publishing Updated

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

## Breaking Changes and Upgrades

### PR [\#2034](https://github.com/hyperledger/aries-cloudagent-python/pull/2034) -- Implicit connections

The break impacts existing deployments that support implicit connections, those
initiated by another agent using a Public DID for this instance instead of an
explicit invitation. Such deployments need to add the configuration parameter
`--requests-through-public-did` to continue to support that feature. The use
case is that an ACA-Py instance publishes a public DID on a ledger with a
DIDComm `service` in the DIDDoc. Other agents resolve that DID, and attempt to
establish a connection with the ACA-Py instance using the `service` endpoint.
This is called an "implicit" connection in [RFC 0023 DID
Exchange](https://github.com/hyperledger/aries-rfcs/blob/main/features/0023-did-exchange/README.md).

### PR [\#1913](https://github.com/hyperledger/aries-cloudagent-python/pull/1913) -- Unrevealed attributes in presentations

Updates the handling of "unrevealed attributes" during verification of AnonCreds
presentations, allowing them to be used in a presentation, with additional data
that can be checked if for unrevealed attributes. As few implementations of
Aries wallets support unrevealed attributes in an AnonCreds presentation, this
is unlikely to impact any deployments.

### PR [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) - Update webhook message to terse form by default, added startup flag --debug-webhooks for full form

The default behavior in ACA-Py has been to keep the full text of all messages in
the protocol state object, and include the full protocol state object in the
webhooks sent to the controller. When the messages include an object that is
very large in all the messages, the webhook may become too big to be passed via
HTTP. For example, issuing a credential with a photo as one of the claims may
result in a number of copies of the photo in the protocol state object and
hence, very large webhooks. This change reduces the size of the webhook message
by eliminating redundant data in the protocol state of the "Issue Credential"
message as the default, and adds a new parameter to use the old behavior.

### UPGRADE PR [\#2116](https://github.com/hyperledger/aries-cloudagent-python/pull/2116) - UPGRADE: Fix multi-use invitation performance

The way that multiuse invitations in previous versions of ACA-Py caused
performance to degrade over time. An update was made to add state into the tag
names that eliminated the need to scan the tags when querying storage for the
invitation.

If you are using multiuse invitations in your existing (pre-`0.8.0` deployment
of ACA-Py, you can run an `upgrade` to apply this change. To run upgrade from
previous versions, use the following command using the `0.8.0` version of
ACA-Py, adding you wallet settings:

`aca-py upgrade <other wallet config settings> --from-version=v0.7.5 --upgrade-config-path ./upgrade.yml`

### Categorized List of Pull Requests

- Verifiable credential, presentation and revocation handling updates
  - **BREAKING:** Update webhook message to terse form [default, added startup flag --debug-webhooks for full form [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) by [victorlee0505](victorlee0505)
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
  - Update webhook message to terse form [default, added startup flag --debug-webhooks for full form [\#2145](https://github.com/hyperledger/aries-cloudagent-python/pull/2145) by [victorlee0505](victorlee0505)
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
  - Fix: Performance Demo [no --revocation] [\#2151](https://github.com/ hyperledger/aries-cloudagent-python/pull/2151) [shaangill025](https://github.com/shaangill025)
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

# 0.7.5

## October 26, 2022

0.7.5 is a patch release to deal primarily to add [PR #1881 DID Exchange in
ACA-Py 0.7.4 with explicit invitations and without auto-accept
broken](https://github.com/hyperledger/aries-cloudagent-python/pull/1881). A
couple of other PRs were added to the release, as listed below, and in
[Milestone 0.7.5](https://github.com/hyperledger/aries-cloudagent-python/milestone/6).

### List of Pull Requests

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

# 0.7.4

## June 30, 2022

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

### Major Enhancements

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

### Categorized List of Pull Requests

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
