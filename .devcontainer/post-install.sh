#!/bin/bash
set -ex

# Convenience workspace directory for later use
WORKSPACE_DIR=$(pwd)

# install all ACA-Py requirements
python -m pip install --upgrade pip
pip3 install -r requirements.txt -r requirements.askar.txt -r requirements.bbs.txt -r requirements.dev.txt -r requirements.indy.txt 

# install black for formatting
pip3 install black