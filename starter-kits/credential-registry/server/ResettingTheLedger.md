# Resetting the Ledger and Wallets

## Overview

Resetting the ledger and wallets used by [TheOrgBook](https://github.com/bcgov/TheOrgBook) and the supporting [dFlow Services](https://github.com/bcgov/dFlow) requires executing an orchestrated process to allow all of the various participants to register with the ledger and recreate their associated wallets to avoid the wallets and ledger entries from getting out of sync.

The following procedure describes the process of resetting the ledger and wallets for an instance of the Ledger, TheOrgBook and dFlow.

## Procedure

These instructions assume you are using the OpenShift management scripts found here; [openshift-developer-tools](https://github.com/BCDevOps/openshift-developer-tools).  Refer to the [OpenShift Scripts](https://github.com/BCDevOps/openshift-developer-tools/blob/master/bin/README.md) documentation for details.

It is assumed you have an instance of [dFlow](https://github.com/bcgov/dFlow) and the [von-network](https://github.com/bcgov/von-network) running, and you have working copies of both the [dFlow](https://github.com/bcgov/dFlow) and [TheOrgBook](https://github.com/bcgov/TheOrgBook) source code.

1. Open 2 Git Bash command prompt windows; one to your `.../dFlow/openshift` working directory and the other to your `.../TheOrgBook/openshift` working directory.
1. From the `.../TheOrgBook/openshift` command prompt, run the manage command to reset TheOrgBook environment, and follow the instructions moving on to running the dFlow manage commands in parallel when instructed.
    - For example; 
        - `./manage -P -e dev hardReset`
    - For full usage information run;
        - `./manage -h`
1. From the `.../dFlow/openshift` command prompt, run the manage commands to reset all of the dFlow service pods, and follow the instructions.
    - For example; 
        - `./manage -e dev reset`
    - For full usage information run;
        - `./manage -h`
1. When both sets of scripts are at the **If you are resetting the ledger** step, reset your [von-network](https://github.com/bcgov/von-network) instance by following the instructions to stop and restart the ledger nodes and ledger browser.
1. Once the ledger nodes and browser have started, allow the manage scripts to complete the DID registration process.

Now you can load data by following the instructions here; [Loading the Test Data](./APISpec/TestData/README.md)
