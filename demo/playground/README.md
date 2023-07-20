# ACA-Py Playground

This directory contains scripts to run several ACA-Py agents in various configurations for demonstration, development and testing scenarios. The agents are using Postgres (15) database storage (`askar`, `DatabasePerWallet`) and are running without security (`--admin-insecure-mode`).

The inspiration for this playground was testing mediation and the differences between single-tenant and multi-tenant modes. These scripts allowed the developer to stand up 3 single-tenant agents and 1 multi-tenant agent and run various scenarios (see [scripts](./scripts) - for some basic examples). Running in `--admin-insecure-mode` simplifies creating tenants in multi-tenant mode and eliminates the need for adding headers for calls in single-tenant mode.

- faber-agent
- alice-agent
- acme-agent
- multi-agent (the multi-tenant agent)

By default, all the agents share the same Postgres Database Service (version 15) and all use [Ngrok](https://ngrok.com) for publicly accessible URLs.

## Dependencies

Docker Compose version v2.17.2

## Agent Configuration

There are two simple configurations provided:

- [`singletenant-auto-accept.yml`](./configs/singletenant-auto-accept.yml)
- [`multitenant-auto-accept.yml`](./configs/multitenant-auto-accept.yml)

These configuration files are provided to the ACA-Py start command via the `AGENT_ARG_FILE` environment variable. See [`.env`](./.env.sample) and [`start.sh`](./start.sh).

### Dockerfile and start.sh

[`Dockerfile.acapy`](./Dockerfile.acapy) assembles the image to run. Currently based on [Aries Cloudagent Python 0.8.1](ghcr.io/hyperledger/aries-cloudagent-python:py3.9-indy-1.16.0-0.8.1), we need [jq](https://stedolan.github.io/jq/) to setup (or not) the ngrok tunnel and execute the Aca-py start command - see [`start.sh`](./start.sh). You may note that the start command is very sparse, additional configuration is done via environment variables in the [docker compose file](./docker-compose.yml).

### ngrok

Note that ngrok allows 2 tunnels per instance with an unpaid account. We have broken up the 4 default services into 2 ngrok services and tunnel configurations. If you need to alter port numbers for your agent services, you will have to update the ngrok tunnel files.

- [ngrok-faber-alice](./ngrok-faber-alice.yml)
- [ngrok-acme-multi](./ngrok-acme-multi.yml)

If you have a paid account, you can set the `NGROK_AUTHTOKEN` environment variable. See below.

### .env

Additional configuration (ie. port numbers for the services, `NGROK_AUTHTOKEN`, ...) are done in the [`.env`](./.env.sample) file. Change as needed and ensure ngrok configuration matches.

```shell
cp .env.sample .env
```

## Running the Playground

To run the agents in this repo, open a command shell in this directory and run:

- to build the containers:

```bash
docker compose build
```

- to run the agents:

```bash
docker compose up
```

- to shut down:

```bash
docker compose stop
docker compose rm -f
```

This will leave the agents wallet data, so if you restart the agent it will maintain any created data.

- to remove the wallet data:

```bash
docker compose down -v --remove-orphans
```

- individual services can be started by specifying the service name(s):

```bash
docker compose up multi-agent
docker compose up faber-agent alice-agent
```

You can now access the agent Admin APIs via Swagger at:

- faber: [http://localhost:9011/api/doc#](http://localhost:9011/api/doc#)
- alice: [http://localhost:9012/api/doc#](http://localhost:9012/api/doc#)
- acme: [http://localhost:9013/api/doc#](http://localhost:9013/api/doc#)
- multi: [http://localhost:9014/api/doc#](http://localhost:9014/api/doc#)

## Scripts

While having the Swagger Admin API is excellent, you may need to do something more complex than a single API call. You may need to see how agents with varying capabilities interact or validate that single-tenant and multi-tenant work the same. Jumping around from multiple browser tabs and cutting and pasting ids and JSON blocks can quickly grow tiresome.

A few Python (3.9) [scripts](./scripts) are provided as examples of what you may do once your agents are up and running.

```shell
cd scripts
pip install -r requirements.txt
python ping_agents.py
```

The [`ping_agents`](./scripts/ping_agents.py) script is a trivial example using the ACA-Py API to create tenants in the multi-agent instance and interact between the agents. We create and receive invitations and ping each other.

The [`mediator_ping_agents`](./scripts/mediator_ping_agents) script requires that you have a mediator service running and have the mediator's invitation URL. See [Aries Mediator Service](https://github.com/hyperledger/aries-mediator-service) for standing up a local instance and how to find the invitation URL. In this script, each agent requests mediation and we can see the mediator forwarding messages between the agents.

## Run without NGrok

[Ngrok](https://ngrok.com) provides a tunneling service and a way to provide a public IP to your locally running instance of ACA-Py. There are restrictions with Ngrok most notably regarding inbound connections.

```shell
Too many connections! The tunnel session SESSION has violated the rate-limit policy of THRESHOLD connections per minute by initiating COUNT connections in the last SECONDS seconds. Please decrease your inbound connection volume or upgrade to a paid plan for additional capacity.

ngrok limits the number of inbound connections to your tunnels. Limits are imposed on connections, not requests. If your HTTP clients use persistent connections aka HTTP keep-alive (most modern ones do), you'll likely never hit this limit. ngrok will return a 429 response to HTTP connections that exceed the rate limit. Connections to TCP and TLS tunnels violating the rate limit will be closed without a response.
```

If you do not require external access to your instance, consider turning NGrok off. NGrok tunnelling can be disabled by changing an environment variable for each service. Set `TUNNEL_NAME` to null/empty, and no tunnel will be created. See [`.env`](.env.sample), [`docker-compose.yml`](./docker-compose.yml) and [`start.sh`](./start.sh),

### update .env

```shell
FABER_TUNNEL_NAME=
```

### docker-compose.yml

```shell
    environment:
      - TUNNEL_HOST=${FABER_TUNNEL_HOST}
```

### start.sh

```shell
# if $TUNNEL_NAME is not empty, grab the service's ngrok route and set our ACAPY_ENDPOINT
if [[ ! -z "$TUNNEL_NAME" ]]; then . . .
```

Set service value to empty in `.env` that will set the `TUNNEL_NAME` environment variable to empty which will circumvent the use of the tunnel for the service (`ACAPY_ENDPOINT`).

## ELK Stack / Tracing logging

Please see [ELK Stack Readme](../elk-stack/README.md).

You may notice a series of environment variables for each agent service in [.env](./.env.sample) and commented-out network and agent configuration in the [docker compose file](./docker-compose.yml). Check the environment variables and uncomment as needed if wanting to send trace events to ELK.
