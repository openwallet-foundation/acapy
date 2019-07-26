# Aries Cloud Agent Python (ACA-Py) Demos <!-- omit in toc -->

There are several demos available for ACA-Py mostly (but not only) aimed at developers learning how to deploy an instance of the agent and an ACA-Py controller to implement an application.

## Table of Contents <!-- omit in toc -->

- [The IIWBook Demo](#the-iiwbook-demo)
- [The Alice/Faber Python demo](#the-alicefaber-python-demo)
  - [Running in a Browser](#running-in-a-browser)
  - [Running in Docker](#running-in-docker)
  - [Running Locally](#running-locally)
    - [Installing Prerequisites](#installing-prerequisites)
    - [Start a local indy ledger](#start-a-local-indy-ledger)
    - [Genesis File handling](#genesis-file-handling)
    - [Run a local Postgres instance](#run-a-local-postgres-instance)
    - [Optional: Run a von-network ledger browser](#optional-run-a-von-network-ledger-browser)
    - [Run the Alice and Faber Controllers/Agents](#run-the-alice-and-faber-controllersagents)
  - [Follow The Script](#follow-the-script)
- [Learning about the Alice/Faber code](#learning-about-the-alicefaber-code)
- [OpenAPI (Swagger) Demo](#openapi-swagger-demo)
- [Performance Demo](#performance-demo)
- [Coding Challenge: Adding ACME](#coding-challenge-adding-acme)

## The IIWBook Demo

The IIWBook demo is a real (play) self-sovereign identity demonstration. During the demo, you will get a mobile agent (sorry - IOS only right now), and use that agent to connect with several enterprise services to collect and prove credentials. The two services in the demo (the [email verification service](https://github.com/bcgov/indy-email-verification) and [IIWBook](https://github.com/bcgov/iiwbook)) are both instances of ACA-Py, and all the agents are using DIDComm to communicate. Learn about and run the demo at [https://vonx.io/how_to/iiwbook](https://vonx.io/how_to/iiwbook). Developers, when you are ready, check out the code in the repos of the two services to see how they implement Django web server-based controller and agent.

## The Alice/Faber Python demo

The Alice/Faber demo is the (in)famous first verifiable credentials demo. Alice, a former student of Faber College ("Knowledge is Good"), connects with the College, is issued a credential about her degree and then is asked by the College for a proof. There are a variety of ways of running the demo. The easiest is in your browser using a site ("Play with VON") that let's you run docker containers without installing anything. Alternatively, you can run locally on docker (our recommendation), or using python on your local machine. Each approach is covered below.

### Running in a Browser

In your browser, go to the docker playground service [Play with VON](http://play-with-von.vonx.io) (from the BC Gov). On the title screen, click "Start". On the next screen, click (in the left menu) "+Add a new instance".  That will start up a terminal in your browser. Run the following commands to start the Faber agent:

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo faber
```

Now to start Alice's agent. Click the "+Add a new instance" button again to open another terminal session. Run the following commands to start Alice's agent:

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo alice
```

Alice's agent is now running.

Jump to the [Follow the Script](#follow-the-script) section below for further instructions.

### Running in Docker

Running the demo in docker requires having a `von-network` (a Hyperledger Indy public ledger sandbox) instance running in docker locally. See the [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) section of the `von-network` readme file for more info.

Open three `bash` shells. For Windows users, `git-bash` is highly recommended. bash is the default shell in Linux and Mac terminal sessions.

In the first terminal window, start `von-network` by following the [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) instructions.

In the second terminal, change directory into `demo` directory of your clone of this repository. Start the `faber` agent by issuing the following command:

``` bash
  ./run_demo faber 
```

In the third terminal, change directory into `demo` directory of your clone of this repository. Start the `alice` agent by issuing the following command:

``` bash
  ./run_demo alice
```

Jump to the [Follow the Script](#follow-the-script) section below for further instructions. 

### Running Locally

The following is an approach to to running the Alice and Faber demo using Python3 running on a bare machine. There are other ways to run the components, but this covers the general approach.

#### Installing Prerequisites

We assume you have a running Python 3 environment.  To install the prerequisites specific to running the agent/controller examples in your Python environment, run the following command from this repo's `demo` folder. The precise command to run may vary based on your Python environment setup.

``` bash
pip3 install -r demo/requirements.txt
```

While that process will include the installation of the Indy python prerequisite, you still have to build and install the `libindy` code for your platform. Follow the [installation instructions](https://github.com/hyperledger/indy-sdk#installing-the-sdk) in the indy-sdk repo for your platform.

#### Start a local indy ledger

Use instructions in the [indy-sdk repo](https://github.com/hyperledger/indy-sdk#how-to-start-local-nodes-pool-with-docker) to run a local ledger.

#### Genesis File handling

An Aries agent (or other client) connecting to an Indy ledger must know the contents of the `genesis` file for the ledger. The genesis file lets the agent/client know the IP addresses of the initial nodes of the ledger, and the agent/client sends ledger requests to those IP addresses. When using the `indy-sdk` ledger, look for the instructions in that repo for how to find/update the ledger genesis file, and note the path to that file on your local system.

The envrionment variable `GENESIS_FILE` is used to let the Aries demo agents know the location of the genesis file. Use the path to that file as value of the `GENESIS_FILE` environment variable in the instructions below. You might want to copy that file to be local to the demo so the path is shorter.

#### Run a local Postgres instance

The demo uses the postgres database the wallet persistence. Use the Docker Hub certified postgres image to start up a postgres instance to be used for the wallet storage:

``` bash
docker run --name some-postgres -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres -c 'log_statement=all' -c 'logging_collector=on' -c 'log_destination=stderr'
```

#### Optional: Run a von-network ledger browser

If you want to be able to browse your local ledger as you run the demo, clone the [von-network](https://github.com/bcgov/von-network) repo, go into the root of the cloned instance and run the following command, replacing the `/path/to/local-genesis.txt` with a path to the same genesis file as was used in starting the ledger.

``` bash
GENESIS_FILE=/path/to/local-genesis.txt PORT=9000 REGISTER_NEW_DIDS=true python -m server.server
```

#### Run the Alice and Faber Controllers/Agents

With the rest of the pieces running, you can run the Alice and Faber controllers and agents. To do so, `cd` into the `demo` folder your clone of this repo in two terminal windows and run the following, replacing the `/path/to/local-genesis.txt`.

``` bash
GENESIS_FILE=/path/to/local-genesis.txt DEFAULT_POSTGRES=true python3 -m runners.faber --port 8020
```

``` bash
GENESIS_FILE=/path/to/local-genesis.txt DEFAULT_POSTGRES=true python3 -m runners.alice --port 8030
```

Note that Alice and Faber will each use 5 ports, e.g. using the parameter `... --port 8020` actually uses ports 8020 through 8024. Feel free to use different ports if you want.

Everything running?  See the [Follow the Script](#follow-the-script) section below for further instructions.

If the demo fails with an error that references the genesis file, a timeout connecting to the Indy Pool, or an Indy `307` error, it's likely a problem with the genesis file handling. Things to check:

- Review the instructions for running the ledger with `indy-sdk`. Is it running properly?
- Is the `/path/to/local-genesis.txt` file correct in your start commands?
- Look at the IP addresses in the genesis file you are using, and make sure that those IP addresses are accessible from the location you are running the Aries demo
- Check to make sure that all of the nodes of the ledger started. We've seen examples of only some of the nodes starting up, triggering an Indy `307` error.

### Follow The Script

With both the Alice and Faber agents started, go to the Faber terminal window. The Faber agent has created and displayed an invitation. Copy this invitation and paste it at the Alice prompt. The agents will connect and then show a menu of options:

Faber:

```
    1 = Issue Credential - send a credential to Alice
    2 = Send Proof Request - send a proof request to Alice
    3 = Send Message - send a message to Alice
    x = Exit - Stop and exit
```

Alice:

```
    3 = Send Message - send a message to Faber
    4 = Input New Invitation
    x = Exit - stop and exit
```

Feel free to use the "3" option to send messages back and forth between the agents. Fun, eh? Those are secure, end-to-end encrypted messages.

When ready to test the credentials exchange protocols, go to the Faber prompt, enter "1" to send a credential, and then "2" to request a proof.

You don't need to do anything with Alice's agent - her agent is implemented to automatically receive credentials and respond to proof requests.

## Learning about the Alice/Faber code

These Alice and Faber scripts (in the `demo/runners` folder) implement the controller and run the agent as a sub-process (see the documentation for `aca-py`). The controller publishes a REST service to receive web hook callbacks from their agent. Note that this architecture, running the agent as a sub-process, is a variation on the documented architecture of running the controller and agent as separate processes/containers.

The controllers for this demo can be found in the [alice.py](runners/alice.py) and [faber.py](runners/faber.py) files. You can watch [this video](https://zoom.us/recording/share/hfGCVMRsYWQcObOUjTQBd1vRxSH3sldO4QbEjWYjiS6wIumekTziMw) to get a start in understanding what is going on (and where) in the controllers.

## OpenAPI (Swagger) Demo

Developing an ACA-Py controller is much like developing a web app that uses a REST API. As you develop, you will want an easy way to test out the behaviour of the API. That's where the industry-standard OpenAPI (aka Swagger) UI comes in. ACA-Py (optionally) exposes an OpenAPI UI in ACA-Py that you can use to learn the ins and outs of the API. This [Aries OpenAPI demo](AriesOpenAPIDemo.md) shows how you can use the OpenAPI UI with an ACA-Py agent by walking through the connectiing, issuing a credential, and presenting a proof sequence.

## Performance Demo

Another example in the `demo/runners` folder is [performance.py](runners/performance.py), that is used to test out the performance of interacting agents. The script starts up agents for Alice and Faber, initializes them, and then runs through an interaction some number of times. In this case, Faber issues a credential to Alice 300 times.

To run the demo, make sure that you shut down any running Alice/Faber agents. Then, follow the same steps to start the Alice/Faber demo, but:

* When starting the first agent, replace the agent name (e.g. `faber`) with `performance`.
* Don't start the second agent (`alice`) at all.

The script starts both agents, runs the performance test, spits out performance results and shuts down the agents. Note that this is just one demonstration of how performance metrics tracking can be done with ACA-Py.

A second version of the performance test can be run by adding the parameter `--router` to the invocation above. The parameter triggers the example to run with Alice using a routing agent such that all messages pass through the routing agent between Alice and Faber. This is a good, simple example of how routing can be implemented with DIDComm agents.

## Coding Challenge: Adding ACME

Now that you have a solid foundation in using ACA-Py, time for a coding challenge. In this challenge, we extend the Alice-Faber command line demo by adding in ACME Corp, a place where Alice wants to work. The demo adds:

* ACME inviting Alice to connect
* ACME requesting a proof of her College degree
* ACME issuing Alice a credential after she is hired.

The framework for the code is in the [acme.py](runners/acme.py) file, but the code is incomplete. Using the knowledge you gained from running demo and viewing the alice.py and faber.py code, fill in the blanks for the code.  When you are ready to test your work:

* Use the instructions above to start the Alice/Faber demo (above).
* Start another terminal session and run the same commands as for "Alice", but replace "alice" with "acme".

All done? Checkout how we added the missing code segments [here](AcmeDemoWorkshop.md).
