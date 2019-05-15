#!/bin/bash
SCRIPT_DIR=$(dirname $0)
MANAGE_CMD=${SCRIPT_DIR}/runManageCmd.sh

# ==============================================================================================================================
usage() {
  cat <<-EOF
  ========================================================================================
  Reprocess all of the registered credentials in the database using the latest mappings
  and schemas from the registered agents.
  ----------------------------------------------------------------------------------------
  Usage:
    ${0} [ -h ]
  
  Options:
    -h Prints the usage for the script
  ========================================================================================
EOF
exit
}

while getopts h FLAG; do
  case $FLAG in
    h ) usage
      ;;
    \? ) #unrecognized option - show help
      echo -e \\n"Invalid script option: -${OPTARG}"\\n
      usage
      ;;
  esac
done

shift $((OPTIND-1))
# ==============================================================================================================================

${MANAGE_CMD} reprocess_credentials