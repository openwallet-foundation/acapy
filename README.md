# Fly2plan Aries Cloud Agent - Python  <!-- omit in toc -->


> An easy to use Aries agent for building SSI services using any language that supports sending/receiving HTTP requests.

## Overview

Fly2plan Drone Pilot Credentialing demo is based on Hyperledger Aries Cloud Agent Python [(ACA-Py)](https://github.com/hyperledger/aries-cloudagent-python) which is a foundation for building Verifiable Credential (VC) ecosystems. ACA-Py operates in the second and third layers of the [Trust Over IP framework (PDF)](https://trustoverip.org/wp-content/uploads/Introduction-to-ToIP-V2.0-2021-11-17.pdf) using [DIDComm messaging](https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0005-didcomm) and [Hyperledger Aries](https://www.hyperledger.org/use/aries) protocols. The "cloud" in the name means that ACA-Py runs on servers (cloud, enterprise, IoT devices, and so forth), but is not designed to run on mobile devices. (Source: [ACA-Py README](https://github.com/hyperledger/aries-cloudagent-python#readme))

### Running in Docker

Running the demo in docker requires having a `von-network` (a Hyperledger Indy public ledger sandbox) instance running in docker locally. See the [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) section of the `von-network` readme file for more info. 

Open `bash` shell terminals for each of the three agents. For Windows users, `git-bash` is highly recommended.

In the first terminal, change directory to `demo`  and start `alice` agent (drone pilot, role: 'holder' ) by issuing the following command:

``` bash
  ./run_demo alice 
```
In the second terminal, change directory to `demo` and start `consortiq` agent (drone trainining provider, role: 'issuer') by issuing the following command:

``` bash
  ./run_demo consortiq 
```

In the third terminal, change directory to `demo` and start `airops` agent (airport operations, role: 'verifier') by issuing the following command:

``` bash
  ./run_demo airops
```

If you are using the scripts from the main Fly2plan repository, these three scripts will be called automatically to start the demo.

## License

[Apache License Version 2.0](https://github.com/hyperledger/aries-cloudagent-python/blob/main/LICENSE)
