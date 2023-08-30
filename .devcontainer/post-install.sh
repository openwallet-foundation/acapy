#!/bin/bash
set -ex

# Convenience workspace directory for later use
WORKSPACE_DIR=$(pwd)

# install all ACA-Py requirements
python -m pip install --upgrade pip
pip3 install -r demo/requirements.txt -r demo/requirements.behave.txt

# install black for formatting
pip3 install black