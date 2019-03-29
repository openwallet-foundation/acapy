# TheOrgBook Database(s)

## Overview

TheOrgBook DB is used to store the core Organizational data for searching (notably names, locations/addresses and claims held) and the claims themselves.

## Development

The DB component is an instance of Postgres. The schema and data loading is all handled by TheOrgBook API, and the Postgres image being used is an unchanged Red Hat image. As such, there is no build or database initialization associated with the DB - just the Deployment.

## Deployment

To deploy TheOrgBook on an instance of OpenShift, see [the instructions](../RunningLocal.md) in the file RunningLocal.md.

## Connecting a database tool to a database instance

Refer to [Accessing a PostgreSQL Database Hosted in OpenShift](./PortForwardingaDatabase.md) for details on how to connect to an instance of a database hosted in OpenShift using port forwarding.

## BC Registries Database Agent

The BC Registries database components have been migrated into their own repository/project.  Please refer to [von-bc-registries-agent](https://github.com/bcgov/von-bc-registries-agent) for details.

# Database Schema Documentation

Databases are documented using [SchemaSpy](https://github.com/bcgov/SchemaSpy).