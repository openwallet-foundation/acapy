#  Running Local Agent macOS TLDR

This is a detailed description of the steps to run the Faber and Alice demos locally on macOS. This fills in and clarifies the instructions for running locally found in the [demo README.md](https://github.com/hyperledger/aries-cloudagent-python/blob/master/demo/README.md) in the running locally section  [here](https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo#Running-Locally).

This document also includes the instructions for setup and installation of the dependencies so it combines instructions found in other places in an attempt to make them more complete, consistent, and self-contained.

The BC Gov team was most kind in answering questions to help me fill in some of the blanks.

## Genesis

One item of information that I found most useful was some detail about the genesis file. An Indy Ledger requires a genesis file. The Hyperledger Indy-SDK repo at: https://github.com/hyperledger/indy-sdk creates a default set of genesis transactions when its run as a local ledger.  One of the things included in the genesis transactions are the IP addresses of the ledger nodes. Any agents that need to talk to these ledger nodes need to be using the same IP addressing as found in these default genesis transactions. This may be a problem for setups that include a mixture of local and docker running components because of the IP networking limitations of docker desktop on macOS. Specifically the file /.../demo/local_genesis.txt from the Aries Cloud Agent Python repo provides a set of matching genesis transactions in JSON format. These use localhost at 127.0.0.1:9702 - 9708 for the local indy nodes. If the genesis transactions do not match then it won't work. This problem was the root of many of my difficulties in getting a local setup to work. The instructions for running locally provided in the demo readme [here](https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo#Running-Locally) give the false impression that there is more than one way to run locally, that is, with either a local ledger or a von-network ledger. This is misleading due to the way the von-network docker IP addressing is configured. At the time of this writing, the docker IP configuration for the von-network local ledger won't work with a locally running agent on macOS. Some work is needed to fix the docker configuration to support localhost on macOS. Currently the only viable way to run local on macOS is to use a local indy-sdk ledger not the von-network docker ledger. This document provides local indy-sdk ledger instructions in detail.


## Dependency Setup

These instructions at the very least assume familiarity with the macOS command line using terminal and the command line tool "git" as well as python3, brew, and docker. Hyperledger Aries makes heavy use of the asyncio library in python 3.7.X.

This setup was performed on macOS Mojave 10.14.6 using Xcode version 10.3 with command line tools version 2354.

```bash
$ /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -version
Xcode 10.3
Build version 10G8

$ xcode-select --version
xcode-select version 2354.
```
To install the command line tools from the macOS terminal:

```bash
$ xcode-select --install

```

These instructions for running a local aires agent depend on the following additional components

- Homebrew package manager https://brew.sh 
- Docker Desktop for macOS 
    https://www.docker.com/products/docker-desktop 
- python 3.7.4 
- Hyperledger indy-sdk code repository 
    https://github.com/hyperledger/indy-sdk
- libindy.dylb built from source in the Hyperledger indy-sdk repository
- Hyperledger aries cloud agent (ACA) python repository 
    https://github.com/hyperledger/aries-cloudagent-python 
    
Most of the dependencies are installed using Homebrew or Python pip install.  In the instructions below terminal commands are prefixed with the terminal prompt character, '$', as a reminder that they are terminal commands but only the text after the prompt is entered on the command line.

### Homebrew

To install Homebrew, in terminal run:

```bash
$ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
$ brew --version
Homebrew 2.1.7

```
### Git

If git is not already installed one may use Homebrew via the CLI "brew" command to install git.

```bash
$ brew install git 
$ brew install git-extras git-flow
$ brew install git-credential-manager
```

Setup git dependencies on osxkeychain

```bash
$ git config --global credential.helper osxkeychain
```

### Docker Desktop

One can install Docker Desktop by downloading the [.dmg](https://hub.docker.com/?overlay=onboarding) installer file from the docker website, but I like using "brew cask" which installs non-command line macOS applications that can then  be updated using brew cask. The brew cask installer puts Docker Desktop in the /applications folder and it runs just like installing it from the .dmg.  Kitematic is a gui application from Docker for managing containers images and is optional part of Docker Desktop.

```bash
$ brew install bash-completion
$ brew cask install docker
$ brew cask install kitematic 
```
Start up docker desktop  by double clicking  /Applications/Docker.app and finish its configuration. One installed the "docker" command line app is available on the Terminal CLI.

```bash
$ docker version
Client: Docker Engine - Community
 Version:           18.09.2
 API version:       1.39
 Go version:        go1.10.8
 Git commit:        6247962
 Built:             Sun Feb 10 04:12:39 2019
 OS/Arch:           darwin/amd64
 Experimental:      false

Server: Docker Engine - Community
 Engine:
  Version:          18.09.2
  API version:      1.39 (minimum version 1.12)
  Go version:       go1.10.6
  Git commit:       6247962
  Built:            Sun Feb 10 04:13:06 2019
  OS/Arch:          linux/amd64
  Experimental:     false
```
There are some limitations of the MacOS Docker Desktop version relative to the full Linux version. One of these is that only one docker daemon is supported and there are limitations on the docker networking bridge interface with macOS. To read about this limitations see:
https://docs.docker.com/docker-for-mac/networking/

Add the directory or volume where you keep your code repositories to the file sharing tab of Docker Desktop Preferences so that docker can find them. These will be the repositories installed below.


### Python 3.7.X

Now we can install Python3 using brew.  The instructions here install Python3 using brew into /usr/local.  


In terminal run:

```bash
$ brew install python3
```


Also upgrade to the latest version of the pip, setuptools, and wheel packages:

```bash
$ pip3 install --upgrade pip setuptools wheel
```

Try out the python3 REPL 

```bash
$ python3
Python 3.7.4 (default, Jul  9 2019, 18:13:23) 
[Clang 10.0.1 (clang-1001.0.46.4)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> 

```

Remember to use "pip3" to install Python packages and not the system default pip which is a different python.

You may instead want to use a python virtual environment to house the Python3 you are using for Indy Aries development.

The following sets up a python3 virtual environment in a subdirectory "myvenv"

```bash
$ python3 -m venv myvenv

```

To activate the virtual environment
```bash
$ source myvenv/bin/active
```

To deactivate
```bash
$ deactivate
``` 

There are numerous tutorials on using venv in python 3.5 or later which are beyond the scope of this document. 
See:

https://realpython.com/python-virtual-environments-a-primer/

https://towardsdatascience.com/comparing-python-virtual-environment-tools-9a6543643a44


### Indy-SDK Repository and libindy.dylb

Use git to clone (or fork and clone) the indy-sdk repository at https://github.com/hyperledger/indy-sdk 

```bash
$ git clone https://github.com/hyperledger/indy-sdk.git
```

Next we will install the build dependencies for libindy.

#### Rust Compiler

The first dependency is "rustup" which is a rust compiler manager. We need this because at the time of this writing there was an incompatibility between  rustc 1.36 (default latest version) and rusqlite 0.13.0 used by libindy. Using rustup we can easily downgrade to an earlier version of rustc and cargo.

```bash
$ brew install rustup
$ rustup-init -y
```

Now use rustup to install rustc 1.35 and cargo 1.35

```bash
$ rustup install 1.35.0
$ rustup override set 1.35.0
$ rustc --version
rustc 1.35.0 (3c235d560 2019-05-20)
$ cargo version
cargo 1.35.0 (6f3e9c367 2019-04-04)

```

Because I had to try different versions of rust to find the one that worked I have multiple version installed. To see what's installed use rustup show.

```bash
$ rustup show
$<2>Default host: $<2>x86_64-apple-darwin

$<2>installed toolchains
--------------------

$<2>stable-x86_64-apple-darwin
1.34.0-x86_64-apple-darwin
1.35.0-x86_64-apple-darwin

$<2>active toolchain
----------------

$<2>1.35.0-x86_64-apple-darwin (directory override for '/Data/Code/public/hyperledger/aries/cloudagentpy')
rustc 1.35.0 (3c235d560 2019-05-20)

```

#### Other Libraries

Use brew to install the other dependant libraries

```bash
$ brew install pkg-config
$ brew install libsodium
$ brew install automake 
$ brew install autoconf
$ brew install cmake
$ brew install zeromq
```

#### Brew version of OpenSSL

By default macOS comes with its own version of OpenSSL but we can install the latest one one using brew and setup our environment to use it instead..

```bash
$ brew install openssl
```
Now setup the local environment variable OPENSSL_DIR so that the compile step will use it. Copy and paste the following into the terminal window.

```bash
###

for version in `ls -t /usr/local/Cellar/openssl/`; do
     export OPENSSL_DIR=/usr/local/Cellar/openssl/$versionls
     break
done

###
```

Confirm that we did it right.

```bash
$echo  $OPENSSL_DIR
/usr/local/Cellar/openssl/1.0.2s
```

#### Setup the rest of the build environment

Set these additional environment variables

```bash
$ export PKG_CONFIG_ALLOW_CROSS=1
$ export CARGO_INCREMENTAL=1
$ export RUST_LOG=indy=trace
$ export RUST_TEST_THREADS=1
```

### Build libindy.dylb

Change direcctory to the libindy subdirectory and build libindy.dylb with cargo.

```bash
$ cd ./indy-sdk/libindy
$ cargo build
```

Assuming all goes well you should see something like this

```bash

....
Compiling libindy v1.10.0 
    Finished dev [unoptimized + debuginfo] target(s) in 26.73s
```

The library libindy.dylb should be found in

```bash
/.../indy-sdk/libindy/target/debug/libindy.dylib
```
Where the /.../ represents your system's path to your copy of the indy-sdk repo

Now we put a symlink to this library in /usr/local/lib so the python wrapper can find it. Replace /.../ with the path on your computer.

```bash
$ ln -s /.../indy-sdk/libindy/target/debug/libindy.dylib /usr/local/lib/libindy.dylib

$ ll /usr/local/lib/libindy.dylib
lrwxrwxr-x  1 samuel  admin  78 Jul 15 17:26 libindy.dylib@ -> /.../indy-sdk/libindy/target/debug/libindy.dylib

```

### Build the indy CLI

Now we can also build the indy-sdk client CLI.

```bash
$ export LIBRARY_PATH=/../indy-sdk/libindy/target/debug/
$ cd /.../indy-sdk/cli
$ cargo build
```

To run the cli:

```bash
$ cd /.../indy-sdk/cli/target/debug/
$ ./indy-cli
```


### Install Python Wrapper for indy-sdk

Use pip3 to install the python wrapper for the indy-sdk from PyPi.

```bash
$ pip3 install python3-indy
```

Test import the wrapper in Python to make sure the wrapper can find libindy.dylb

```bash
$ python3
Python 3.7.4 (default, Jul  9 2019, 18:13:23) 
[Clang 10.0.1 (clang-1001.0.46.4)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import indy
>>> help(indy)
Help on package indy:

NAME
    indy

```

Yippee! now you have a local build of libindy used by the indy python module.


## Hyperledger Aries Cloud Agent Python Setup

Now we can setup the Hyperledger Aries Repository.

The repository is found here:

https://github.com/hyperledger/aries-cloudagent-python 

There are a couple of python dependencies that need to be installed. These are prompt_toolkit and web.py

```bash
$ pip3 install prompt_toolkit
```

In order for web.py to work with Python3 we have to install it from source. In an appropriate directory clone the web.py repository and install from source.

```bash
$ git clone git://github.com/webpy/webpy.git
$ pip3 install -e webpy
```


BTW using the -e option on pip3 installs symlinks to the repository code instead of copying it in the python library directly. This means that changes to the repository code will be picked up automatically without reinstalling. This may be useful the repo is used in active development. Leave off the -e if that is not what you want.



Now git clone (or fork and clone) the ACA python repository into an appropriate directory.

```bash
$ git clone https://github.com/hyperledger/aries-cloudagent-python.git

```

Now we can install the python module
```bash
$ pip3 install -e /..../pathofACAPYrepo
```

This installs the python package "aries_cloudagent" and the CLI for the agent package
called aca-py.

To test

```bash
$ python3
Python 3.7.4 (default, Jul  9 2019, 18:13:23) 
[Clang 10.0.1 (clang-1001.0.46.4)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import aries_cloudagent
>>> aries_cloudagent.version.__version__
'0.2.1'
```


```bash
$ aca-py -h
usage: aca-py [-h] -it <module> <host> <port> -ot <module>
              [--log-config <path-to-config>] [--log-level <log-level>]
              [-e <endpoint>] [-l <label>] [--seed <wallet-seed>]
              [--storage-type <storage-type>] [--wallet-key <wallet-key>]
              [--wallet-name <wallet-name>] [--wallet-type <wallet-type>]
              [--wallet-storage-type <storage-type>]
              [--wallet-storage-config <storage-config>]
              [--wallet-storage-creds <storage-creds>]
              [--pool-name <pool-name>]
              [--genesis-transactions <genesis-transactions>]
              [--genesis-url <genesis-url>] [--admin <host> <port>]
              [--admin-api-key <api-key>] [--admin-insecure-mode] [--debug]
              [--debug-seed <debug-did-seed>] [--debug-connections]
              [--public-invites] [--auto-accept-invites]
              [--auto-accept-requests] [--auto-ping-connection]
              [--auto-respond-messages] [--auto-respond-credential-offer]
              [--auto-store-credential] [--auto-respond-presentation-request]
              [--auto-verify-presentation] [--no-receive-invites]
              [--help-link <help-url>] [--invite] [--timing]
              [--protocol <module>] [--webhook-url <url>]
```

### Install Von-Network Indy Ledger Repository



This VON Network repository includes a web server that we need in order to browse our local indy ledger from the indy-sdk repository. This allows the agents to get the genesis transactions from the ledger. 

The Von-Network indy ledger repository is found at 

https://github.com/bcgov/von-network 

First install a couple of dependencies.

```bash
$ pip3 install aiohttp_jinja2
$ pip3 install aiosqlite
```


Now clone (or fork and clone) the von-network repo.

```bash
$ git clone https://github.com/bcgov/von-network.git
```


## Running the Demos Locally

Now that we have installed all the dependencies we can now run local versions of the demo agents. This allows us to do development and use local debuggers.  If instead we were to run the docker versions of the agents the only way to debug would be to use a remote debug setup if supported by our IDE. The [ACA Python](https://github.com/hyperledger/aries-cloudagent-python) repo comes with support via a configuration command to use Microsoft Visual Studio in remote debug mode. Other IDE's will require some additional setup (not provided) to run in remote debug mode with the docker version of the agents. The advantage of these instructions here is that you may use your IDE's normal local debug mode to debug the agent code.

### Run a local indy ledger

Start up a local indy ledger in docker using your local copy of the indy-sdk repo.

```bash
$ cd /.../indy-sdk/
$ docker build -f ci/indy-pool.dockerfile -t indy_pool .
$ docker run -itd -p 9701-9708:9701-9708 indy_pool
```

This runs the ledger in detached mode. To run it attached so you can view log messages just omit the -d option.

```bash
$ docker run -it -p 9701-9708:9701-9708 indy_pool
```

Use docker container ls to get the name or id of the container and docker container stop to stop it.

```bash
$ docker container ls
 ...  xenodochial_hermann
$ docker container stop xenodochial_hermann
```


### Run von-network web server to browse the local indy ledger

As mentioned above the von-network repo includes code for a web server that the agents access and we may also access with a web browser to browse the local indy ledger. We need to tell the web server what genesis transactions to use. This has a little bit of magic to it. It just so happens that the same genesis transactions that the indy-sdk defaults too are provided by the local-genesis.txt file in the ACA python repo in the demos directory.

```bash
/.../demo/local-genesis.txt
```
where "/.../" represents the path on your computer to your cloned copy of the ACA python repository.

We need to set an environment variable with the full path to this local-genesis.txt file so the web server will be able to find the local indy ledger nodes and also serve up the correct genesis transactions. The genesis transactions include the IP addresses on localhost (127.0.01) of the indy ledger nodes. The web server uses these to attach to the local indy ledger nodes.  We do this by including the assignment of the environment variables within the command. We need to first navigate to the von-network repository. 

In a new terminal run the server. The commands follow:


```bash
$ cd /.../von-network
$ GENESIS_FILE=/Data/Code/public/hyperledger/aries/cloudagentpy/demo/local-genesis.txt PORT=9000 REGISTER_NEW_DIDS=true python3 -m server.server
```

The server.server command line also set the web server port to 9000 and enables registering new DIDs.
Once running we can navigate a web browser to
http://localhost:9000 
to view the status of the local indy ledger.


Hit CNTL-C a couple of times to stop the server.


### Run postgres database server for agent wallets

A clean way to run the agents is to use a docker postgres database to store the entries in the wallets. Then when we delete the docker container the wallet storage is also deleted. Otherwise the wallets are stored in 
~/.indy_client/wallet

The agents are already configured hardcoded to use the POSTGRES_PASSWORD provided below.

```bash
$ docker run --name some-postgres -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres
```

To run attached
```bash
$ docker run --name some-postgres -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 postgres
```

To stop and then remove the postgres container.

```bash
$ docker container ls
  ... some-postgres

$ docker container stop some-postgres
$ docker container rm some-postgres
```

### Run Demos

Finally we can now run the demos locally. We have to provide each demo agent with the URL of the von-network web server via the environment variable LEDGER_URL so that it can then get a copy of the genesis transactions from the web server. The genesis transactions include the addresses of the local indy ledger nodes. Under the hood, giving each agent a value for LEDGER_URL also allows the agent to assign a value to the environment variable GENESIS_URL.  We also instruct provision the agent to use postgres for its wallet via the environment variable DEFAULT_POSTGRES=true. 

We run each agent in a new terminal window so we can see the interactive prompts.

The command to run Faber is as follows:

```bash
$ cd /.../demo/
$ LEDGER_URL=http://localhost:9000 DEFAULT_POSTGRES=true python3 -m runners.faber --port 8020 
```
The GENESIS_URL variable is set internally by faber to be
http://localhost:9000/genesis

Likewise the command to run Alice is as follows:

```bash
$ cd /.../demo/
$ LEDGER_URL=http://localhost:9000 DEFAULT_POSTGRES=true python3 -m runners.alice --port 8030 
```

Now at this point one can resume following the instructions here

https://github.com/hyperledger/aries-cloudagent-python/tree/master/demo#Follow-The-Script

Hope this helps. Enjoy.

## Additional Info

The demo agents in /demo/runners/faber.py and /demo/runners/alice.py are actually agents and controllers combined. This may be confusing because the documentation architecture diagrams show each controller running as a distinct standalone process. This may be the eventual intent but they are not yet separated out in the demo version. The agent code library also provides controller functionality. 

For example, runners.faber.main listens on webhooks as a controller
for events generated by an agent as in

```python
await agent.listen_webhooks(start_port + 2)
```

But also provisions the agent as a subprocess as in

```python
await agent.start_process()
```

The agent sub-process generates the events that are sent to the webhook url. 

The clean separation of concerns between generic agents and application specific controllers is not yet fully reflected in the organization of the code.

