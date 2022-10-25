# Running an Author Agent and connecting to an Endorser

This directory contains scripts to run an aca-py agent as an Author, that can conenct to an Endorser service.

## Running the Author Agent

The docker-compose script runs ngrok to expose the agent's port publicly, and stores wallet data in a postgres database.

To run the Author agent in this repo, open a command shell in this directory and run:

- to build the containers:

```bash
docker-compose build
```

- to run the author agent:

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
docker volume rm docker-agent_wallet-db-data
```

Note that the Author agent is not (yet) configured with revocations enabled or a tails server, so revocation is not supported.

## Connecting to an Endorser Service

For this example, we will connect to [this endorser service](https://github.com/bcgov/aries-endorser-service), which you can connect to locally at `http://localhost:5050/endorser/docs`.

Make sure you start the endorser service on the same ledger as your author, and make sure the endorser has a public DID with ENDORSER role.

For example start the endorser service as `LEDGER_URL=http://test.bcovrin.vonx.io TAILS_SERVER_URL=https://tails-test.vonx.io ./manage start --logs` and then make sure the Author agent is started with `--genesis_url http://test.bcovrin.vonx.io/genesis`.

### Connecting the Author to the Endorser

Endorser Service:  Use the `GET /v1/admin/config` endpoint to fetch the endorser's configuration, including the public DID (which the author will need to know).  Also confirm whether the `ENDORSER_AUTO_ACCEPT_CONNECTIONS` and `ENDORSER_AUTO_ENDORSE_REQUESTS` settings are `True` or `False` - for the following we will assume that both are `False` and the endorser must explicitely respond to all requests.

Author Agent:  Use the `POST /didexchange/create-request` to request a connection with the endorser, using the endorser's public DID.  Set the `alias` to `Endorser` - this *MUST* match the `--endorser-alias 'Endorser'` setting (in the ngrok-wait.sh script).  Use the `GET /connections` endpoint to verify the connection is in `request` state.

Endorser Service:  Use the `GET /v1/connections` endpoint to see the connection request (state `request`).  Using the `connection_id`, call the `POST /connections/{connection_id}/accept` endpoint to accept the request.  Verify that the connection state goes to `active`.

Author Agent:  Verify the connection state goes to `active`.  Use the `POST /transactions/{conn_id}/set-endorser-role` to set the connection role to `TRANSACTION_AUTHOR`, and then use `POST /transactions/{conn_id}/set-endorser-info` to set the endorser's alias to `Endorser` and the public DID to the endorser's public DID.  Verify the settings using the `GET /connections/{conn_id}/meta-data` endpoint.

The connection is now setup between the two agents!

### Creating a Public Author DID

Author Agent:  Use the `POST /wallet/did/create` (use an empty `{}` POST body) to create a local did.  Then use `POST /ledger/register-nym` to send the data to the ledger - this will create a transaction and send it to the endorser service.

Endorser Service:  Use the `GET /v1/endorse/transactions` endpoint to see the endorse request - it should be in state `request_received`.  Using the `POST /v1/endorse/transactions/{transaction_id}/endorse` endpoint and the `transaction_id`, approve the request.  The state should now (eventually) go to `transaction_acked`.

Author Service:  Use the `GET /transactions` endpoint to verify the transaction is in `transaction_acked` state.  Then use the `POST /wallet/did/public` to set the new DID to be the Author's public DID.  This will generate another endorser transaction to set the DID's endpoint (ATTRIB transaction) on the ledger.

Endorser Service:  Use the same endpoints as above (`GET /v1/endorse/transactions` and then `POST /v1/endorse/transactions/{transaction_id}/endorse`) to view the endorse request and approve it.

### Endorsing Author Requests

Author requests to create schema, create credential definition and create revocation registries will all now generate endorse requests to the endorser.

Author Agent:  To create a schema use the `POST /schemas` endpoint.  This will create an endorse request.

Endorser Service:  Use the same endpoints as above (`GET /v1/endorse/transactions` and then `POST /v1/endorse/transactions/{transaction_id}/endorse`) to view the endorse request and approve it.

Author Agent:  To create a cred def use the `POST /credential-definitions` endpoint.  This will create an endorse request.

Endorser Service:  Use the same endpoints as above (`GET /v1/endorse/transactions` and then `POST /v1/endorse/transactions/{transaction_id}/endorse`) to view the endorse request and approve it.



