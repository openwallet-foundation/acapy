# Databases

Your wallet stores secret keys, connections and other information.
You have different choices to store this information.
The wallet supports 2 different databases to store data, SQLite and PostgresDB.

## SQLite

If the wallet is configured the default way in eg. [demo-args.yaml](demo/demo-args.yaml), without explicit wallet-storage, a sqlite database file is used.

```yaml
wallet-type: indy
wallet-name: wallet
wallet-key: wallet-password
```

For this configuration, a folder called wallet will be created which contains a file called `sqlite.db`.
