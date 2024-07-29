#!/bin/bash
set -ex

# Convenience workspace directory for later use
WORKSPACE_DIR=$(pwd)

# install all ACA-Py requirements
python -m pip install --upgrade pip
pip3 install -r demo/requirements.txt -r demo/requirements.behave.txt

# install a version of aries-cloudagent so the pytests can pick up a version
pip3 install aries-cloudagent

# hack/workaround to allow `pytest .` and `poetry run pytest` work.
# need to not run ruff...

cat > .pytest.ini <<EOF
# this is created for the devcontainer so pytests are properly discoverable.
# remove this file for normal operations outside of the devcontainer.
# basically we cannot have ruff (--ruff) in the pytest configuration as it breaks the Testing View.
[pytest]
testpaths = "aries_cloudagent"
addopts = --quiet
markers = [
    "anoncreds: Tests specifically relating to AnonCreds support",
    "askar: Tests specifically relating to Aries-Askar support",
    "indy: Tests specifically relating to Hyperledger Indy SDK support",
    "indy_credx: Tests specifically relating to Indy-Credx support",
    "indy_vdr: Tests specifically relating to Indy-VDR support",
    "ursa_bbs_signatures: Tests specificaly relating to BBS Signatures support",
    "postgres: Tests relating to the postgres storage plugin for Indy"]
junit_family = "xunit1"
asyncio_mode = auto
EOF
