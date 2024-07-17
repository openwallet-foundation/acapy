# ACA-Py Development with Dev Container

The following guide will get you up and running and developing/debugging ACA-Py as quickly as possible.
We provide a [`devcontainer`](https://containers.dev) and will use [`VS Code`](https://code.visualstudio.com) to illustrate.

By no means is ACA-Py limited to these tools; they are merely examples.  

**For information on running demos and tests using provided shell scripts, see [DevReadMe](./DevReadMe.md) readme.**

## Caveats

The primary use case for this `devcontainer` is for developing, debugging and unit testing (pytest) the [aries_cloudagent](https://github.com/hyperledger/aries-cloudagent-python/tree/main/aries_cloudagent) source code.

There are limitations running this devcontainer, such as all networking is within this container. This container has [docker-in-docker](https://github.com/microsoft/vscode-dev-containers/blob/main/script-library/docs/docker-in-docker.md) which allows running demos, building docker images, running `docker compose` all within this container.

### Files

The `.devcontainer` folder contains the `devcontainer.json` file which defines this container. We are using a `Dockerfile` and `post-install.sh` to build and configure the container run image. The `Dockerfile` is simple but in place for simplifying image enhancements (ex. adding `poetry` to the image). The `post-install.sh` will install some additional development libraries (including for BDD support).

## Devcontainer

> What are Development Containers?
>
> A Development Container (or Dev Container for short) allows you to use a container as a full-featured development environment. It can be used to run an application, to separate tools, libraries, or runtimes needed for working with a codebase, and to aid in continuous integration and testing. Dev containers can be run locally or remotely, in a private or public cloud.

see [https://containers.dev](https://containers.dev).

In this guide, we will use [Docker](https://www.docker.com) and [Visual Studio Code](https://code.visualstudio.com) with the [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) installed, please set your machine up with those. As of writing, we used the following:

- Docker Version: 20.10.24
- VS Code Version: 1.79.0
- Dev Container Extension Version: v0.295.0

### Open ACA-Py in the devcontainer

To open ACA-Py in a devcontainer, we open the *root* of this repository. We can open in 2 ways:

1. Open Visual Studio Code, and use the Command Palette and use `Dev Containers: Open Folder in Container...`
2. Open Visual Studio Code and `File|Open Folder...`, you should be prompted to `Reopen in Container`.

*NOTE* follow any prompts to install `Python Extension` or reload window for `Pylance` when first building the container.

*ADDITIONAL NOTE* we advise that after each time you rebuild the container that you also perform: `Developer: Reload Window` as some extensions seem to require this in order to work as expected.

#### devcontainer.json

When the [.devcontainer/devcontainer.json](https://github.com/hyperledger/aries-cloudagent-python/blob/main/.devcontainer/devcontainer.json) is opened, you will see it building... it is building a Python 3.12 image (bash shell) and loading it with all the ACA-Py requirements. We also load a few Visual Studio settings (for running Pytests and formatting with Ruff).

### Poetry

The Python libraries / dependencies are installed using [`poetry`](https://python-poetry.org). For the devcontainer, we *DO NOT* use virtual environments. This means you will not see or need venv prompts in the terminals and you will not need to run tasks through poetry (ie. `poetry run ruff check .`). If you need to add new dependencies, you will need to add the dependency via poetry *AND* you should rebuild your devcontainer.

In VS Code, open a Terminal, you should be able to run the following commands:

```bash
python -m aries_cloudagent -v
cd aries_cloudagent
ruff check .
poetry --version
```

The first command should show you that `aries_cloudagent` module is loaded (ACA-Py). The others are examples of code quality checks that ACA-Py does on commits (if you have [`precommit`](https://pre-commit.com) installed) and Pull Requests.

When running `ruff check .` in the terminal, you may see `error: Failed to initialize cache at /.ruff_cache: Permission denied (os error 13)` - that's ok. If there are actual ruff errors, you should see something like:

```bash
error: Failed to initialize cache at /.ruff_cache: Permission denied (os error 13)
admin/base_server.py:7:7: D101 Missing docstring in public class
Found 1 error.
```

#### extensions

We have added Ruff extensions. Although we have added launch settings for both `ruff`, you can also use the extension commands from the command palette.

- `ruff (format) - aries_cloudagent`

More importantly, these extensions are now added to document save, so files will be formatted and checked. We advise that after each time you rebuild the container that you also perform: `Developer: Reload Window` to ensure the extensions are loaded correctly.

### Running docker-in-docker demos

Start by running a von-network inside your dev container. Or connect to a hosted ledger. You will need to adjust the ledger configurations if you do this.

```sh
git clone https://github.com/bcgov/von-network
cd von-network
./manage build
./manage start
cd ..
```

If you want to have revocation then start up a tails server in your dev container. Or connect to a hosted tails server. Once again you will need to adjust the configurations.

```sh
git clone https://github.com/bcgov/indy-tails-server.git
cd indy-tails-server/docker
./manage build
./manage start
cd ../..
```

```sh
# open a terminal in VS Code...
cd demo
./run_demo faber
# open a second terminal in VS Code...
cd demo
./run_demo alice
# follow the script...
```

## Further Reading and Links

- Development Containers (devcontainers): [https://containers.dev](https://containers.dev)
- Visual Studio Code: [https://code.visualstudio.com](https://code.visualstudio.com)
- Dev Containers Extension: [marketplace.visualstudio.com](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- Docker: [https://www.docker.com](https://www.docker.com)
- Docker Compose: [https://docs.docker.com/compose/](https://docs.docker.com/compose/)

## ACA-Py Debugging

To better illustrate debugging pytests and ACA-Py runtime code, let's add some run/debug configurations to VS Code. If you have your own `launch.json` and `settings.json`, please cut and paste what you want/need.

```sh
cp -R .vscode-sample .vscode
```

This will add a `launch.json`, `settings.json` and multiple ACA-Py configuration files for developing with different scenarios.

- Faber: Simple agent to simulate an issuer
- Alice: Simple agent to simulate a holder
- Endorser: Simulates the endorser agent in an endorsement required environment
- Author: Simulates an author agent in a endorsement required environment
- Multitenant Admin: Includes settings for a multitenant/wallet scenario

Having multiple agents is to demonstrate launching multiple agents in a debug session. Any of the config files and the launch file can be changed and customized to meet your needs. They are all setup to run on different ports so they don't interfere with each other. Running the debug session from inside the dev container allows you to contact other services such as a local ledger or tails server using localhost, while still being able to access the swagger admin api through your browser.

For all the agents if you want to use another ledger (von-network) other than localhost you will need to change the `genesis-url` config.
For all the agents if you don't want to support revocation you need to remove or comment out the `tails-server-base-url` config. If you want to use a non localhost server then you will need to change the url.

### Faber

- admin api url = http://localhost:9041
- study the demo to understand the steps to have the agent in the correct state. Make your public dids and schemas, cred-defs, etc.

### Alice

- admin api url = http://localhost:9011
- study the demo to get a connection with faber

### Endorser

- admin api url = http://localhost:9031
- This config is useful if you want to develop in an environment that requires endorsement. You can run the demo with `./run_demo faber --endorser-role author` to see all the steps to become and endorser.

### Author

- admin api url = http://localhost:9021
- This config is useful if you want to develop in an environment that requires endorsement. You can run the demo with `./run_demo faber --endorser-role author` to see all the steps to become and author. You need to uncomment the configurations for automating the connection to endorser.

### Multitenant-Admin

- admin api url = http://localhost:9051
- This is for a multitenant environment where you can create multiple tenants with subwallets with one agent. See [Multitenancy](./Multitenancy.md)

### Try running Faber and Alice at the same time and add break points and recreate the demo

To run your ACA-Py code in debug mode, go to the `Run and Debug` view, select the agent(s) you want to start and click `Start Debugging (F5)`.

This will start your source code as a running ACA-Py instance, all configuration is in the `*.yml` files. This is just a sample of a configuration. Note that we are not using a database and are joining to a local VON Network (by default, it would be `http://localhost:9000`). You could change this or another ledger such as `http://test.bcovrin.vonx.io`. These are purposefully, very simple configurations.

For example, open `aries_cloudagent/admin/server.py` and set a breakpoint in `async def status_handler(self, request: web.BaseRequest):`, then call [`GET /status`](http://localhost:9061/api/doc#/server/get_status) in the Admin Console and hit your breakpoint.

## Pytest

Pytest is installed and almost ready; however, we must build the test list. In the Command Palette, `Test: Refresh Tests` will scan and find the tests.

See [Python Testing](https://code.visualstudio.com/docs/python/testing) for more details, and [Test Commands](https://code.visualstudio.com/docs/python/testing#_test-commands) for usage.

*WARNING*: our pytests include coverage, which will prevent the [debugger from working](https://code.visualstudio.com/docs/python/testing#_debug-tests). One way around this would be to have a `.vscode/settings.json` that says not to use coverage (see above). This will allow you to set breakpoints in the pytest and code under test and use commands such as `Test: Debug Tests in Current File` to start debugging.

*WARNING*: the project configuration found in `pyproject.toml` include performing `ruff` checks when we run `pytest`. Including `ruff` does not play nice with the Testing view. In order to have our pytests discoverable AND available in the Testing view, we create a `.pytest.ini` when we build the devcontainer. This file will not be committed to the repo, nor does it impact `./scripts/run_tests` but it will impact if you manually run the pytest commands locally outside of the devcontainer. Just be aware that the file will stay on your file system after you shutdown the devcontainer.

## Next Steps

At this point, you now have a development environment where you can add pytests, add ACA-Py code and run and debug it all. Be aware there are limitations with `devcontainer` and other docker networks. You may need to adjust other docker-compose files not to start their own networks, and you may need to reference containers using `host.docker.internal`. This isn't a panacea but should get you going in the right direction and provide you with some development tools.
