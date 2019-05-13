#!/bin/bash
SCRIPT_DIR=$(dirname $0)
MANAGE_CMD=${SCRIPT_DIR}/runManageCmd.sh
OUTPUT_DIR=${SCRIPT_DIR}/../tob-solr/cores/the_org_book/conf

# ==============================================================================================================================
usage() {
  cat <<-EOF
  ===============================================================================================
  Builds the schema and configuration file(s) for Solr, based on your project's 
  Haystack/Solr configuration.
  
  By default the configuration files will be output to, ${OUTPUT_DIR}.
  -----------------------------------------------------------------------------------------------
  Usage:
    ${0} [ -h -x -s <SolrUrl/> -o <OutputDirectory/>]
  
  Options:
    -h Prints the usage for the script
    -x Enable debug output
    -s The URL to the Solar search engine instance
    -o Output directory.  Default; ${OUTPUT_DIR}
  
  Example:
    ${0}
  ===============================================================================================
EOF
exit
}
while getopts s:o:xh FLAG; do
  case $FLAG in
    s ) export SOLR_URL=$OPTARG
      ;;
    o ) OUTPUT_DIR=$OPTARG
      ;;
    x ) export DEBUG=1
      ;;
    h ) usage
      ;;
    \? ) #unrecognized option - show help
      echo -e \\n"Invalid script option: -${OPTARG}"\\n
      usage
      ;;
  esac
done

shift $((OPTIND-1))

if [ -z "${SOLR_URL}" ]; then
  # Fake the Haystack configuration script into hooking up the solr backend
  # Required for the Solr configuration to be updated.
  export SOLR_URL=http://localhost:8983/solr/the_org_book
fi
# ==============================================================================================================================

${MANAGE_CMD} build_solr_schema -c ${OUTPUT_DIR}