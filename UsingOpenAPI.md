# Aries Cloud Agent-Python (ACA-Py) - OpenAPI Code Generation Considerations

ACA-Py provides an OpenAPI-documented REST interface for administering the agent's internal state and initiating communication with connected agents.

The running agent provides a `Swagger User Interface` that can be browsed and used to test various scenarios manually (see the [Admin API Readme](AdminAPI.md) for details). However, it is often desirable to produce native language interfaces rather than coding `Controllers` using HTTP primitives. This is possible using several public code generation (codegen) tools. This page provides some suggestions based on experience with these tools when trying to generate `Typescript` wrappers. The information should be useful to those trying to generate other languages. Updates to this page based on experience are encouraged.

## ACA-Py, OpenAPI Raw Output Characteristics

ACA-Py uses [aiohttp_apispec](https://github.com/maximdanilchenko/aiohttp-apispec) tags in code to produce the OpenAPI spec file at runtime dependent on what features have been loaded. How these tags are created is documented in the [API Standard Behaviour](https://github.com/hyperledger/aries-cloudagent-python/blob/main/AdminAPI.md#api-standard-behaviour) section of the [Admin API Readme](AdminAPI.md). The OpenAPI spec is available in raw, unformatted form from a running ACA-Py instance using a route of `http://<acapy host and port>/api/docs/swagger.json` or from the browser `Swagger User Interface` directly.

The ACA-Py Admin API evolves across releases. To track these changes and ensure conformance with the OpenAPI specification, we provide a tool located at [`scripts/generate-open-api-spec`](scripts/generate-open-api-spec). This tool starts ACA-Py, retrieves the `swagger.json` file, and runs codegen tools to generate specifications in both Swagger and OpenAPI formats with `json` language output. The output of this tool enables comparison with the checked-in `open-api/swagger.json` and `open-api/openapi.json`, and also serves as a useful resource for identifying any non-conformance to the OpenAPI specification. At the moment, `validation` is turned off via the `open-api/openAPIJSON.config` file, so warning messages are printed for non-conformance, but the `json` is still output. Most of the warnings reported by `generate-open-api-spec` relate to missing `operationId` fields which results in manufactured method names being created by codegen tools. At the moment, [aiohttp_apispec](https://github.com/maximdanilchenko/aiohttp-apispec) does not support adding `operationId` annotations via tags.

The `generate-open-api-spec` tool was initially created to help identify issues with method parameters not being sorted, resulting in somewhat random ordering each time a codegen operation was performed. This is relevant for languages which do not have support for [named parameters](https://en.wikipedia.org/wiki/Named_parameter) such as `Javascript`. It is recommended that the `generate-open-api-spec` is run prior to each release, and the resulting `open-api/openapi.json` file checked in to allow tracking of API changes over time. At the moment, this process is not automated as part of the release pipeline.

## Generating Language Wrappers for ACA-Py

There are inevitably differences around `best practice` for method naming based on coding language and organization standards.

Best practice for generating ACA-Py language wrappers is to obtain the raw OpenAPI file from a configured/running ACA-Py instance and then post-process it with a merge utility to match routes and insert desired `operationId` fields. This allows the greatest flexibility in conforming to external naming requirements.

Two major open-source code generation tools are [Swagger](https://github.com/swagger-api/swagger-codegen) and [OpenAPI Tools](https://github.com/OpenAPITools/openapi-generator). Which of these to use can be very dependent on language support required and preference for the style of code generated.

The [OpenAPI Tools](https://github.com/OpenAPITools/openapi-generator) was found to offer some nice features when generating `Typescript`. It creates separate files for each class and allows the use of a `.openapi-generator-ignore` file to override generation if there is a spec file issue that needs to be maintained manually.

If generating code for languages that do not support [named parameters](https://en.wikipedia.org/wiki/Named_parameter), it is recommended to specify the `useSingleRequestParameter` or equivalent in your code generator of choice. The reason is that, as mentioned previously, there have been instances where parameters were not sorted when output into the raw ACA-Py API spec file, and this approach helps remove that risk.

Another suggestion for code generation is to keep the `modelPropertyNaming` set to `original` when generating code. Although it is tempting to try and enable marshaling into standard naming formats such as `camelCase`, the reality is that the models represent what is sent on the wire and documented in the [Aries Protocol RFCS](https://github.com/hyperledger/aries-rfcs/tree/master/features). It has proven handy to be able to see code references correspond directly with protocol RFCs when debugging. It will also correspond directly with what the `model` shows when looking at the ACA-Py `Swagger UI` in a browser if you need to try something out manually before coding. One final point is that on occasions, it has been discovered that the code generation tools don't always get the marshaling correct in all circumstances when changing model name format.

## Existing Language Wrappers for ACA-Py

### Python

- [Aries Cloud Controller Python (GitHub / didx-xyz)](https://github.com/didx-xyz/aries-cloudcontroller-python)
  - [Aries Cloud Controller (PyPi)](https://pypi.org/project/aries-cloudcontroller/)
- [Traction (GitHub / bcgov)](https://github.com/bcgov/traction)
- [acapy-client (GitHub / Indicio-tech)](https://github.com/Indicio-tech/acapy-client)

### Go

- [go-acapy-client (GitHub / Idej)](https://github.com/ldej/go-acapy-client)

### Java

- [ACA-Py Java Client Library (GitHub / hyperledger-labs)](https://github.com/hyperledger-labs/acapy-java-client)
