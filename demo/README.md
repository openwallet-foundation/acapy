# Running the Alice/Faber Python demo

## Running in Docker

### Requirements
The dockerized demo requires to have von-network instance running in Docker locally. See the [von-network](von-https://github.com/bcgov/von-network) readme file for more info.

### Running the dockerized demo
Open three `bash` shells. Git Bash is highly recommended for Windows, Linux and Mac terminal apps default to `bash`.

In the first terminal window, start `von-network` using the instructions provided [here](https://github.com/bcgov/von-network#running-the-network-locally).

In the second terminal, change directory into `scripts` directory of your clone of this repository. Start the `faber` agent by issuing the following command:

``` bash
  ./run_demo faber 
```

In the second terminal, change directory into `scripts` directory of your clone of this repository. Start the `faber` agent by issuing the following command:

``` bash
  ./run_demo alice
```

Jump to the [Follow The Script](#follow-the-script) section below for further instructions. 

## Running Locally

First you need to startup a local ledger (e.g. like this:  https://github.com/hyperledger/indy-sdk#1-starting-the-test-pool-on-localhost), and then open up two shell scripts and run:

``` bash
python faber-pg.py <port#>
```

``` bash
python alice-pg.py <port#>
```

Note that Alice and Faber will each use 5 ports, e.g. if you run ```python faber-pg.py 8020``` it will actually use ports 8020 through 8024.

To create the Alice/Faber wallets using postgres storage, just add the "--postgres" option when running the script.

These scripts implement the controller and run the agent as a sub-process (see the documentation for `aca-py`). The controller publishes a rest service to receive web hook callbacks from their agent.

Refer to the [Follow The Script](#follow-the-script) section below for further instructions.

## Follow The Script

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
