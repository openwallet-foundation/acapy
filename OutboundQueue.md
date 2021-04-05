# Outbound Queues in ACA-py

## Background

By default, messages often stay in ACA-py memory for long periods of time without being delivered. As a result, when the ACA-py Python process is terminated unexpectedly, messages are lost.

But with recent changes, outbound messages can now be sent to a message queue of your choice instead of being delivered by ACA-py. This queue is external to the ACA-py process, and can be configured for the durability requirements you want. This new concept of an "outbound queue" is intended to be an optional replacement to the current ACA-py outbound transport (i.e. option `-ot`, `--outbound-transport`).

If you run an outbound queue, you will also need to run a new service, a delivery agent, to actually deliver the message. See more details below.

## Usage Details

A new set of commandline options have been added to provide a way for users to "opt in" to use of the outbound queue. These new options are as follows:

- `-oq`, `--outbound-queue`: specifies the queue connection details.
- `-oqp`, `--outbound-queue-prefix`: defines a prefix to use when generating the topic key.
- `-oqc`, `--outbound-queue-class`: specify the location of a custom queue class.

Only the first, `--outbound-queue`, is required if you would like to opt into the outbound queue to replace `--outbound-transport`. The input for this option takes the form `[protocol]://[host]:[port]`. So for example, if the queue I want to use is Redis, on host `myredis.mydomain.com` using the default port for Redis, the string would be as follows: `redis://myredis.mydomain.com:6379`

The second option, `--outbound-queue-prefix`, specifies the queue topic prefix. The queue topic is generated in the following form: `{prefix}.outbound_transport`. The default value for this commandline option is the value `acapy`, so a queue key of `acapy.outbound_transport` is generated in the case of the default settings. ACA-py will send messages to the queue using this generated key as the topic.

The third option, `--outbound-queue-class`, specifies the queue backend. By default, this is `aries_cloudagent.transport.outbound.queue.redis:RedisOutboundQueue`, which specifies ACA-py's builtin Redis `LIST` backend. Users can define their own class, inheriting from `BaseOutboundQueue`, to implement a queue backend of their choice. This commandline option is the official entrypoint of ACA-py's pluggable queue interface. Developers must specify a Python dotpath to a module importable in the current `PYTHONPATH`, followed by a colon, followed by the name of their custom class.

## Delivery Agent

When using `--outbound-queue` instead of `--outbound-transport`, ACA-py no longer delivers the messages to destinations. Instead, a delivery service ([a prototype can be found here](https://github.com/andrewwhitehead/aca-deliver)) would need to be run. This service should pick up a message from the queue and then deliver that message. 

When running `--outbound-queue`, ACA-py serializes messages to be sent to the queue by using MessagePack. MessagePack is a protocol to serialize content into a compact binary format. ACA-py generates keys in MessagePack as follows:
- `endpoint` - specifies the endpoint for the message.
- `headers` - specifies a set of key-value pairs representing message headers.
- `payload` - the raw binary content of the message.

The delivery service will need to deserialize the binary content on the consuming end. The result will then be a key-value data structure (for example, a `dict` in Python). So the deseralized message, deserialized into a Python `dict` for example, would be in the following form:
```
{
    "headers": {"Content-Type": "..."},
    "endpoint": "...",
    "payload": "..."
}
```
The delivery agent should process this message and deliver it to the recipient as appropriate.

## Backend-Specific Notes

### Redis

Value for `--outbound-queue-class` to use this backend:
- `aries_cloudagent.transport.outbound.queue.redis:RedisOutboundQueue`

This is a queue backend, using the `LIST` data type in Redis. When using Redis, the delivery service consuming this queue in order to send outbound messages over transport will need to pop from the left side of the queue (i.e. the Redis `LPOP` command) to get messages in the order they were sent.

Users will need to configure [Redis persistence](https://redis.io/topics/persistence) to gain message durability benefits in their Redis deployment. Redis by default runs entirely in-memory, so it is subject to the same data loss characteristics as ACA-py unless you also configure it to run in persistence mode.
