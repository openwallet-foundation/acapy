# Aca-Py Docker Test Scripts

These docker compose files allow you to run an aca-py instance against a postgres database.

There are separate scripts for starting the database and agent to allow you to restart the agent against the same postgres database.

This is useful for - for example - initializing a database with on older aca-py version, and then running an upgrade to a newer version.

To start the database:

```bash
docker-compose -f docker-compose-wallet.yml up
```

To start the agent:

```bash
docker-compose -f docker-compose-agent.yml up
```

Note you can edit the docker-compose file to change the aca-py version.

To stop the agent:

```bash
docker-compose -f docker-compose-agent.yml rm
```

To stop the database

```bash
docker-compose -f docker-compose-wallet.yml rm
```

To remove the database volume:

```bash
docker volume rm docker-test_wallet-db-data
```
