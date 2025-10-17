# Kanon Storage docs

## Concepts

Kanon Storage is a normalized approach to secure data storage for ACA-Py that introducing an additional component that complements the existing Askar Aries solution. While Askar provides robust field-level encryption and secure storage for ACA-Py, it currently has limitations when it comes to the choice of database providers for large-scale, server-side deployments and lacks an interface to support report generation.

Kanon Storage addresses these gaps by introducing a component designed to work alongside Askar. This new component offers support for multiple enterprise-grade database providers, including cloud-based solutions. It also leverages cloud-native encryption capabilities, providing flexibility with options for encryption at rest and field-level encryption that can be turned on or off based on specific security requirements.

By relying on proven, built-in encryption mechanisms provided by various database and cloud platforms, this approach simplifies the overall architecture, reducing the need for custom encryption logic at the application layer. It also maximizes the benefits of vendor-provided encryption technologies, ensuring "best-of-breed" encryption tailored to each database provider.

This enhancement also prepares the ACA-Py system for quantum-proof encryption by allowing different vendors to implement solutions aligned with their specific quantum-resistant technologies. This design strengthens ACA-Py’s resilience while maintaining flexibility, scalability, and compliance with enterprise-grade standards.

The new Database store module supports the existing DBStore interface to ensure compatibility with all the existing Acapy modules.  It provides core functionality for provisioning, opening, and removing stores; managing profiles; executing scans; and handling sessions or transactions. It also includes method such as provision, open, create profile, scan, and close. 

Furthermore, the DB Store also introduces new functions such as 
- A new keyset pagination method for scans
- Provisioning the store includes configurable parameters such as the schema configuration type (Normalized or Generic) and the schema release version.
- Opening the store allows the ACA-Py profile to control and enforce which schema release version is required for operation.

The existing Wallet Query Language (WQL) module is a custom-built tool that provides a unified approach to querying data across various database systems. It accepts JSON input and translates it into database-specific query statements.

It’s important for the new database module to support the existing WQL because it plays a central role in the Aries ecosystem, as it is the language/protocol currently used to communicate with the storage layer.

In order for ACA-Py and other tools in the Aries ecosystem to use the new storage module without code changes, our proposal is to leverage and enhance the current WQL design and rebuild it. The enhancement will be able to easily extend WQL’s functionality to support multiple database-specific query encoders. 

The new extended encoders are able to support the following query types:
- Key-value pair table structure (Generic)
- Document / sub-document structure (e.g., MongoDB)
- Normalized table structure

## Scan Function:

To ensure backward compatibility, we have implemented an OFFSET-based cursor scan function.

- Uses sqlite3.Cursor
- Uses OFFSET-based pagination
- Combines with a Python generator and DB cursor to stream results.
- Minimizes memory usage by yielding entries one-by-one instead of loading all at once.
- Supports page jumping (e.g., go to page 5).


## Limitations with OFFSET (for large datasets)
- OFFSET becomes slower as the value increases (e.g., OFFSET 100000).
- PostgreSQL still has to scan and discard all skipped rows before returning the next page.
- Performance degrades significantly with large tables (like 8 million records).
- Not suitable for real-time or large-scale production loads.

To address this, we have introduced  keyset pagination - scan_keyset()
- Users sqlite3.Cursor
- Leverages indexed column (id) for fast and consistent page retrieval.
- Much more scalable and efficient on large datasets.
- Works well for infinite scrolling, continuous fetching, and API data streaming.

## Trade-offs of Keyset Pagination
- Cannot jump to pages (e.g., "go to page 100").
- Only supports forward sequential navigation.
- Caller must track the last item’s ID (or composite key) to fetch the next page.

## Provisioning Kanon Storage at startup

Provisioning the ACA-Py data store involves setting configurable parameters, such as choosing between a Normalized or Generic schema configuration and specifying the schema release version. NOTE that the Generic Schema configuration (key-value pair structure) does not support version control. 

For the Normalized configuration, each category of ACA-Py JSON document—such as Connection, Credential Definition, or Schema—is linked to a specific schema file that defines table creation, triggers, indexes, and drop statements for various database types (e.g., SQLite, PostgreSQL, MSSQL). These schema files also include version details to ensure consistency.

Schema release management is handled through release notes, which allow a mix of schema versions for different categories, controlled by the ACA-Py maintainer and set during provisioning. 

When opening the data store, the ACA-Py Kanon Anoncreds Profile enforces the required schema release version, checking for compatibility and prompting the user to perform an upgrade if the versions don’t match.

### New startup parameters for KanonAnoncreds profile

NOTE: Kanon Anoncreds Profile will use Askar for Key Management only. 

