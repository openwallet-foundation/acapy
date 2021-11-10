# Multi-ledger in ACA-Py <!-- omit in toc -->

Ability to use multiple Indy ledgers (both IndySdk and IndyVdr) for resolving a `DID` by the ACA-Py agent. For read requests, checking of multiple ledgers in parallel is done dynamically according to logic detailed in [Read Requests Ledger Selection](#read-requests). For write requests, dynamic allocation of `write_ledger` is not supported, either it is automatically set to first configured pool (by order and preferring `production`) on startup or it can be manually updates using `get_write_ledger`, `set_write_ledger` and `reset_write_ledger` endpoints in [Multi-ledger Admin API](#multi-tenant-admin-api).

More background information including problem statement, design (algorithm) and more can be found [here](https://docs.google.com/document/d/109C_eMsuZnTnYe2OAd02jAts1vC4axwEKIq7_4dnNVA).

## Table of Contents <!-- omit in toc -->

- [Usage](#usage)
- [Multi-ledger Admin API](#multi-ledger-admin-api)
- [Ledger Selection](#ledger-selection)
  - [Read Requests](#read-requests)
  - [Write Requests](#write-requests)
- [Impact on other ACA-Py function](#impact-on-other-aca-py-function)

## Usage

Multi-ledger is disabled by default. You can enable support for multiple ledgers using the `--genesis-transactions-list` startup parameter. This parameter accepts a string which is the path to the `YAML` configuration file. For example:

`--genesis-transactions-list ./aries_cloudagent/config/multi_ledger_config.yml`

If `--genesis-transactions-list` is specified, then `--genesis-url, --genesis-file, --genesis-transactions` should not be specified.

Example config file:
```
- id: localVON
  is_production: true
  genesis_url: 'http://host.docker.internal:9000/genesis'
- id: bcorvinTest
  is_production: false
  genesis_url: 'http://test.bcovrin.vonx.io/genesis'
```

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


## Multi-ledger Admin API

Multi-ledger related actions are grouped under the `ledger` topic in the SwaggerUI or under `/ledger/multiple` path.

- `/ledger/multiple/config`:
Returns the multiple ledger configuration currently in use
- `/ledger/multiple/update-config`:
Returns the multiple ledger configuration currently in use
- `/ledger/multiple/get-write-ledger`:
Returns the current active/set `write_ledger's` `ledger_id`
- `/ledger/multiple/reset-write-ledger`:
Sets the `write_ledger` to the first configured pool (default) and return it's `ledger_id`
- `/ledger​/multiple​/set-write-ledger`:
Sets the `write_ledger` to the one which corresponds to the specified `ledger_id`

## Ledger Selection

### Read Requests

### Write Requests

## Impact on other ACA-Py function

`IndySdkLedger` was refactored by replacing `wallet: IndySdkWallet` instance variable with `profile: Profile` and accordingly `.aries_cloudagent/indy/credex/verifier`, `.aries_cloudagent/indy/models/pres_preview`, `.aries_cloudagent/indy/sdk/profile.py`, `.aries_cloudagent/indy/sdk/verifier`, `./aries_cloudagent/indy/verifier` were also updated.

Added `build_and_return_get_nym_request` and `submit_get_nym_request` helper functions to `IndySdkLedger` and `IndyVdrLedger`.

Best practice/feedback emerging from `Askar session deadlock` issue and `endorser refactoring` PR was also addressed here by not leaving sessions open unnecessarily and changing `context.session` to `context.profile.session` in `routes`. 
These changes are made here:

-test

There should be no impact/change in functionality of other ACA-Py protocols.
