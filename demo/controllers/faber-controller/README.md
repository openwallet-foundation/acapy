# Faber Controller

Web controller for a Hyperledger Aries Faber CloudAgent demo

## Table of Contents

- [Running Locally](#running-locally)
    - [Prerequisites](#prerequisites)
    - [Start the Application](#start-the-application)
- [Running with Docker](#runnig-with-docker)
- [Notes](#notes)


### Running Locally

#### Prerequisites

Faber Controller requires `.NET Core 3.1`. Installation instructions for vairous platforms can be viewed [here](https://dotnet.microsoft.com/download).

#### Start the Application

`.NET Core 3.1` comes with a CLI for running .NET applications. To run the controller, you simply need to issue the following command from the faber-controller root directory in a terminal:

For example on Linux:

```
$ dotnet run -p FaberController
```
You may see an output like:

```
info: Microsoft.Hosting.Lifetime[0]
      Now listening on: https://localhost:5001
info: Microsoft.Hosting.Lifetime[0]
      Now listening on: http://localhost:5000
info: Microsoft.Hosting.Lifetime[0]
      Application started. Press Ctrl+C to shut down.
info: Microsoft.Hosting.Lifetime[0]
      Hosting environment: Development
info: Microsoft.Hosting.Lifetime[0]
```

You can now open your browser tab to either `localhost:5000` or `localhost:5001` to see the application.

### Running with Docker

Faber Controller comes with a Docker configuration that containerizes the application along with the `.NET Core 3.1` runtime. You simply need to issue the follwing command from the faber-controller root directory in a terminal:

```
$ docker-compose up
```

You can now open your browser tab to either `localhost:8022` to see the application.

### Notes

_Note: Faber Controller has already been configured to connect to it's agent on localhost:8021. If the controller is not connected to it's agent you will see a red status indicator on the top right-hand side of the navbar. If the agent is succesffully connected, you will see a green status indicator._