#!/bin/bash
SCRIPT_DIR=$(dirname $0)
PYTHON_CMD=${SCRIPT_DIR}/runPythonCmd.sh
MANAGE_PY=${SCRIPT_DIR}/manage.py

# ==============================================================================================================================
usage () {
  echo "========================================================================================"
  echo "Runs manage.py commands on the project."
  echo "----------------------------------------------------------------------------------------"
  echo "Usage:"
  echo
  echo "${0} <command>"
  echo
  echo "Where:"
  echo " - <command> is the manage.py command you wish to run."
  echo
  echo "Examples:"
  echo "${0} makemigrations"
  echo "========================================================================================"
  exit 1
}

if [ -z "${1}" ]; then
  usage
fi
# ==============================================================================================================================

${PYTHON_CMD} ${MANAGE_PY} ${@}