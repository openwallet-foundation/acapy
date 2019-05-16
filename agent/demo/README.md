# Running the Alice/Faber Python demo

## Running in Docker

### Requirements
The dockerized demo requires to have von-network instance running in Docker locally. See the [von-network](von-https://github.com/bcgov/von-network) readme file for more info.

### Running the dockerized demo
Open two shells (Git Bash is recommended for Windows) in the `indy-catalyst/agent/scripts` directory.

Start the `faber` agent by issuing the following command in the first shell: 
``` 
  ./run_demo faber 
```

Start the `alice` agent by issuing the following command in the first shell:
```
  ./run_demo alice
```

Refer to the section [follow the script](#follow-the-script) for further instructions. 

## Running locally
First you need to startup a local ledger (e.g. like this:  https://github.com/hyperledger/indy-sdk#1-starting-the-test-pool-on-localhost), and then open up two shell scripts and run:

```
python faber-pg.py <port#>
```

```
python alice-pg.py <port#>
```

Note that alice and faber will each use 5 ports, e.g. if you run ```python faber-pg.py 8020``` if will actually use 
ports 8020 through 8024.

To create the alice/faber wallets using postgres storage, just add the "--postgres" option when running the script.

These scripts run the agent as a sub-process (see the documentation for icatagent) and also publish a rest service to 
receive web hook callbacks from their agent

Refer to the section [follow the script](#follow-the-script)for further instructions.

## Follow The Script
Once Faber has started, it will create and display an invitation; copy this invitation and input at the Alice prompt.

The scripts will then request an option:

faber-pg.py - establishes a connection with Alice, and then provides a menu:

```
                 1 = send credential to Alice
                 2 = send proof request to Alice
                 3 = send a message to Alice
                 x = stop and exit
```

alice-pg.py - once a connection is established, this script provides a menu:

```
                 3 = send a message to Faber
                 x = stop and exit
```

At the Faber prompt, enter "1" to send a credential, and then "2" to request a proof.

You don't need to do anything with Alice - she will automatically receive Credentials and respond to Proofs.
