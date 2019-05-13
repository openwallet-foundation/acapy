# TheOrgBook Web

## Overview

The Web implements the user interface for TheOrgBook, calling the API to manage data. The interface is served from an instance of [NGINX](https://www.nginx.com/).

## Development

To deploy TheOrgBook on an instance of OpenShift, see [the instructions](../RunningLocal.md) in the file RunningLocal.md.

To run the Web UI only in the development mode, run the following command in the *tob-web* directory.

When running for the first time, install the required node.js packages:

``` 
npm install
``` 

and

``` 
npm start
``` 