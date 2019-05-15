#!/bin/bash
SCRIPT_DIR=$(dirname $0)
ENV_DIR=${SCRIPT_DIR}/env

# ==============================================================================================================================
usage () {
  echo "========================================================================================"
  echo "Runs Python commands using the project's virtual python installation."
  echo "----------------------------------------------------------------------------------------"
  echo "Usage:"
  echo
  echo "${0} <command>"
  echo
  echo "Where:"
  echo " - <command> is the Python command you wish to run."
  echo
  echo "Examples:"
  echo "${0} --version"
  echo "========================================================================================"
  exit 1
}

if [ -z "${1}" ]; then
  usage
fi

if [[ -z "$PYTHON_EXE" ]]; then
	if [[ ! -d ${ENV_DIR} ]]; then
	  PYTHON_EXE=python
	else
	  PYTHON_EXE=${ENV_DIR}/Scripts/python
	fi
fi
# ==============================================================================================================================

${PYTHON_EXE} ${@}