# Upgrade via API Design

To isolate an upgrade process and trigger it via API the following pattern was designed to handle multitenant scenarios. It includes a per instance memory singleton and an is_upgrading record in the wallet(DB) and a middleware to prevent requests during the upgrade process.

```mermaid
sequenceDiagram
    participant A as Agent
    participant M as Middleware
    participant S as Singleton
    participant W as Wallet (DB)

    Note over A: Start upgrade
    A->>M: POST /any-upgrade-path
    M-->>S: check wallet name
    S-->>M: 
    M->>A: OK
    A-->>S: add wallet name to set
    A-->>W: update is_upgrading = true for wallet or subwallet

    Note over A: Attempted Request
    A->>M: GET /any-endpoint
    M-->>S: check wallet name
    S-->>M: 
    M->>A: 503 Service Unavailable

    Note over A: Agent Restart
    A-->>W: Get is_upgrading record for wallet or all subwallets
    W-->>A: 
    A-->>S: Populate set with wallet names

    Note over A: Attempted Request
    A->>M: GET /any-endpoint
    M-->>S: check wallet name
    S-->>M: 
    M->>A: 503 Service Unavailable

    Note over A: End upgrade
    A-->>S: Remove wallet name from set
    A-->>W: delete is_upgrading record for wallet

    Note over A: Attempted Request
    A->>M: GET /any-endpoint
    M-->>S: check wallet name
    S-->>M: 
    M->>A: OK
```

#### To use this mehanism you simply need to set the upgrading record in the wallet (DB) and add the wallet name to the singleton set. The middleware will prevent requests from being processed until the upgrade process is finished. After the upgrade process is finished you must remove the wallet name from the set and delete the upgrading record in the wallet (DB).

##### An example can be found via the anoncreds upgrade `aries_cloudagent/wallet/routes.py` in the `upgrade_anoncreds` controller.