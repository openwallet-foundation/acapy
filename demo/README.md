# Aries Cloud Agent Python (ACA-Py) Demos <!-- omit in toc -->

There are several demos available for ACA-Py mostly (but not only) aimed at developers learning how to deploy an instance of the agent and an ACA-Py controller to implement an application.

## Table of Contents <!-- omit in toc -->

- [The IIWBook Demo](#The-IIWBook-Demo)
- [The Alice/Faber Python demo](#The-AliceFaber-Python-demo)
  - [Running in a Browser](#Running-in-a-Browser)
  - [Running in Docker](#Running-in-Docker)
  - [Running Locally](#Running-Locally)
  - [Follow The Script](#Follow-The-Script)
- [Learning about the Alice/Faber code](#Learning-about-the-AliceFaber-code)
- [OpenAPI (Swagger) Demo](#OpenAPI-Swagger-Demo)
- [Performance Demo](#Performance-Demo)
- [Coding Challenge: Adding ACME](#Coding-Challenge-Adding-ACME)

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

Running the demo in docker requires having a `von-network` (a Hyperledger Indy public ledger sandbox) instance running in docker locally. See the [von-network](von-https://github.com/bcgov/von-network) readme file for more info.

Open three `bash` shells. For Windows users, `git-bash` is highly recommended. bash is the default shell in Linux and Mac terminal sessions.

In the first terminal window, start `von-network` using the instructions provided [here](https://github.com/bcgov/von-network#running-the-network-locally).

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

To run locally, complete the same steps above for running in docker, except use the following in place of the `run_demo` commands for starting the two agents.

``` bash
python faber-pg.py 8020
```

``` bash
python alice-pg.py 8030
```

Note that Alice and Faber will each use 5 ports, e.g. running ```python faber-pg.py 8020``` actually uses ports 8020 through 8024. Feel free to use different ports if you want.

To create the Alice/Faber wallets using postgres storage, just add the "--postgres" option when running the script.

Refer to the [Follow the Script](#follow-the-script) section below for further instructions.

### Follow The Script

With both the Alice and Faber agents started, go to the Faber terminal window. The Faber agent has created and displayed an invitation. Copy this invitation and paste it at the Alice prompt. The agents will connect and then show a menu of options:

Faber:

```
                 1 = send credential to Alice
                 2 = send proof request to Alice
                 3 = send a message to Alice
                 x = stop and exit
```

Alice:

```
                 3 = send a message to Faber
                 x = stop and exit
```

Feel free to use the "3" option to send messages back and forth between the agents. Fun, eh? Those are secure, end-to-end encrypted messages.

When ready to test the credentials exchange protocols, go to the Faber prompt, enter "1" to send a credential, and then "2" to request a proof.

You don't need to do anything with Alice's agent - her agent is implemented to automatically receive credentials and respond to proof requests.

## Learning about the Alice/Faber code

These Alice and Faber scripts implement the controller and run the agent as a sub-process (see the documentation for `aca-py`). The controller publishes a REST service to receive web hook callbacks from their agent.

The controllers for this demo can be found in the [alice.py](alice.py) and [faber.py](faber.py) files. You can watch [this video](https://zoom.us/recording/share/hfGCVMRsYWQcObOUjTQBd1vRxSH3sldO4QbEjWYjiS6wIumekTziMw) to get a start in understanding what is going on (and where) in the controllers.

## OpenAPI (Swagger) Demo

Developing an ACA-Py controller is much like developing a web app that uses a REST API. As you develop, you will want an easy way to test out the behaviour of the API. That's where the industry-standard OpenAPI (aka Swagger) UI comes in. ACA-Py (optionally) exposes an OpenAPI UI in ACA-Py that you can use to learn the ins and outs of the API. This [Aries OpenAPI demo](AriesOpenAPI.md) shows how you can use the OpenAPI UI with an ACA-Py agent by walking through the connectiing, issuing a credential, and presenting a proof sequence.

## Performance Demo

Another demo in this folder is [performance.py](performance.py), that is used to test out the performance of a couple of interacting agents. The script starts up two agents, initializes them and then runs through an interaction some number of times. In this demo, the test is issuing a credential and it is repeated 100 times.

To run the demo, make sure that you shut down both the Alice and Faber agents. Follow the steps to start the Alice/Faber demo running either in your browser or in docker, but:

* Don't start the second agent (`alice`) at all.
* When starting the first agent, replace the agent name (e.g. `faber`) with `performance`.

The script will start up both Alice and Faber agents, run the performance test, and spit out the performance results for you to review. Note that this is just an example of performance metrics tracking that can be done with ACA-Py.

## Coding Challenge: Adding ACME

Now that you have a solid foundation in using ACA-Py, time for a coding challenge. In this challenge, we extend the Alice-Faber command line demo by adding in ACME Corp, a place where Alice wants to work. The demo adds:

* ACME inviting Alice to connect
* ACME requesting a proof of her College degree
* ACME issuing Alice a credential after she is hired.

The framework for the code is in the [acme.py](acme.py) file, but the code is incomplete. Using the knowledge you gained from running demo and viewing the alice.py and faber.py code, fill in the blanks for the code.  When you are ready to test your work:

* Use the instructions above to start the Alice/Faber demo (above).
* Start another terminal session and run the same commands as for "Alice", but replace "alice" with "acme".

We'll post a way to get to a completed challenge here soon, and you can see how you did.
