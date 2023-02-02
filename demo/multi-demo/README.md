# Running an Aca-Py Agent in Multitenant Mode

This directory contains scripts to run an aca-py agent in multitenancy mode.

## Running the Agent

The docker-compose script runs ngrok to expose the agent's port publicly, and stores wallet data in a postgres database.

To run the agent in this repo, open a command shell in this directory and run:

- to build the containers:

```bash
docker-compose build
```

- to run the agent:

```bash
docker-compose up
```

You can connect to the [agent's api service here](http://localhost:8010).

Note that all the configuration settings are hard-coded in the docker-compose file and ngrok-wait.sh script, so if you change any configs you need to rebuild the docker images.

- to shut down the agent:

```bash
docker-compose stop
docker-compose rm -f
```

This will leave the agent's wallet data, so if you restart the agent it will maintain any created data.

- to remove the agent's wallet:

```bash
docker volume rm multi-demo_wallet-db-data
```
