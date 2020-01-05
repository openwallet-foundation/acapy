# Faber Controller

Web controller for a Hyperledger Aries Faber CloudAgent demo

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running Locally](#running-locally)

### Prerequisites

Faber Controller requires `.NET Core 3.1` installation instructions for vairous platforms can be viewed [here](https://dotnet.microsoft.com/download).

### Running Locally

`.NET Core 3.1` comes with a CLI for running .NET applications. To run the controller Simply navigate to the `FaberController` project from the faber-controller root directory and issue the `dotnet run` command:

For example on Linux:

```
$ cd FaberController/
$ dotnet run
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

_Note: Faber Controller has already been configured to connect to it's agent on localhost:8021. If the controller is not connected to it's agent you will see a red status indicator on the top right-hand side of the navbar. If the agent is succesffully connected, you will see a green status indicator._