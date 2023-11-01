#!/bin/bash
set -ex

# Convenience workspace directory for later use
WORKSPACE_DIR=$(pwd)

# install all ACA-Py requirements
python -m pip install --upgrade pip
pip3 install -r demo/requirements.txt -r demo/requirements.behave.txt

# install black for formatting
pip3 install black

# install a version of aries-cloudagent so the pytests can pick up a version
pip3 install aries-cloudagent