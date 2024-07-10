# Upgrade via API Design

## Design Goals

To isolate an upgrade process and trigger it via API the following pattern was designed to handle multitenant scenarios. It includes an is_upgrading record in the wallet(DB) and a middleware to prevent requests during the upgrade process.

## Flow

The diagram below describes the sequence of events for the anoncreds upgrade process which it was designed, but the architecture can be used for any upgrade process.

```mermaid
sequenceDiagram
    participant A1 as Agent 1
    participant M1 as Middleware
    participant IAS1 as IsAnoncredsSingleton Set
    participant UIPS1 as UpgradeInProgressSingleton Set
    participant W as Wallet (DB)
    participant UIPS2 as UpgradeInProgressSingleton Set
    participant IAS2 as IsAnoncredsSingleton Set
    participant M2 as Middleware
    participant A2 as Agent 2

    Note over A1,A2: Start upgrade for non-anoncreds wallet
    A1->>M1: POST /anoncreds/wallet/upgrade
    M1-->>IAS1: check if wallet is in set
    IAS1-->>M1: wallet is not in set
    M1-->>UIPS1: check if wallet is in set
    UIPS1-->>M1: wallet is not in set
    M1->>A1: OK
    A1-->>W: Add is_upgrading = anoncreds_in_progress record
    A1->>A1: Upgrade wallet
    A1-->>UIPS1: Add wallet to set

    Note over A1,A2: Attempted Requests During Upgrade

    Note over A1: Attempted Request
    A1->>M1: GET /any-endpoint
    M1-->>IAS1: check if wallet is in set
    IAS1-->>M1: wallet is not in set
    M1-->>UIPS1: check if wallet is in set
    UIPS1-->>M1: wallet is in set
    M1->>A1: 503 Service Unavailable

    Note over A2: Attempted Request
    A2->>M2: GET /any-endpoint
    M2-->>IAS2: check if wallet is in set
    IAS2->>M2: wallet is not in set
    M2-->>UIPS2: check if wallet is in set
    UIPS2-->>M2: wallet is not in set
    A2-->>W: Query is_upgrading = anoncreds_in_progress record
    W-->>A2: record = anoncreds_in_progress
    A2->>A2: Loop until upgrade is finished in seperate process
    A2-->>UIPS2: Add wallet to set
    M2->>A2: 503 Service Unavailable

    Note over A1,A2: Agent Restart During Upgrade
    A1-->>W: Get is_upgrading record for wallet or all subwallets
    W-->>A1: 
    A1->>A1: Resume upgrade if in progress
    A1-->>UIPS1: Add wallet to set

    Note over A2: Same as Agent 1

    Note over A1,A2: Upgrade Completes

    Note over A1: Finish Upgrade
    A1-->>W: set is_upgrading = anoncreds_finished
    A1-->>UIPS1: Remove wallet from set
    A1-->>IAS1: Add wallet to set
    A1->>A1: update subwallet or restart

    Note over A2: Detect Upgrade Complete
    A2-->>W: Check is_upgrading = anoncreds_finished
    W-->>A2: record = anoncreds_in_progress
    A2->>A2: Wait 1 second
    A2-->>W: Check is_upgrading = anoncreds_finished
    W-->>A2: record = anoncreds_finished
    A2-->>UIPS2: Remove wallet from set
    A2-->>IAS2: Add wallet to set
    A2->>A2: update subwallet or restart

    Note over A1,A2: Restarted Agents After Upgrade

    A1-->W: Get is_upgrading record for wallet or all subwallets
    W-->>A1: 
    A1->>IAS1: Add wallet to set if record = anoncreds_finished

    Note over A2: Same as Agent 1

    Note over A1,A2: Attempted Requests After Upgrade

    Note over A1: Attempted Request
    A1->>M1: GET /any-endpoint
    M1-->>IAS1: check if wallet is in set
    IAS1-->>M1: wallet is in set
    M1-->>A1: OK

    Note over A2: Same as Agent 1
```

## Example

An example of the implementation can be found via the anoncreds upgrade components.

- `aries_cloudagent/wallet/routes.py` in the `upgrade_anoncreds` controller 
- the upgrade code in `wallet/anoncreds_upgrade.py`
- the middleware in `admin/server.py` in the `upgrade_middleware` function
- the singleton sets in `wallet/singletons.py`
- the startup process in `core/conductor.py` in the `check_for_wallet_upgrades_in_progress` function
