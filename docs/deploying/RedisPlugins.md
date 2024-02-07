# ACA-Py Redis Plugins
# [aries-acapy-plugin-redis-events](https://github.com/bcgov/aries-acapy-plugin-redis-events/blob/master/README.md) [`redis_queue`]

<!-- Adopted from aries-acapy-cache-redis/README.md -->
It provides a mechansim to persists both inbound and outbound messages using redis, deliver messages and webhooks, and dispatch events.

More details can be found [here](https://github.com/bcgov/aries-acapy-plugin-redis-events/blob/master/README.md).

### <b>Plugin configuration</b> [`yaml`]
```
redis_queue:
  connection: 
    connection_url: "redis://default:test1234@172.28.0.103:6379"

  ### For Inbound ###
  inbound:
    acapy_inbound_topic: "acapy_inbound"
    acapy_direct_resp_topic: "acapy_inbound_direct_resp"

  ### For Outbound ###
  outbound:
    acapy_outbound_topic: "acapy_outbound"
    mediator_mode: false

  ### For Event ###
  event:
    event_topic_maps:
      ^acapy::webhook::(.*)$: acapy-webhook-$wallet_id
      ^acapy::record::([^:]*)::([^:]*)$: acapy-record-with-state-$wallet_id
      ^acapy::record::([^:])?: acapy-record-$wallet_id
      acapy::basicmessage::received: acapy-basicmessage-received
      acapy::problem_report: acapy-problem_report
      acapy::ping::received: acapy-ping-received
      acapy::ping::response_received: acapy-ping-response_received
      acapy::actionmenu::received: acapy-actionmenu-received
      acapy::actionmenu::get-active-menu: acapy-actionmenu-get-active-menu
      acapy::actionmenu::perform-menu-action: acapy-actionmenu-perform-menu-action
      acapy::keylist::updated: acapy-keylist-updated
      acapy::revocation-notification::received: acapy-revocation-notification-received
      acapy::revocation-notification-v2::received: acapy-revocation-notification-v2-received
      acapy::forward::received: acapy-forward-received
    event_webhook_topic_maps:
      acapy::basicmessage::received: basicmessages
      acapy::problem_report: problem_report
      acapy::ping::received: ping
      acapy::ping::response_received: ping
      acapy::actionmenu::received: actionmenu
      acapy::actionmenu::get-active-menu: get-active-menu
      acapy::actionmenu::perform-menu-action: perform-menu-action
      acapy::keylist::updated: keylist
    deliver_webhook: true
```
- `redis_queue.connection.connection_url`: This is required and is expected in `redis://{username}:{password}@{host}:{port}` format.
- `redis_queue.inbound.acapy_inbound_topic`: This is the topic prefix for the inbound message queues. Recipient key of the message are also included in the complete topic name. The final topic will be in the following format `acapy_inbound_{recip_key}`
- `redis_queue.inbound.acapy_direct_resp_topic`: Queue topic name for direct responses to inbound message.
- `redis_queue.outbound.acapy_outbound_topic`: Queue topic name for the outbound messages. Used by Deliverer service to deliver the payloads to specified endpoint.
- `redis_queue.outbound.mediator_mode`: Set to true, if using Redis as a http bridge when setting up a mediator agent. By default, it is set to false.
- `event.event_topic_maps`: Event topic map
- `event.event_webhook_topic_maps`: Event to webhook topic map
- `event.deliver_webhook`: When set to true, this will deliver webhooks to endpoints specified in `admin.webhook_urls`. By default, set to true.

### <b>Usage</b>

#### <b>With Docker</b>
Running the plugin with docker is simple. An
example [docker-compose.yml](https://github.com/bcgov/aries-acapy-plugin-redis-events/blob/master/docker/docker-compose.yml) file is available which launches both ACA-Py with redis and an accompanying Redis cluster.

```sh
$ docker-compose up --build -d
```
More details can be found [here](https://github.com/bcgov/aries-acapy-plugin-redis-events/blob/master/docker/README.md).

#### <b>Without Docker</b>
Installation
```
pip install git+https://github.com/bcgov/aries-acapy-plugin-redis-events.git
```
Startup ACA-Py with `redis_queue` plugin loaded
```
docker network create --subnet=172.28.0.0/24 `network_name`
export REDIS_PASSWORD=" ... As specified in redis_cluster.conf ... "
export NETWORK_NAME="`network_name`"
aca-py start \
    --plugin redis_queue.v1_0.events \
    --plugin-config plugins-config.yaml \
    -it redis_queue.v1_0.inbound redis 0 -ot redis_queue.v1_0.outbound
    # ... the remainder of your startup arguments
```

Regardless of the options above, you will need to startup `deliverer` and `relay`/`mediator` service as a bridge to receive inbound messages. Consider the following to build your `docker-compose` file which should also start up your redis cluster:
- Relay + Deliverer
    ```
    relay:
        image: redis-relay
        build:
            context: ..
            dockerfile: redis_relay/Dockerfile
        ports:
            - 7001:7001
            - 80:80
        environment:
            - REDIS_SERVER_URL=redis://default:test1234@172.28.0.103:6379
            - TOPIC_PREFIX=acapy
            - STATUS_ENDPOINT_HOST=0.0.0.0
            - STATUS_ENDPOINT_PORT=7001
            - STATUS_ENDPOINT_API_KEY=test_api_key_1
            - INBOUND_TRANSPORT_CONFIG=[["http", "0.0.0.0", "80"]]
            - TUNNEL_ENDPOINT=http://relay-tunnel:4040
            - WAIT_BEFORE_HOSTS=15
            - WAIT_HOSTS=redis-node-3:6379
            - WAIT_HOSTS_TIMEOUT=120
            - WAIT_SLEEP_INTERVAL=1
            - WAIT_HOST_CONNECT_TIMEOUT=60
        depends_on:
            - redis-cluster
            - relay-tunnel
        networks:
            - acapy_default
    deliverer:
        image: redis-deliverer
        build:
            context: ..
            dockerfile: redis_deliverer/Dockerfile
        ports:
            - 7002:7002
        environment:
            - REDIS_SERVER_URL=redis://default:test1234@172.28.0.103:6379
            - TOPIC_PREFIX=acapy
            - STATUS_ENDPOINT_HOST=0.0.0.0
            - STATUS_ENDPOINT_PORT=7002
            - STATUS_ENDPOINT_API_KEY=test_api_key_2
            - WAIT_BEFORE_HOSTS=15
            - WAIT_HOSTS=redis-node-3:6379
            - WAIT_HOSTS_TIMEOUT=120
            - WAIT_SLEEP_INTERVAL=1
            - WAIT_HOST_CONNECT_TIMEOUT=60
        depends_on:
            - redis-cluster
        networks:
            - acapy_default
    ```
- Mediator + Deliverer
    ```
    mediator:
        image: acapy-redis-queue
        build:
            context: ..
            dockerfile: docker/Dockerfile
        ports:
            - 3002:3001
        depends_on:
            - deliverer
        volumes:
            - ./configs:/home/indy/configs:z
            - ./acapy-endpoint.sh:/home/indy/acapy-endpoint.sh:z
        environment:
            - WAIT_BEFORE_HOSTS=15
            - WAIT_HOSTS=redis-node-3:6379
            - WAIT_HOSTS_TIMEOUT=120
            - WAIT_SLEEP_INTERVAL=1
            - WAIT_HOST_CONNECT_TIMEOUT=60
            - TUNNEL_ENDPOINT=http://mediator-tunnel:4040
        networks:
            - acapy_default
        entrypoint: /bin/sh -c '/wait && ./acapy-endpoint.sh poetry run aca-py "$$@"' --
        command: start --arg-file ./configs/mediator.yml

    deliverer:
        image: redis-deliverer
        build:
            context: ..
            dockerfile: redis_deliverer/Dockerfile
        depends_on:
            - redis-cluster
        ports:
            - 7002:7002
        environment:
            - REDIS_SERVER_URL=redis://default:test1234@172.28.0.103:6379
            - TOPIC_PREFIX=acapy
            - STATUS_ENDPOINT_HOST=0.0.0.0
            - STATUS_ENDPOINT_PORT=7002
            - STATUS_ENDPOINT_API_KEY=test_api_key_2
            - WAIT_BEFORE_HOSTS=15
            - WAIT_HOSTS=redis-node-3:6379
            - WAIT_HOSTS_TIMEOUT=120
            - WAIT_SLEEP_INTERVAL=1
            - WAIT_HOST_CONNECT_TIMEOUT=60
        networks:
            - acapy_default
    ```

Both relay and mediator [demos](https://github.com/bcgov/aries-acapy-plugin-redis-events/tree/master/demo) are also available.

# [aries-acapy-cache-redis](https://github.com/Indicio-tech/aries-acapy-cache-redis/blob/main/README.md) [`redis_cache`]

<!-- Adopted from aries-acapy-cache-redis/README.md -->
ACA-Py uses a modular cache layer to story key-value pairs of data. The purpose
of this plugin is to allow ACA-Py to use Redis as the storage medium for it's
caching needs.

More details can be found [here](https://github.com/Indicio-tech/aries-acapy-cache-redis/blob/main/README.md).

### <b>Plugin configuration</b> [`yaml`]
```
redis_cache:
  connection: "redis://default:test1234@172.28.0.103:6379"
  max_connection: 50
  credentials:
    username: "default"
    password: "test1234"
  ssl:
    cacerts: ./ca.crt
```
- `redis_cache.connection`: This is required and is expected in `redis://{username}:{password}@{host}:{port}` format.
- `redis_cache.max_connection`: Maximum number of redis pool connections. Default: 50
- `redis_cache.credentials.username`: Redis instance username
- `redis_cache.credentials.password`: Redis instance password
- `redis_cache.ssl.cacerts`

### <b>Usage</b>

#### <b>With Docker</b>
- Running the plugin with docker is simple and straight-forward. There is an
example [docker-compose.yml](https://github.com/Indicio-tech/aries-acapy-cache-redis/blob/main/docker-compose.yml) file in the root of the
project that launches both ACA-Py and an accompanying Redis instance. Running
it is as simple as:

    ```sh
    $ docker-compose up --build -d
    ```

- To launch ACA-Py with an accompanying redis cluster of 6 nodes [3 primaries and 3 replicas], please refer to example [docker-compose.cluster.yml](https://github.com/Indicio-tech/aries-acapy-cache-redis/blob/main/docker-compose.cluster.yml) and run the following:

    Note: Cluster requires external docker network with specified subnet

    ```sh
    $ docker network create --subnet=172.28.0.0/24 `network_name`
    $ export REDIS_PASSWORD=" ... As specified in redis_cluster.conf ... "
    $ export NETWORK_NAME="`network_name`"
    $ docker-compose -f docker-compose.cluster.yml up --build -d
    ```
#### <b>Without Docker</b>
Installation
```
pip install git+https://github.com/Indicio-tech/aries-acapy-cache-redis.git
```
Startup ACA-Py with `redis_cache` plugin loaded
```
aca-py start \
    --plugin acapy_cache_redis.v0_1 \
    --plugin-config plugins-config.yaml \
    # ... the remainder of your startup arguments
```
or
```
aca-py start \
    --plugin acapy_cache_redis.v0_1 \
    --plugin-config-value "redis_cache.connection=redis://redis-host:6379/0" \
    --plugin-config-value "redis_cache.max_connections=90" \
    --plugin-config-value "redis_cache.credentials.username=username" \
    --plugin-config-value "redis_cache.credentials.password=password" \
    # ... the remainder of your startup arguments
```
## <b>RedisCluster</b>

If you startup a redis cluster and an ACA-Py agent loaded with either `redis_queue` or `redis_cache` plugin or both, then during the initialization of the plugin, it will bind an instance of `redis.asyncio.RedisCluster` [onto the `root_profile`]. Other plugin will have access to this redis client for it's functioning. This is done for efficiency and to avoid duplication of resources.
