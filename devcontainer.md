For information on running demos and tests using provided shell scripts, see [DevReadMe](/DevReadMe.md) readme.

# ACA-Py Development with Dev Container
The following guide will get you up and running and developing/debugging ACA-Py as quickly as possible. 
We provide a [`devcontainer`](https://containers.dev) and will use [`VS Code`](https://code.visualstudio.com) to illustrate.

By no means is ACA-Py limited to these tools; they are merely examples.  

## Caveats

The primary use case for this `devcontainer` is for developing, debugging and unit testing (pytest) the [aries_cloudagent](./aries_cloudagent) source code.

There are limitations running this devcontainer, such as not being able to select the docker network. Also, we are not expecting developers to run the [demos](./demo) or other docker based scripts within this container.


## Further Reading and Links

* Development Containers (devcontainers): [https://containers.dev](https://containers.dev)
* Visual Studio Code: [https://code.visualstudio.com](https://code.visualstudio.com)
* Dev Containers Extension: [marketplace.visualstudio.com](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
* Docker: [https://www.docker.com](https://www.docker.com)
* Docker Compose: [https://docs.docker.com/compose/](https://docs.docker.com/compose/)


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

#### devcontainer.json

When the [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) is opened, you will see it building... it is building a Python 3.9 image (bash shell) and loading it with all the ACA-Py requirements (and black). Since this is a Docker container, we will also open ports `9060` and `9061`, allowing you to run/debug ACA-Py with those ports available to your `localhost` (more on those later). We also load a few Visual Studio settings (for running Pytests and formatting with Flake and Black).

In VS Code, open a Terminal, you should be able to run the following commands:

```
python -m aries_cloudagent -v
cd aries_cloudagent
flake8 --max-line-length=90 --exclude=*/tests/** --extend-ignore=D202,W503 --per-file-ignores=*/__init__.py:D104
black . --check
```

The first command should show you that `aries_cloudagent` module is loaded (ACA-Py). The others are examples of code quality checks that ACA-Py does on commits (if you have [`precommit`](https://pre-commit.com) installed) and Pull Requests.

## Debugging

To better illustrate debugging pytests and ACA-Py runtime code, let's add some run/debug configurations to VS Code. If you have your own `launch.json` and `settings.json`, please cut and paste what you want/need.

```
cp -R .vscode-sample .vscode
```

This will add a `launch.json`, `settings.json` and an ACA-Py configuration file: `multitenant.yml`. 

### Pytest

Pytest is installed and almost ready; however, we must build the test list. In the Command Palette, `Test: Refresh Tests` will scan and find the tests.

See [Python Testing](https://code.visualstudio.com/docs/python/testing) for more details, and [Test Commands](https://code.visualstudio.com/docs/python/testing#_test-commands) for usage.

*IMPORTANT*: our pytests include coverage, which will prevent the [debugger from working](https://code.visualstudio.com/docs/python/testing#_debug-tests). One way around this would be to have a `.vscode/settings.json` that says not to use coverage (see above). This will allow you to set breakpoints in the pytest and code under test and use commands such as `Test: Debug Tests in Current File` to start debugging.


### ACA-Py

Above, we added some run/debug configurations, one of which is to run our ACA-Py source code so we can debug it.

In `launch.json` you will see:

```
        {
            "name": "Run/Debug ACA-Py",
            "type": "python",
            "request": "launch",
            "module": "aries_cloudagent",
            "justMyCode": true,
            "args": [
                "start",
                "--arg-file=${workspaceRoot}/.vscode/multitenant.yml"
            ]
        },
```

To run your ACA-Py code in debug mode, go to the `Run and Debug` view, select "Run/Debug ACA-Py" and click `Start Debugging (F5)`.

This will start your source code as a running ACA-Py instance, all configuration is in the `multitenant.yml` file. This is just a sample of a configuration, and we chose multi-tenancy so we can easily create multiple wallets/agents and have them interact.  Note that we are not using a database and are joining the ` http://test.bcovrin.vonx.io` ledger. Feel free to change to a local VON Network (by default, it would be `http://host.docker.internal:9000`) or another ledger. This is purposefully a very simple configuration.

Remember those ports we exposed in `devcontainer`? You can open a browser to `http://localhost:9061/api/doc` and see your Admin Console Swagger. Set some breakpoints and hit some endpoints, and start debugging your source code.

For example, open `aries_cloudagent/admin/server.py` and set a breakpoint in `async def status_handler(self, request: web.BaseRequest):`, then call [`GET /status`](http://localhost:9061/api/doc#/server/get_status) in the Admin Console and hit your breakpoint.

## Next Steps

At this point, you now have a development environment where you can add pytests, add ACA-Py code and run and debug it all. Be aware there are limitations with `devcontainer` and other docker networks. You may need to adjust other docker-compose files not to start their own networks, and you may need to reference containers using `host.docker.internal`. This isn't a panacea but should get you going in the right direction and provide you with some development tools.
