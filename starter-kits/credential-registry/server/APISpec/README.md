# OpenAPI 3.0 spec

The auto-generated documentation only generates openapi 2.0. Because of this, we use the following process to create the openapi 3.0 spec available in this directory.

1. Download the current openapi 2.0 spec from https://orgbook.gov.bc.ca/api/?format=openapi.
2. Use the following tool to convert the openapi 2.0 spec to 3.0: https://mermade.org.uk/openapi-converter
3. Update the output to include the `/indy/` endpoints which are not automatically generated.