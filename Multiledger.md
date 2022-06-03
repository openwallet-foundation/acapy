# Multi-ledger in ACA-Py <!-- omit in toc -->

Ability to use multiple Indy ledgers (both IndySdk and IndyVdr) for resolving a `DID` by the ACA-Py agent. For read requests, checking of multiple ledgers in parallel is done dynamically according to logic detailed in [Read Requests Ledger Selection](#read-requests). For write requests, dynamic allocation of `write_ledger` is not supported. Write ledger can be assigned using `is_write` in the [configuration](#config-properties) or using any of the `--genesis-url`, `--genesis-file`, and `--genesis-transactions` startup (ACA-Py) arguments. If no write ledger is assigned then a `ConfigError` is raised.

More background information including problem statement, design (algorithm) and more can be found [here](https://docs.google.com/document/d/109C_eMsuZnTnYe2OAd02jAts1vC4axwEKIq7_4dnNVA).

## Table of Contents <!-- omit in toc -->

- [Usage](#usage)
  - [Example config file:](#example-config-file)
  - [Config properties](#config-properties)
- [Multi-ledger Admin API](#multi-ledger-admin-api)
- [Ledger Selection](#ledger-selection)
  - [Read Requests](#read-requests)
    - [For checking ledger in parallel](#for-checking-ledger-in-parallel)
  - [Write Requests](#write-requests)
- [A Special Warning for TAA Acceptance](#a-special-warning-for-taa-acceptance)
- [Impact on other ACA-Py function](#impact-on-other-aca-py-function)

## Usage

Multi-ledger is disabled by default. You can enable support for multiple ledgers using the `--genesis-transactions-list` startup parameter. This parameter accepts a string which is the path to the `YAML` configuration file. For example:

`--genesis-transactions-list ./aries_cloudagent/config/multi_ledger_config.yml`

If `--genesis-transactions-list` is specified, then `--genesis-url, --genesis-file, --genesis-transactions` should not be specified.

### Example config file:
```
- id: localVON
  is_production: false
  genesis_url: 'http://host.docker.internal:9000/genesis'
- id: bcorvinTest
  is_production: true
  is_write: true
  genesis_url: 'http://test.bcovrin.vonx.io/genesis'
```

### Config properties
For each ledger, the required properties are as following:

- `id`\*: The id (or name) of the ledger, can also be used as the pool name if none provided
- `is_production`\*: Whether the ledger is a production ledger. This is used by the pool selector algorithm to know which ledger to use for certain interactions (i.e. prefer production ledgers over non-production ledgers)
  
For connecting to ledger, one of the following needs to be specified:

- `genesis_file`: The path to the genesis file to use for connecting to an Indy ledger.
- `genesis_transactions`: String of genesis transactions to use for connecting to an Indy ledger.
- `genesis_url`: The url from which to download the genesis transactions to use for connecting to an Indy ledger.

Optional properties:
- `pool_name`: name of the indy pool to be opened
- `keepalive`: how many seconds to keep the ledger open
- `socks_proxy`
- `is_write`: Whether the ledger is the write ledger. Only one ledger can be assigned, otherwise a `ConfigError` is raised.


## Multi-ledger Admin API

Multi-ledger related actions are grouped under the `ledger` topic in the SwaggerUI or under `/ledger/multiple` path.

- `/ledger/multiple/config`:
Returns the multiple ledger configuration currently in use
- `/ledger/multiple/get-write-ledger`:
Returns the current active/set `write_ledger's` `ledger_id`

## Ledger Selection

### Read Requests

The following process is executed for these functions in ACA-Py:
1. `get_schema`
2. `get_credential_definition`
3. `get_revoc_reg_def`
4. `get_revoc_reg_entry`
5. `get_key_for_did`
6. `get_all_endpoints_for_did`
7. `get_endpoint_for_did`
8. `get_nym_role`
9. `get_revoc_reg_delta`

If multiple ledgers are configured then `IndyLedgerRequestsExecutor` service extracts `DID` from the record identifier and executes the [check](#for-checking-ledger-in-parallel) below, else it returns the `BaseLedger` instance.

#### For checking ledger in parallel

- `lookup_did_in_configured_ledgers` function
  - If the calling function (above) is in [1-4], then check the `DID` in `cache` for a corresponding applicable `ledger_id`. If found, return the ledger info, else continue.
  - Otherwise, launch parallel `_get_ledger_by_did` tasks for each of the configured ledgers.
  - As these tasks get finished, construct `applicable_prod_ledgers` and `applicable_non_prod_ledgers` dictionaries, each with `self_certified` and `non_self_certified` inner dict which are sorted by the original order or index. 
  - Order/preference for selection: `self_certified` > `production` > `non_production`
    - Checks `production` ledger where the `DID` is `self_certified`
    - Checks `non_production` ledger where the `DID` is `self_certified`
    - Checks `production` ledger where the `DID` is not `self_certified`
    - Checks `non_production` ledger where the `DID` is not `self_certified`
  - Return an applicable ledger if found, else raise an exception.
- `_get_ledger_by_did` function
  - Build and submit `GET_NYM`
  - Wait for a response for 10 seconds, if timed out return None
  - Parse response
  - Validate state proof
  - Check if `DID` is self certified
  - Returns ledger info to `lookup_did_in_configured_ledgers`

### Write Requests

On startup, the first configured applicable ledger is assigned as the `write_ledger` [`BaseLedger`], the selection is dependant on the order (top-down) and whether it is `production` or `non_production`. For instance, considering this [example configuration](#example-config-file), ledger `bcorvinTest` will be set as `write_ledger` as it is the topmost `production` ledger. If no `production` ledgers are included in configuration then the topmost `non_production` ledger is selected.

## A Special Warning for TAA Acceptance

When you run in multi-ledger mode, ACA-Py will use the `pool-name` (or `id`) specified in the ledger configuration file for each ledger.

(When running in single-ledger mode, ACA-Py uses `default` as the ledger name.)

If you are running against a ledger in `write` mode, and the ledger requires you to accept a Transaction Author Agreement (TAA), ACA-Py stores the TAA acceptance
status in the wallet in a non-secrets record, using the ledger's `pool_name` as a key.

This means that if you are upgrading from single-ledger to multi-ledger mode, you will need to *either*:

- set the `id` for your writable ledger to `default` (in your `ledgers.yaml` file)

*or*:

- re-accept the TAA once you restart your ACA-Py in multi-ledger mode

Once you re-start ACA-Py, you can check the `GET /ledger/taa` endpoint to verify your TAA acceptance status.

## Impact on other ACA-Py function

There should be no impact/change in functionality to any ACA-Py protocols.

`IndySdkLedger` was refactored by replacing `wallet: IndySdkWallet` instance variable with `profile: Profile` and accordingly `.aries_cloudagent/indy/credex/verifier`, `.aries_cloudagent/indy/models/pres_preview`, `.aries_cloudagent/indy/sdk/profile.py`, `.aries_cloudagent/indy/sdk/verifier`, `./aries_cloudagent/indy/verifier` were also updated.

Added `build_and_return_get_nym_request` and `submit_get_nym_request` helper functions to `IndySdkLedger` and `IndyVdrLedger`.

Best practice/feedback emerging from `Askar session deadlock` issue and `endorser refactoring` PR was also addressed here by not leaving sessions open unnecessarily and changing `context.session` to `context.profile.session`, etc. 

These changes are made here:
- `./aries_cloudagent/ledger/routes.py`
- `./aries_cloudagent/messaging/credential_definitions/routes.py`
- `./aries_cloudagent/messaging/schemas/routes.py`
- `./aries_cloudagent/protocols/actionmenu/v1_0/routes.py`
- `./aries_cloudagent/protocols/actionmenu/v1_0/util.py`
- `./aries_cloudagent/protocols/basicmessage/v1_0/routes.py`
- `./aries_cloudagent/protocols/coordinate_mediation/v1_0/handlers/keylist_handler.py`
- `./aries_cloudagent/protocols/coordinate_mediation/v1_0/routes.py`
- `./aries_cloudagent/protocols/endorse_transaction/v1_0/routes.py`
- `./aries_cloudagent/protocols/introduction/v0_1/handlers/invitation_handler.py`
- `./aries_cloudagent/protocols/introduction/v0_1/routes.py`
- `./aries_cloudagent/protocols/issue_credential/v1_0/handlers/credential_issue_handler.py`
- `./aries_cloudagent/protocols/issue_credential/v1_0/handlers/credential_offer_handler.py`
- `./aries_cloudagent/protocols/issue_credential/v1_0/handlers/credential_proposal_handler.py`
- `./aries_cloudagent/protocols/issue_credential/v1_0/handlers/credential_request_handler.py`
- `./aries_cloudagent/protocols/issue_credential/v1_0/routes.py`
- `./aries_cloudagent/protocols/issue_credential/v2_0/routes.py`
- `./aries_cloudagent/protocols/present_proof/v1_0/handlers/presentation_handler.py`
- `./aries_cloudagent/protocols/present_proof/v1_0/handlers/presentation_proposal_handler.py`
- `./aries_cloudagent/protocols/present_proof/v1_0/handlers/presentation_request_handler.py`
- `./aries_cloudagent/protocols/present_proof/v1_0/routes.py`
- `./aries_cloudagent/protocols/trustping/v1_0/routes.py`
- `./aries_cloudagent/resolver/routes.py`
- `./aries_cloudagent/revocation/routes.py`
