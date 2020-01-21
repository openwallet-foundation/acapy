 # Web Demo

 This interactive web demo follows the [Alice/Faber Python demo](#the-alicefaber-python-demo) using a series of web controllers. The controllers are deisgned to provide an easy-to-use interface to showcase agent-to-agent interactions.
 
## Table of Contents

- [Prerequisites](#prerequisites)
    - [Docker and Docker Compose](#docker-and-docker-compose)
    - [VON Network](#von-network)
- [Running the Demo](#running-the-demo)
    - [Starting Up](#starting-up)
    - [Shutting Down and Cleaning Up](#shutting-down-and-cleaning-up)
- [Demo Walkthrough](#demo-walkthrough)

### Prerequisites

#### Docker and Docker Compose

The web demo requires `docker` and `docker-compose`. Please see the [Get Docker](https://docs.docker.com/get-docker/) information for your specific platform. We recommend installing `Docker Desktop` for [Mac](https://docs.docker.com/docker-for-mac/install/) and [Windows](https://docs.docker.com/docker-for-windows/install/), which will include everything you need to run the demo. Specific instructions for [Linux](https://docs.docker.com/install/linux/docker-ce/ubuntu/) are also included.

#### VON Network

This demo requires a Hyperledger Indy Node network. The [VON Network](https://github.com/bcgov/von-network) is a portable implementation that can be run locally for development purposes and comes included with a ledger browser. You will need to clone the [von-network](https://github.com/bcgov/von-network) repository, and follow the instructions for [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally).

_Note: You should already have `docker` and `docker-compose` installed from the [Docker and Docker Commpose](#docker-and-docker-compose) prerequisite above so you can start directly at step `3`._

**Note: the web demo will not work without a local VON Network running.**

### Running the Demo

#### Starting Up
 In a terminal navigate to the `demo/` directory and exectute the following command:

 ```
$ ./run_demo webstart
 ```

 _Note: If this is the first time running the demo, it may take some time to build docker images and start the necessary containers, networks, and volumes used in the demo._

#### Shutting Down and Cleaning Up

Once you are finished with the demo you can execute the following command from the `demo/` directory to stop and destroy all docker containers, networks, and volumes used in the demo:

```
$ ./run_demo webdown
```

 _Note: You will need to stop and clean up the running VON Network separately. Please see step `8` from [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) for the instructions on how to proceed._

### Demo Walkthrough

Instructions for the demo walkthrough can be viewed [here]().