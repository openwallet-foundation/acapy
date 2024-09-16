This project is used to write integration tests leveraging the [acapy-minimal-example](https://github.com/Indicio-tech/acapy-minimal-example) library provided by the contributors from Indicio

Getting started:
- `poetry install --no-root`
- Study the test agent library https://github.com/Indicio-tech/acapy-minimal-example
- Add a scneario or additions to existing scenarios.
- Add assertions.

Every test example will have a docker-compose.yml file for all the agents and services used in the test scenario. To run an individual scenario:
- From the scenarios directory. 
- Make sure the local acapy image is up to date. 
 - `cd ..`
 - `docker build -t acapy-test -f ./docker/Dockerfile.run .`
 - `cd scenarios`
- Navigate to the base example. `cd examples/simple`
- `docker compose up`

To run all the tests with pytest:
- From the scenarios directory. 
- Make sure the local acapy image is up to date. 
 - `cd ..`
 - `docker build -t acapy-test -f ./docker/Dockerfile.run .`
 - `cd scenarios`
- `poetry run pytest -m examples`
- TODO: easily run individual tests with pytest.
