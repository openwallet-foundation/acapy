# ACA-Py ELK Stack for demos

Note - this code was originally obtained from [https://github.com/deviantony/docker-elk](https://github.com/deviantony/docker-elk).

The following changes were made to better incorporate this stack into ACA-Py demos and tracing.

- renamed the network to `elknet` and added environment variable `ELK_NETWORK_NAME` in `.env` to change the name of the docker network. 
- set [elasticsearch](./elasticsearch/config/elasticsearch.yml) license to `basic`
- [logstash.conf](./logstash/pipeline/logstash.conf) set an http port (9700) and exposed this for pushing agent traces into ELK.

## run

```
cp .env.sample .env
docker compose build
docker compose up
```

Using the default configuration, `elasticsearch`, `kibana` and `logstash` services will be started. Kibana can be accessed at [http://localhost:5601](http://localhost:5601), and you can log in with `elastic / changeme` as the username and password.  

A `log-*` index will be created, and you can refresh the [Discover Analytics](http://localhost:5601/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:now-15m,to:now))&_a=(columns:!(traced_type,handler,elapsed_milli,outcome,thread_id,msg_id),filters:!(),index:'logs-*',interval:auto,query:(language:kuery,query:''),sort:!(!('@timestamp',desc)))) to see any logged events.


We can run demos to see agent tracing events and attach them to the `elknet` network to push events to ELK.

## demos

Assuming the elk stack is running from above... from your demos directory, in two separate bash shells, startup the demo as follows:

```bash
DOCKER_NET=elknet TRACE_TARGET_URL=logstash:9700 LEDGER_URL=https://test.bcovrin.vonx.io ./run_demo faber --trace-http
```

```bash
DOCKER_NET=elknet TRACE_TARGET_URL=logstash:9700 LEDGER_URL=https://test.bcovrin.vonx.io ./run_demo alice --trace-http
```

And run the demo scenarios as you wish.

**Note**: the `LEDGER_URL` override is unnecessary for tracing; it is only used so `faber` and `alice` are on the same ledger as the following `multi-demo`. 

## multi-demo

The `multi-demo` (running ACA-Py in multitenant mode) requires a few edits to [docker-compose.yml](../multi-demo/docker-compose.yml). 


Note the reference to `elknet`.

```
networks:  
  app-network:  
    name: ${APP_NETWORK_NAME:-appnet}
    driver: bridge
  elk-network:
    name: ${ELK_NETWORK_NAME:-elknet}
    driver: bridge    
```


And uncomment the tracing environment variables...

```docker-compose.yml
    environment:
      - NGROK_NAME=ngrok-agent
      - ACAPY_AGENT_ACCESS=${ACAPY_AGENT_ACCESS:-public}
      - ACAPY_TRACE=${ACAPY_TRACE:-1}
      - ACAPY_TRACE_TARGET=${ACAPY_TRACE_TARGET:-http://logstash:9700/}
      - ACAPY_TRACE_TAG=${ACAPY_TRACE_TAG:-acapy.events}
      - ACAPY_TRACE_LABEL=${ACAPY_TRACE_LABEL:-multi.agent.trace}
```

Another change you may wish to make is setting `ACAPY_AGENT_ACCESS` to `local`. Use this if there is no need for ngrok tunnelling. For instance, if all your agents are local to the docker network (ie not phones) and connect only to themselves (or with some "public" agents), then we can eliminate `ngrok` throwing errors if we have too many simultaneous http connections (ie hundreds of wallets in a load test).

Assuming the elk stack is running from above... from your multi-demo directory, startup the agent as follows:

```bash
docker compose build
docker compose up
```


# Elastic stack (ELK) on Docker

[![Elastic Stack version](https://img.shields.io/badge/Elastic%20Stack-8.7.0-00bfb3?style=flat&logo=elastic-stack)](https://www.elastic.co/blog/category/releases)
[![Build Status](https://github.com/deviantony/docker-elk/workflows/CI/badge.svg?branch=main)](https://github.com/deviantony/docker-elk/actions?query=workflow%3ACI+branch%3Amain)
[![Join the chat](https://badges.gitter.im/Join%20Chat.svg)](https://app.gitter.im/#/room/#deviantony_docker-elk:gitter.im)

Run the latest version of the [Elastic stack][elk-stack] with Docker and Docker Compose.

It gives you the ability to analyze any data set by using the searching/aggregation capabilities of Elasticsearch and
the visualization power of Kibana.

![Animated demo](https://user-images.githubusercontent.com/3299086/155972072-0c89d6db-707a-47a1-818b-5f976565f95a.gif)

> **Note**  
> [Platinum][subscriptions] features are enabled by default for a [trial][license-mngmt] duration of **30 days**. After
> this evaluation period, you will retain access to all the free features included in the Open Basic license seamlessly,
> without manual intervention required, and without losing any data. Refer to the [How to disable paid
> features](#how-to-disable-paid-features) section to opt out of this behaviour.

Based on the official Docker images from Elastic:

* [Elasticsearch](https://github.com/elastic/elasticsearch/tree/main/distribution/docker)
* [Logstash](https://github.com/elastic/logstash/tree/main/docker)
* [Kibana](https://github.com/elastic/kibana/tree/main/src/dev/build/tasks/os_packages/docker_generator)

Other available stack variants:

* [`tls`](https://github.com/deviantony/docker-elk/tree/tls): TLS encryption enabled in Elasticsearch, Kibana (opt in),
  and Fleet
* [`searchguard`](https://github.com/deviantony/docker-elk/tree/searchguard): Search Guard support

---

## Philosophy

We aim at providing the simplest possible entry into the Elastic stack for anybody who feels like experimenting with
this powerful combo of technologies. This project's default configuration is purposely minimal and unopinionated. It
does not rely on any external dependency, and uses as little custom automation as necessary to get things up and
running.

Instead, we believe in good documentation so that you can use this repository as a template, tweak it, and make it _your
own_. [sherifabdlnaby/elastdocker][elastdocker] is one example among others of project that builds upon this idea.

---

## Contents

- [ACA-Py ELK Stack for demos](#aca-py-elk-stack-for-demos)
  - [run](#run)
  - [demos](#demos)
  - [multi-demo](#multi-demo)
- [Elastic stack (ELK) on Docker](#elastic-stack-elk-on-docker)
  - [Philosophy](#philosophy)
  - [Contents](#contents)
  - [Requirements](#requirements)
    - [Host setup](#host-setup)
    - [Docker Desktop](#docker-desktop)
      - [Windows](#windows)
      - [macOS](#macos)
  - [Usage](#usage)
    - [Bringing up the stack](#bringing-up-the-stack)
    - [Initial setup](#initial-setup)
      - [Setting up user authentication](#setting-up-user-authentication)
      - [Injecting data](#injecting-data)
    - [Cleanup](#cleanup)
    - [Version selection](#version-selection)
  - [Configuration](#configuration)
    - [How to configure Elasticsearch](#how-to-configure-elasticsearch)
    - [How to configure Kibana](#how-to-configure-kibana)
    - [How to configure Logstash](#how-to-configure-logstash)
    - [How to disable paid features](#how-to-disable-paid-features)
    - [How to scale out the Elasticsearch cluster](#how-to-scale-out-the-elasticsearch-cluster)
    - [How to re-execute the setup](#how-to-re-execute-the-setup)
    - [How to reset a password programmatically](#how-to-reset-a-password-programmatically)
  - [Extensibility](#extensibility)
    - [How to add plugins](#how-to-add-plugins)
    - [How to enable the provided extensions](#how-to-enable-the-provided-extensions)
  - [JVM tuning](#jvm-tuning)
    - [How to specify the amount of memory used by a service](#how-to-specify-the-amount-of-memory-used-by-a-service)
    - [How to enable a remote JMX connection to a service](#how-to-enable-a-remote-jmx-connection-to-a-service)
  - [Going further](#going-further)
    - [Plugins and integrations](#plugins-and-integrations)

## Requirements

### Host setup

* [Docker Engine][docker-install] version **18.06.0** or newer
* [Docker Compose][compose-install] version **1.26.0** or newer (including [Compose V2][compose-v2])
* 1.5 GB of RAM

> **Warning**  
> While Compose versions between **1.22.0** and **1.25.5** can technically run this stack as well, these versions have a
> [known issue](https://github.com/deviantony/docker-elk/pull/678#issuecomment-1055555368) which prevents them from
> parsing quoted values properly inside `.env` files.

> **Note**  
> Especially on Linux, make sure your user has the [required permissions][linux-postinstall] to interact with the Docker
> daemon.

By default, the stack exposes the following ports:

* 5044: Logstash Beats input
* 50000: Logstash TCP input
* 9600: Logstash monitoring API
* 9200: Elasticsearch HTTP
* 9300: Elasticsearch TCP transport
* 5601: Kibana

> **Warning**  
> Elasticsearch's [bootstrap checks][bootstrap-checks] were purposely disabled to facilitate the setup of the Elastic
> stack in development environments. For production setups, we recommend users to set up their host according to the
> instructions from the Elasticsearch documentation: [Important System Configuration][es-sys-config].

### Docker Desktop

#### Windows

If you are using the legacy Hyper-V mode of _Docker Desktop for Windows_, ensure [File Sharing][win-filesharing] is
enabled for the `C:` drive.

#### macOS

The default configuration of _Docker Desktop for Mac_ allows mounting files from `/Users/`, `/Volume/`, `/private/`,
`/tmp` and `/var/folders` exclusively. Make sure the repository is cloned in one of those locations or follow the
instructions from the [documentation][mac-filesharing] to add more locations.

## Usage

> **Warning**  
> You must rebuild the stack images with `docker-compose build` whenever you switch branch or update the
> [version](#version-selection) of an already existing stack.

### Bringing up the stack

Clone this repository onto the Docker host that will run the stack with the command below:

```sh
git clone https://github.com/deviantony/docker-elk.git
```

Then, start the stack components locally with Docker Compose:

```sh
docker-compose up
```

> **Note**  
> You can also run all services in the background (detached mode) by appending the `-d` flag to the above command.

Give Kibana about a minute to initialize, then access the Kibana web UI by opening <http://localhost:5601> in a web
browser and use the following (default) credentials to log in:

* user: *elastic*
* password: *changeme*

> **Note**  
> Upon the initial startup, the `elastic`, `logstash_internal` and `kibana_system` Elasticsearch users are initialized
> with the values of the passwords defined in the [`.env`](.env) file (_"changeme"_ by default). The first one is the
> [built-in superuser][builtin-users], the other two are used by Kibana and Logstash respectively to communicate with
> Elasticsearch. This task is only performed during the _initial_ startup of the stack. To change users' passwords
> _after_ they have been initialized, please refer to the instructions in the next section.

### Initial setup

#### Setting up user authentication

> **Note**  
> Refer to [Security settings in Elasticsearch][es-security] to disable authentication.

> **Warning**  
> Starting with Elastic v8.0.0, it is no longer possible to run Kibana using the bootstrapped privileged `elastic` user.

The _"changeme"_ password set by default for all aforementioned users is **unsecure**. For increased security, we will
reset the passwords of all aforementioned Elasticsearch users to random secrets.

1. Reset passwords for default users

    The commands below reset the passwords of the `elastic`, `logstash_internal` and `kibana_system` users. Take note
    of them.

    ```sh
    docker-compose exec elasticsearch bin/elasticsearch-reset-password --batch --user elastic
    ```

    ```sh
    docker-compose exec elasticsearch bin/elasticsearch-reset-password --batch --user logstash_internal
    ```

    ```sh
    docker-compose exec elasticsearch bin/elasticsearch-reset-password --batch --user kibana_system
    ```

    If the need for it arises (e.g. if you want to [collect monitoring information][ls-monitoring] through Beats and
    other components), feel free to repeat this operation at any time for the rest of the [built-in
    users][builtin-users].

1. Replace usernames and passwords in configuration files

    Replace the password of the `elastic` user inside the `.env` file with the password generated in the previous step.
    Its value isn't used by any core component, but [extensions](#how-to-enable-the-provided-extensions) use it to
    connect to Elasticsearch.

    > **Note**  
    > In case you don't plan on using any of the provided [extensions](#how-to-enable-the-provided-extensions), or
    > prefer to create your own roles and users to authenticate these services, it is safe to remove the
    > `ELASTIC_PASSWORD` entry from the `.env` file altogether after the stack has been initialized.

    Replace the password of the `logstash_internal` user inside the `.env` file with the password generated in the
    previous step. Its value is referenced inside the Logstash pipeline file (`logstash/pipeline/logstash.conf`).

    Replace the password of the `kibana_system` user inside the `.env` file with the password generated in the previous
    step. Its value is referenced inside the Kibana configuration file (`kibana/config/kibana.yml`).

    See the [Configuration](#configuration) section below for more information about these configuration files.

1. Restart Logstash and Kibana to re-connect to Elasticsearch using the new passwords

    ```sh
    docker-compose up -d logstash kibana
    ```

> **Note**  
> Learn more about the security of the Elastic stack at [Secure the Elastic Stack][sec-cluster].

#### Injecting data

Launch the Kibana web UI by opening <http://localhost:5601> in a web browser, and use the following credentials to log
in:

* user: *elastic*
* password: *\<your generated elastic password>*

Now that the stack is fully configured, you can go ahead and inject some log entries.

The shipped Logstash configuration allows you to send data over the TCP port 50000. For example, you can use one of the
following commands — depending on your installed version of `nc` (Netcat) — to ingest the content of the log file
`/path/to/logfile.log` in Elasticsearch, via Logstash:

```sh
# Execute `nc -h` to determine your `nc` version

cat /path/to/logfile.log | nc -q0 localhost 50000          # BSD
cat /path/to/logfile.log | nc -c localhost 50000           # GNU
cat /path/to/logfile.log | nc --send-only localhost 50000  # nmap
```

You can also load the sample data provided by your Kibana installation.

### Cleanup

Elasticsearch data is persisted inside a volume by default.

In order to entirely shutdown the stack and remove all persisted data, use the following Docker Compose command:

```sh
docker-compose down -v
```

### Version selection

This repository stays aligned with the latest version of the Elastic stack. The `main` branch tracks the current major
version (8.x).

To use a different version of the core Elastic components, simply change the version number inside the [`.env`](.env)
file. If you are upgrading an existing stack, remember to rebuild all container images using the `docker-compose build`
command.

> **Warning**  
> Always pay attention to the [official upgrade instructions][upgrade] for each individual component before performing a
> stack upgrade.

Older major versions are also supported on separate branches:

* [`release-7.x`](https://github.com/deviantony/docker-elk/tree/release-7.x): 7.x series
* [`release-6.x`](https://github.com/deviantony/docker-elk/tree/release-6.x): 6.x series (End-of-life)
* [`release-5.x`](https://github.com/deviantony/docker-elk/tree/release-5.x): 5.x series (End-of-life)

## Configuration

> **Note**  
> Configuration is not dynamically reloaded, you will need to restart individual components after any configuration
> change.

### How to configure Elasticsearch

The Elasticsearch configuration is stored in [`elasticsearch/config/elasticsearch.yml`][config-es].

You can also specify the options you want to override by setting environment variables inside the Compose file:

```yml
elasticsearch:

  environment:
    network.host: _non_loopback_
    cluster.name: my-cluster
```

Please refer to the following documentation page for more details about how to configure Elasticsearch inside Docker
containers: [Install Elasticsearch with Docker][es-docker].

### How to configure Kibana

The Kibana default configuration is stored in [`kibana/config/kibana.yml`][config-kbn].

You can also specify the options you want to override by setting environment variables inside the Compose file:

```yml
kibana:

  environment:
    SERVER_NAME: kibana.example.org
```

Please refer to the following documentation page for more details about how to configure Kibana inside Docker
containers: [Install Kibana with Docker][kbn-docker].

### How to configure Logstash

The Logstash configuration is stored in [`logstash/config/logstash.yml`][config-ls].

You can also specify the options you want to override by setting environment variables inside the Compose file:

```yml
logstash:

  environment:
    LOG_LEVEL: debug
```

Please refer to the following documentation page for more details about how to configure Logstash inside Docker
containers: [Configuring Logstash for Docker][ls-docker].

### How to disable paid features

Switch the value of Elasticsearch's `xpack.license.self_generated.type` setting from `trial` to `basic` (see [License
settings][license-settings]).

You can also cancel an ongoing trial before its expiry date — and thus revert to a basic license — either from the
[License Management][license-mngmt] panel of Kibana, or using Elasticsearch's [Licensing APIs][license-apis].

### How to scale out the Elasticsearch cluster

Follow the instructions from the Wiki: [Scaling out Elasticsearch](https://github.com/deviantony/docker-elk/wiki/Elasticsearch-cluster)

### How to re-execute the setup

To run the setup container again and re-initialize all users for which a password was defined inside the `.env` file,
delete its volume and "up" the `setup` Compose service again manually:

```console
$ docker-compose rm -f setup
 ⠿ Container docker-elk-setup-1  Removed
```

```console
$ docker volume rm docker-elk_setup
docker-elk_setup
```

```console
$ docker-compose up setup
 ⠿ Volume "docker-elk_setup"             Created
 ⠿ Container docker-elk-elasticsearch-1  Running
 ⠿ Container docker-elk-setup-1          Created
Attaching to docker-elk-setup-1
...
docker-elk-setup-1  | [+] User 'monitoring_internal'
docker-elk-setup-1  |    ⠿ User does not exist, creating
docker-elk-setup-1  | [+] User 'beats_system'
docker-elk-setup-1  |    ⠿ User exists, setting password
docker-elk-setup-1 exited with code 0
```

### How to reset a password programmatically

If for any reason your are unable to use Kibana to change the password of your users (including [built-in
users][builtin-users]), you can use the Elasticsearch API instead and achieve the same result.

In the example below, we reset the password of the `elastic` user (notice "/user/elastic" in the URL):

```sh
curl -XPOST -D- 'http://localhost:9200/_security/user/elastic/_password' \
    -H 'Content-Type: application/json' \
    -u elastic:<your current elastic password> \
    -d '{"password" : "<your new password>"}'
```

## Extensibility

### How to add plugins

To add plugins to any ELK component you have to:

1. Add a `RUN` statement to the corresponding `Dockerfile` (eg. `RUN logstash-plugin install logstash-filter-json`)
1. Add the associated plugin code configuration to the service configuration (eg. Logstash input/output)
1. Rebuild the images using the `docker-compose build` command

### How to enable the provided extensions

A few extensions are available inside the [`extensions`](extensions) directory. These extensions provide features which
are not part of the standard Elastic stack, but can be used to enrich it with extra integrations.

The documentation for these extensions is provided inside each individual subdirectory, on a per-extension basis. Some
of them require manual changes to the default ELK configuration.

## JVM tuning

### How to specify the amount of memory used by a service

The startup scripts for Elasticsearch and Logstash can append extra JVM options from the value of an environment
variable, allowing the user to adjust the amount of memory that can be used by each component:

| Service       | Environment variable |
|---------------|----------------------|
| Elasticsearch | ES_JAVA_OPTS         |
| Logstash      | LS_JAVA_OPTS         |

To accommodate environments where memory is scarce (Docker Desktop for Mac has only 2 GB available by default), the Heap
Size allocation is capped by default in the `docker-compose.yml` file to 512 MB for Elasticsearch and 256 MB for
Logstash. If you want to override the default JVM configuration, edit the matching environment variable(s) in the
`docker-compose.yml` file.

For example, to increase the maximum JVM Heap Size for Logstash:

```yml
logstash:

  environment:
    LS_JAVA_OPTS: -Xms1g -Xmx1g
```

When these options are not set:

* Elasticsearch starts with a JVM Heap Size that is [determined automatically][es-heap].
* Logstash starts with a fixed JVM Heap Size of 1 GB.

### How to enable a remote JMX connection to a service

As for the Java Heap memory (see above), you can specify JVM options to enable JMX and map the JMX port on the Docker
host.

Update the `{ES,LS}_JAVA_OPTS` environment variable with the following content (I've mapped the JMX service on the port
18080, you can change that). Do not forget to update the `-Djava.rmi.server.hostname` option with the IP address of your
Docker host (replace **DOCKER_HOST_IP**):

```yml
logstash:

  environment:
    LS_JAVA_OPTS: -Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.port=18080 -Dcom.sun.management.jmxremote.rmi.port=18080 -Djava.rmi.server.hostname=DOCKER_HOST_IP -Dcom.sun.management.jmxremote.local.only=false
```

## Going further

### Plugins and integrations

See the following Wiki pages:

* [External applications](https://github.com/deviantony/docker-elk/wiki/External-applications)
* [Popular integrations](https://github.com/deviantony/docker-elk/wiki/Popular-integrations)

[elk-stack]: https://www.elastic.co/what-is/elk-stack
[subscriptions]: https://www.elastic.co/subscriptions
[es-security]: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-settings.html
[license-settings]: https://www.elastic.co/guide/en/elasticsearch/reference/current/license-settings.html
[license-mngmt]: https://www.elastic.co/guide/en/kibana/current/managing-licenses.html
[license-apis]: https://www.elastic.co/guide/en/elasticsearch/reference/current/licensing-apis.html

[elastdocker]: https://github.com/sherifabdlnaby/elastdocker

[docker-install]: https://docs.docker.com/get-docker/
[compose-install]: https://docs.docker.com/compose/install/
[compose-v2]: https://docs.docker.com/compose/compose-v2/
[linux-postinstall]: https://docs.docker.com/engine/install/linux-postinstall/

[bootstrap-checks]: https://www.elastic.co/guide/en/elasticsearch/reference/current/bootstrap-checks.html
[es-sys-config]: https://www.elastic.co/guide/en/elasticsearch/reference/current/system-config.html
[es-heap]: https://www.elastic.co/guide/en/elasticsearch/reference/current/important-settings.html#heap-size-settings

[win-filesharing]: https://docs.docker.com/desktop/settings/windows/#file-sharing
[mac-filesharing]: https://docs.docker.com/desktop/settings/mac/#file-sharing

[builtin-users]: https://www.elastic.co/guide/en/elasticsearch/reference/current/built-in-users.html
[ls-monitoring]: https://www.elastic.co/guide/en/logstash/current/monitoring-with-metricbeat.html
[sec-cluster]: https://www.elastic.co/guide/en/elasticsearch/reference/current/secure-cluster.html

[connect-kibana]: https://www.elastic.co/guide/en/kibana/current/connect-to-elasticsearch.html
[index-pattern]: https://www.elastic.co/guide/en/kibana/current/index-patterns.html

[config-es]: ./elasticsearch/config/elasticsearch.yml
[config-kbn]: ./kibana/config/kibana.yml
[config-ls]: ./logstash/config/logstash.yml

[es-docker]: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html
[kbn-docker]: https://www.elastic.co/guide/en/kibana/current/docker.html
[ls-docker]: https://www.elastic.co/guide/en/logstash/current/docker-config.html

[upgrade]: https://www.elastic.co/guide/en/elasticsearch/reference/current/setup-upgrade.html
