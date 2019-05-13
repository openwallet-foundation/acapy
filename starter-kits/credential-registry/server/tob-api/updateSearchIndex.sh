#!/bin/bash
SCRIPT_DIR=$(dirname $0)
MANAGE_CMD=${SCRIPT_DIR}/runManageCmd.sh
SOLR_BATCH_SIZE=${SOLR_BATCH_SIZE:-500}

# ==============================================================================================================================
usage() {
  cat <<-EOF
  ========================================================================================
  Updates the Haystack indexes for the project.
  ----------------------------------------------------------------------------------------
  Usage:
    ${0} [ -h -x -s <SolrUrl/> -b <BatchSize/> ]
  
  Options:
    -h Prints the usage for the script
    -x Enable debug output
    -s The URL to the Solr search engine instance 
    -b The batch size to use when performing the indexing.  Defaults to ${SOLR_BATCH_SIZE}.
  
  Example:
    ${0} -s http://localhost:8983/solr/the_org_book  
  ========================================================================================
EOF
exit

}
while getopts s:b:xh FLAG; do
  case $FLAG in
    s ) export SOLR_URL=$OPTARG
      ;;
    b ) SOLR_BATCH_SIZE=$OPTARG
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
# ==============================================================================================================================

${MANAGE_CMD} update_index --batch-size=$SOLR_BATCH_SIZE
