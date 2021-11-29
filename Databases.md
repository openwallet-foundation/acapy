# Databases

Your wallet stores secret keys, connections and other information.
You have different choices to store this information.
The wallet supports 2 different databases to store data, SQLite and PostgreSQL.

## SQLite

If the wallet is configured the default way in eg. [demo-args.yaml](demo/demo-args.yaml), without explicit wallet-storage, a sqlite database file is used.

```yaml
# demo-args.yaml
wallet-type: indy
wallet-name: wallet
wallet-key: wallet-password
```

For this configuration, a folder called wallet will be created which contains a file called `sqlite.db`.

## PostgreSQL

The wallet can be configured to use PostgreSQL as storage.

```yaml
# demo-args.yaml
wallet-type: indy
wallet-name: wallet
wallet-key: wallet-password

wallet-storage-type: postgres_storage
wallet-storage-config: "{\"url\":\"db:5432\",\"wallet_scheme\":\"DatabasePerWallet\"}"
wallet-storage-creds: "{\"account\":\"postgres\",\"password\":\"mysecretpassword\",\"admin_account\":\"postgres\",\"admin_password\":\"mysecretpassword\"}"
```

In this case the hostname for the database is `db` on port 5432.

A docker-compose file could look like this:

```yaml
# docker-compose.yml
version: '3'
services:
  # acapy ...
  # database
  db:
    image: postgres:10
    environment:
      POSTGRES_PASSWORD: mysecretpassword
      POSTGRES_USER: postgres
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
```