| Startup Parameter                                            | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| --wallet-type kanon-anoncreds                                 | New wallet type: kanon-anocreds                              |
| --wallet-name your_wallet_name                               | Both Askar and DB stores will use the same wallet name as the profile name. |
| --wallet-key askar_secret_key                                | Askar storage only - no changes                              |
| --wallet-key-derivation-method RAW                           | Askar storage only - no changes                              |
| --wallet-storage-type sqlite / postgresql                    | Askar storage only - no changes                              |
| --wallet-storage-creds                                       | Askar storage only - no changes                              |
| --dbstore-key db.storage.new.secret                          | DB Store - sqlite only - if provided the sqlite store will be encrypted. |
| --dbstore-storage-type sqlite / postgresql                   | DB Store - define storage type for DB Store                  |
| --dbstore-storage-config<br/>'{"url":"192.168.2.164:5432", "connection_timeout":30.0, "max_connections":100, "min_idle_count":5, "max_idle":10.0, "max_lifetime":7200.0,"tls":{"sslmode":"prefer", "sslcert":"/path/to/client.crt" ,"sslkey":"/path/to/client.key", "sslrootcert":"/path/to/ca.crt"}}' | DB Store - postgresql only - describe the connection requirements for postgresql database.  <br />DB Store also supports TLS/SSL Settings for secure communication. |
| --dbstore-storage-creds '{"account":"myuser", "password":"mypass"}' | DB Store - postgresql only - to specify the user accounts.   |
| --dbstore-schema-config normalize / generic                  | DB Store - Specify the type of schema configuration you want during provisioning. |
| --auto-provision                                             | When the wallet does not exist, both Askar and DB store will automatically trigger the provisioning procedure |
| --recreate-wallet                                            | Both **Askar** and **DB Store** behave the same way. To recreate a wallet, the provision command must be used explicitly, just like the existing Askar implementation.<br />If a wallet already exists with the same name, both Askar and DB Store will remove the existing wallet and create a new one.<br />For **DB Store** in **normalized mode** with the **PostgreSQL implementation**, the process is slightly different:<br />Instead of deleting the entire database, it will first record the existing schema version, retrieve the release notes for that version, and then perform a **drop and create the** tables based on that specific release. |

## Example startup with Kanon Storage (sqlite un-encrypted)

```bash
aca-py start \
  --endpoint https://bb24329752a7.ngrok-free.app \
  --label veridid.agent.kanon.issuer.normalized \
  --inbound-transport http 0.0.0.0 8030 \
  --outbound-transport http \
  --admin 0.0.0.0 8031 \
  --admin-insecure-mode \
  --wallet-type kanon-anoncreds\
  --wallet-storage-type sqlite \
  --wallet-name veridid.agent.kanon.issuer.normalized \
  --wallet-key kms.storage.secret \
  --preserve-exchange-records \
  --genesis-url http://test.bcovrin.vonx.io/genesis \
  --tails-server-base-url http://tails-server.digicred.services:6543 \
  --trace-target log \
  --trace-tag acapy.events \
  --trace-label alice.agent.trace \
  --auto-ping-connection \
  --auto-respond-messages \
  --auto-accept-invites \
  --auto-accept-requests \
  --auto-respond-credential-proposal \
  --auto-respond-credential-offer \
  --auto-respond-credential-request \
  --auto-store-credential \
  --log-file acatest.log \
  --log-level debug \
  --auto-provision \
  --wallet-allow-insecure-seed 
```

## Example startup with Kanon Storage (postgresql normalize)

```bash
 aca-py start \
  --endpoint https://c3614600333f.ngrok-free.app \
  --label veridid_multitenant_postgres_normalize  \
  --inbound-transport http 0.0.0.0 8030 \
  --outbound-transport http \
  --admin 0.0.0.0 8031 \
  --wallet-type kanon-anoncreds \
  --wallet-storage-type postgres \
  --wallet-name veridid_multitenant_postgres_normalize \
  --wallet-key kms.storage.new.secret \
  --wallet-storage-config '{"url":"192.168.2.164:5432","max_connections":100,"min_idle_count":5,"max_idle":10.0,"max_lifetime":7200.0}' \
  --wallet-storage-creds '{"account":"myuser","password":"mypass"}' \
  --dbstore-storage-type postgres \
  --dbstore-storage-config '{"url":"192.168.2.164:5432","connection_timeout":30.0,"max_connections":100,"min_idle_count":5,"max_idle":10.0,"max_lifetime":7200.0,"tls":{"sslmode":"prefer"}}' \
  --dbstore-storage-creds '{"account":"myuser","password":"mypass"}' \
  --dbstore-schema-config normalize \
  --multitenant \
  --multitenant-admin \
  --admin-api-key 76d3xW38jc9cd2VBZy8FVaxEHHD \
  --preserve-exchange-records \
  --genesis-url http://test.bcovrin.vonx.io/genesis \
  --tails-server-base-url http://tails-server.digicred.services:6543 \
  --trace-target log \
  --trace-tag acapy.events \
  --trace-label alice.agent.trace \
  --auto-ping-connection \
  --auto-respond-messages \
  --auto-accept-invites \
  --auto-accept-requests \
  --auto-respond-credential-proposal \
  --auto-respond-credential-offer \
  --auto-respond-credential-request \
  --auto-store-credential \
  --log-file acatest.log \
  --log-level debug \
  --auto-provision \
  --wallet-allow-insecure-seed \
  --jwt-secret secret  
```