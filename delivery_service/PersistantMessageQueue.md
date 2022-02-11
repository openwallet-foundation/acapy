# ACA-PY Persistent Queue

```
│    
│
└───aries_cloudagent
│   │
│   └───core
│   │   conductor.py
│   │
│   └───transport
│       │  
│       └───inbound   
│       │     │
│       │     └───queue 
│       └───outbound
│             │
│             └───queue 
└───delivery_service
│    │   redis
│    │   kafka
│    │   run_delivery_service
│    │   docker-compose.yml
│   
```
## Steps
- Specifically for Kafka, the kafka instance, ACA-Py agent and delivery service agents will have to run in the same docker network. Create a docker network, `docker network create NETWORK_NAME`
- `export ACAPY_DOCKER_NETWORK=NETWORK_NAME`
<br/>To reset and run ACA-Py in default bridge network(as previously), execute `export ACAPY_DOCKER_NETWORK=""` 
- Start a Kafka or Redis instance (`docker-compose.yml` included below)
- Startup ACA-Py agent, `run_docker` script manages the delivery_agents automatically.
```
PORTS="5002" ./scripts/run_docker start --admin 0.0.0.0 5002 --admin-insecure-mode --public-invites --auto-ping-connection --auto-accept-invites --auto-accept-requests --auto-respond-credential-offer --auto-respond-credential-request --auto-respond-presentation-proposal --auto-verify-presentation --genesis-url http://host.docker.internal:9000/genesis --seed 00000000000000000000000000000008 --auto-provision --recreate-wallet --wallet-type indy --wallet-name issuer --wallet-key mykey -oq kafka:9092 -oqp acapy -oqc aries_cloudagent.transport.outbound.queue.kafka.KafkaOutboundQueue -iq kafka:9092 -iqp acapy -iqc aries_cloudagent.transport.inbound.queue.kafka.KafkaInboundQueue -e http://host.docker.internal:8002 -iqt http 0.0.0.0 8002
```
```
PORTS="5002" ./scripts/run_docker start --admin 0.0.0.0 5002 --admin-insecure-mode --public-invites --auto-ping-connection --auto-accept-invites --auto-accept-requests --auto-respond-credential-offer --auto-respond-credential-request --auto-respond-presentation-proposal --auto-verify-presentation --genesis-url http://host.docker.internal:9000/genesis --seed 00000000000000000000000000000008 --auto-provision --recreate-wallet --wallet-type indy --wallet-name issuer --wallet-key mykey -oq redis://host.docker.internal:6379 -oqp acapy -oqc aries_cloudagent.transport.outbound.queue.redis.RedisOutboundQueue -iq redis://host.docker.internal:6379 -iqp acapy -iqc aries_cloudagent.transport.inbound.queue.redis.RedisInboundQueue -e http://host.docker.internal:8002 -iqt http 0.0.0.0 8002
```
## Startup arugments
### Inbound
- `-iq or --inbound-queue`<br/>
Specifies inbound queue connection details/host. The input for this option takes the form `[protocol]://[host]:[port]`. So for 
example,  `redis://myredis.mydomaincom:port` or `kafka:9092`. Currently, support Redis and Kafka backend only.
- `-iqc or --inbound-queue-class`<br/>
Defines the location of the Inbound Queue Engine. This must be 
a 'dotpath' to a Python module on the PYTHONPATH, followed by a 
colon, followed by the name of a Python class that implements 
BaseInboundQueue. This commandline option is the official entry 
point of ACA-py's pluggable queue interface. The default value is: 
'aries_cloudagent.transport.inbound.queue.redis.RedisInboundQueue
- `-iqp or --inbound-queue-prefix`<br/>
Specifies the queue topic prefix. The queue topic is generated 
in the following form: 'prefix.inbound_transport'. The default value
is the value `acapy`, so a queue key of 'acapy.inbound_transport' 
is generated in the case of the default settings. ACA-py will send 
messages to the queue using this generated key as the topic.
- `-iqt or --inbound-queue-transport`<br/>
REQUIRED. Defines the inbound queue transport(s) on which the inbound 
delivery_service agent listens for receiving messages from other 
agents. This parameter can be specified multiple times to create 
multiple interfaces. Built-in inbound transport types include 
'http' and 'ws'
### Outbound
- `-oq or --outbound-queue`<br/>
Specifies outbound queue connection details/host. The input for this option takes the form `[protocol]://[host]:[port]`. So for 
example,  `redis://myredis.mydomaincom:port` or `kafka:9092`. Currently, support Redis and Kafka backend only.
- `-oqc or --outbound-queue-class`<br/>
Defines the location of the Outbound Queue Engine. This must be 
a 'dotpath' to a Python module on the PYTHONPATH, followed by a 
colon, followed by the name of a Python class that implements 
BaseOutboundQueue. This commandline option is the official entry 
point of ACA-py's pluggable queue interface. The default value is: 
'aries_cloudagent.transport.outbound.queue.redis.RedisOutboundQueue
- `-oqp or --outbound-queue-prefix`<br/>
Specifies the queue topic prefix. The queue topic is generated 
in the following form: 'prefix.outbound_transport'. The default value
is the value `acapy`, so a queue key of 'acapy.outbound_transport' 
is generated in the case of the default settings. ACA-py will send 
messages to the queue using this generated key as the topic.

# Redis

## Start Redis Instance
```
version: "3"
services:
  redis:
    image: redis:latest
    networks:
      - acapy_default
    ports:
      - 6379:6379
    volumes:
      - ./config/redis.conf:/redis.conf
    command: ["redis-server", "/redis.conf"]
networks:
  acapy_default:
    external: true
    name: ${NETWORK_NAME}
```
Network name can either be specified as `NETWORK_NAME=acapy_test_network docker-compose up -d` or manually updated inside the `docker-compose.yml` itself

# Kafka

## Start Redis Instance
```
version: "3" 
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    networks:
      - acapy_default
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
  kafka:
    image: confluentinc/cp-kafka:latest
    networks:
      - acapy_default
    depends_on:
      - zookeeper
    ports:
      - 29092:29092
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
networks:
  acapy_default:
    external: true
    name: ${NETWORK_NAME}
```