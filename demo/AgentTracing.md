# Using Tracing in ACA-PY

The aca-py agent supports message tracing, according to the [Tracing RFC](https://github.com/hyperledger/aries-rfcs/tree/master/features/0034-message-tracing).

Tracing can be enabled globally, for all messages/events, or it can be enabled on an exchange-by-exchange basis.

Tracing is configured globally for the agent.

## ACA-PY Configuration

The following options can be specified when starting the aca-py agent:

```
  --trace               Generate tracing events.
  --trace-target <trace-target>
                        Target for trace events ("log", "message", or http
                        endpoint).
  --trace-tag <trace-tag>
                        Tag to be included when logging events.
  --trace-label <trace-label>
                        Label (agent name) used logging events.
```

The `--trace` option enables tracing globally for the agent, the other options can configure the trace destination and content (default is `log`).

Tracing can be enabled on an exchange-by-exchange basis, by including `{ ... "trace": True, ...}` in the JSON payload to the API call (for credential and proof exchanges).

## Enabling Tracing in the Alice/Faber Demo

The `run_demo` script supports the following parameters and environment variables.

Environment variables:

```
TRACE_ENABLED          Flag to enable tracing

TRACE_TARGET_URL       Host:port of endpoint to log trace events (e.g. fluentd:8088)

DOCKER_NET             Docker network to join (must be used if EFK stack is running in docker)

TRACE_TAG              Tag to be included in all logged trace events
```

Parameters:

```
--trace-log            Enables tracing to the standard log output
                       (sets TRACE_ENABLED, TRACE_TARGET, TRACE_TAG)

--trace-http           Enables tracing to an HTTP endpoint (specified by TRACE_TARGET_URL)
                       (sets TRACE_ENABLED, TRACE_TARGET, TRACE_TAG)
```

When running the Faber controller, tracing can be enabled using the `T` menu option:

```
Faber      | Connected
    (1) Issue Credential
    (2) Send Proof Request
    (3) Send Message
    (T) Toggle tracing on credential/proof exchange
    (X) Exit?
[1/2/3/T/X] t

>>> Credential/Proof Exchange Tracing is ON
    (1) Issue Credential
    (2) Send Proof Request
    (3) Send Message
    (T) Toggle tracing on credential/proof exchange
    (X) Exit?

[1/2/3/T/X] t

>>> Credential/Proof Exchange Tracing is OFF
    (1) Issue Credential
    (2) Send Proof Request
    (3) Send Message
    (T) Toggle tracing on credential/proof exchange
    (X) Exit?

[1/2/3/T/X]
```

When `Exchange Tracing` is `ON`, all exchanges will include tracing.

## Logging Trace Events to an EFK Stack

You can use the `EFK` stack in the [EFK sub-directory](./EFK-stack) as a target for trace events, just start the EFK stack using the docker-compose file and then in two separate bash shells, startup the demo as follows:

```bash
DOCKER_NET=efk-stack_efk_net TRACE_TARGET_URL=fluentd:8088 ./run_demo faber --trace-http
```

```bash
DOCKER_NET=efk-stack_efk_net TRACE_TARGET_URL=fluentd:8088 ./run_demo alice --trace-http
```

## Hooking into event messaging

ACA-PY supports sending events to web hooks, which allows the demo agents to display them in the CLI. To also send them to another end point, use the `--webhook-url` option, which requires the `WEBHOOK_URL` environment variable. Configure an end point running on the docker host system, port *8888*, use the following:

```bash
WEBHOOK_URL=host.docker.internal:8888 ./run_demo faber --webhook-url
```
