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

# Run without NGrok
[Ngrok](https://ngrok.com) provides a tunneling service and a way to provide a public IP to your locally running instance of Aca-Py. There are restrictions with Ngrok most notably regarding inbound connections. 

```
Too many connections! The tunnel session SESSION has violated the rate-limit policy of THRESHOLD connections per minute by initiating COUNT connections in the last SECONDS seconds. Please decrease your inbound connection volume or upgrade to a paid plan for additional capacity.

ngrok limits the number of inbound connections to your tunnels. Limits are imposed on connections, not requests. If your HTTP clients use persistent connections aka HTTP keep-alive (most modern ones do), you'll likely never hit this limit. ngrok will return a 429 response to HTTP connections that exceed the rate limit. Connections to TCP and TLS tunnels violating the rate limit will be closed without a response.
```

If you do not require external access to your instance, consider turning NGrok off. NGrok tunneling can be disabled by changing the environment variable `ACAPY_AGENT_ACCESS` from "public" to "local".  See [docker-compose file](docker-compose.yml).  

```
    environment:
      - NGROK_NAME=ngrok-agent
      - ACAPY_AGENT_ACCESS=local
```


# ELK Stack / Tracing logging

Please see [ELK Stack Readme](../elk-stack/README.md) to run the `multi-demo` with tracing enabled and pushing into an ELK Stack.