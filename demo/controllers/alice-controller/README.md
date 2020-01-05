# Alice Controller

Web controller for a Hyperledger Aries Alice CloudAgent (aca-py)

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running Locally](#running-locally)

### Prerequisites

Alice Controller requires `Node.js 10.x` or higher. Node.js can be downloaded [here](https://nodejs.org/en/download/). Alternatively you can use a Node.js version manager like [`nvm`](https://github.com/nvm-sh/nvm) or [`nvm-windows`](https://github.com/coreybutler/nvm-windows).

### Running Locally

Alice controller was generated with [Angular CLI](https://github.com/angular/angular-cli) version 8.1.1 and can be run locally with minimal effort using the CLI. The CLI is installed as a global npm package.

For example on Linux:

```
$ npm install -g @angular/cli
```

From the alice-controller root directory, simply install application node modules then call `ng serve`

For example on Linux:

```
$ npm install
$ ng serve
```

You may see an output like:

```
chunk {connection-connection-module} connection-connection-module.js, connection-connection-module.js.map (connection-connection-module) 306 kB  [rendered]
chunk {credential-credential-module} credential-credential-module.js, credential-credential-module.js.map (credential-credential-module) 17.7 kB  [rendered]
chunk {main} main.js, main.js.map (main) 60.6 kB [initial] [rendered]
chunk {polyfills} polyfills.js, polyfills.js.map (polyfills) 264 kB [initial] [rendered]
chunk {proof-proof-module} proof-proof-module.js, proof-proof-module.js.map (proof-proof-module) 16.7 kB  [rendered]
chunk {runtime} runtime.js, runtime.js.map (runtime) 9.13 kB [entry] [rendered]
chunk {styles} styles.js, styles.js.map (styles) 842 kB [initial] [rendered]
chunk {vendor} vendor.js, vendor.js.map (vendor) 4.63 MB [initial] [rendered]
Date: 2020-01-05T18:47:21.136Z - Hash: 61c4728366fef065089e - Time: 7894ms
** Angular Live Development Server is listening on localhost:4200, open your browser on http://localhost:4200/ **
ℹ ｢wdm｣: Compiled successfully.
```

You can now open your browser tab to `localhost:4200` to see the application.

_Note: Alice Controller has already been configured to connect to it's agent on localhost:8031. If the controller is not connected to it's agent you will see a red status indicator on the top right-hand side of the navbar. If the agent is succesffully connected, you will see a green status indicator._

