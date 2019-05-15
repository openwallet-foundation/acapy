# TheOrgBook API

## Overview

The API provides an interface into the database for TheOrgBook.

## Development

The API is developed in Django/Python, using a Visual Studio 2017 project.

## Development

### libindy and the von-agent

This project depends on libindy and the von-agent (some custom agent code).

The von-agent can be installed into your virtual environment through the requirements.txt file for the python project.

The libindy binaries can be download (for Windows) from, https://repo.sovrin.org/windows/libindy/stable/, or built from source.  At the time of writing the project is using 1.1.0.  The binaries can be copied into the virual environment along side Python.

### Connecting to a Node Pool

The von-agent requires a valid genesis transaction file in order to connect to a node pool.  For development purposes we are running a node pool on Digital Ocean and the genesis transaction file for the pool can be downloaded from here; http://138.197.170.136/genesis.

Copy the content to a file on your system such as `C:/TheOrgBook/tob-api/app-root/genesis` or `/opt/app-root/genesis` and update the code in `.../TheOrgBook/tob-api/api/indy/agent.py` accordingly.  **Make sure this file and your changes do not get checked in.**

ToDo:
* Make this process easier for the developer.  Automate the configuration like we do for the database (database.py) and Haystack (haystack.py)
* Perhaps even download the genesis transaction file automatically if it does not exist.

### Local `.indy_client` Files

Local node pool and a wallet database will be created.  Due to limitations with the referance implementations of the code these files cannot be re-used between sessions or by more than one process.  Therefore you will need to manually delete these files between session.  On Windows these files will be under the `C:\Users\<UserName>\.indy_client` directory.

ToDo:
* Delete the folders in `C:\Users\<UserName>\.indy_client` between debug sessions automatically, since the agent cannot reuse the files at the moment (time of writing).

### Debugging - Visual Studio

Using the Visual Studio 2017 solution you can launch and debug the **entire** `tob-api` project right from Visual Studio.

Open the [tob-api Solution](./tob-api.sln), and press F5.

Visual Studio allows you to do things such as create and run migration right from the IDE, run and debug unit tests, set breakpoints, inspect variables, and step through code (including asynchronous calls).

### Debugging - Visual Studio Code

TheOrgBook is configured for debugging while running in its Docker environment using [Visual Studio Code](http://code.visualstudio.com). Currently, only code under the directory `/tob-api/api` is configured for debugging.

To run in debug mode, append DEBUG=true to your run command. For example, `./manage start seed=the_org_book_0000000000000000000 DEBUG=true`. This will start Django's development server instead of running Gunicorn. It will also start the debugger software to allow a remote debugger to be attached. Using Visual Studio Code's debugging feature, you can connect to application running in docker by navigating to the debug tab and running the "Python Experimental: Attach" debug configuration.

## Development Deployment Environment

To deploy TheOrgBook on an instance of OpenShift, see [the instructions](../RunningLocal.md) in the file RunningLocal.md.

- [Schema Spy](http://schema-spy-devex-von-dev.pathfinder.gov.bc.ca/)
- [Open API (Swagger) API Explorer](http://dev-demo-api.orgbook.gov.bc.ca/api/v1/)

## Database Migrations

Migrations are triggered automatically when the Django/Python container is deployed.  The process it triggered by wrapper code injected as part of the s2i-python-container build; https://github.com/sclorg/s2i-python-container/blob/master/3.6/s2i/bin/run

## ToDo:
- The auto-generated views are constructed using generics and a number of mixins.
  - Determine if there is a better way to do this.  Since it's not as clean as something constructed from ModelSerializer or HyperlinkedModelSerializer.
- Logging; ref gwells
