# =================================================================================================================
# Default Settings:
# - Override using script options
# -----------------------------------------------------------------------------------------------------------------
queryPattern=${queryPattern:-"api\/search\/credential\/topic?name="}
projectNamespace=${projectNamespace:-devex-von-bc-tob-prod}
appName=${appName:-angular-on-nginx}
blacklistRaw=${blacklistRaw:-blacklist.raw}
blacklistConf=${blacklistConf:-blacklist.conf}
# -----------------------------------------------------------------------------------------------------------------
# Usage:
# -----------------------------------------------------------------------------------------------------------------
usage() {
  cat <<-EOF

  A script to dynamically generate and update and nginx blacklist from logs and a given pattern.

  Basic usage:
    $0 [options]

  Example:
    $0 -q "api\/search\/credential\/topic?name="

  Options:
  ========
    -h prints the usage for the script
    -q Query pattern; default "${queryPattern}"
    -p OCP project namespace; default ${projectNamespace}
    -a App name; default ${appName}
    -l Log file name; default ${blacklistRaw}
    -c Blacklist config file name; default ${blacklistConf}

EOF
  exit 1
}
# -----------------------------------------------------------------------------------------------------------------
# Initialization:
# -----------------------------------------------------------------------------------------------------------------
while getopts q:p:a:l:c:h FLAG; do
  case $FLAG in
    q ) queryPattern=${OPTARG} ;;
    p ) projectNamespace=${OPTARG} ;;
    a ) appName=${OPTARG} ;;
    l ) blacklistRaw=${OPTARG} ;;
    c ) blacklistConf=${OPTARG} ;;
    h ) usage ;;
    \? ) #unrecognized option - show help
      echo -e \\n"Invalid script option: -${OPTARG}"\\n
      usage
      ;;
  esac
done
shift $((OPTIND-1))
# -----------------------------------------------------------------------------------------------------------------
# Functions:
# -----------------------------------------------------------------------------------------------------------------
echoYellow (){
  (
    _msg=${1}
    _yellow='\e[33m'
    _nc='\e[0m' # No Color
    echo -e "${_yellow}${_msg}${_nc}"
  )
}

buildBlacklist (){
  (
    queryPattern=${1}
    blacklistRaw=${2:-blacklist.raw}
    blacklistConf=${3:-blacklist.conf}

    echo "" >> ${blacklistConf}

    # Generate a blacklist from the logs
    # - Exclude IPs that are already being blocked.
    # - Include queries matching suspicious pattern(s)
    # - Filter out any cruft
    # - Remove duplicate lines
    sed '/access forbidden by rule/d' ${blacklistRaw} \
      | sed "/${queryPattern}/!d" \
      | sed -r 's~(^.*) - - .*$~deny \1;~' \
      | sed '/deny/!d' \
      | awk '!seen[$0]++' >> ${blacklistConf}

    # Remove any duplicate entries
    awk '!seen[$0]++' ${blacklistConf} > ${blacklistConf}.tmp
    rm ${blacklistConf}
    mv ${blacklistConf}.tmp ${blacklistConf}
  )
}

dumpLogs() {
  (
    projectNamespace=${1:-devex-von-bc-tob-prod}
    appName=${2:-angular-on-nginx}
    blacklistRaw=${3:-blacklist.raw}

    echo "" > ${blacklistRaw}
    oc -n ${projectNamespace} get pods -o name -l app=${appName} | xargs -I {} oc -n ${projectNamespace} logs {} >> ${blacklistRaw}
  )
}
# =================================================================================================================

startLineCount=$(wc -l < ${blacklistConf})

echo ""
echoYellow "$(date)"

echo "Dumping a recent copy of the logs from ${projectNamespace}/${appName} into ${blacklistRaw} ..."
dumpLogs "${projectNamespace}" "${appName}" "${blacklistRaw}"

echo "Building blacklist (${blacklistConf}) from ${blacklistRaw}, using pattern \"${queryPattern}\" ..."
buildBlacklist "${queryPattern}" "${blacklistRaw}" "${blacklistConf}"

endLineCount=$(wc -l < ${blacklistConf})
addedLines=$(expr ${endLineCount} - ${startLineCount})
echoYellow "- ${addedLines} new entries where added to the list."

if (( ${addedLines} > 0 )); then
  echo -e \\n"Generating updated config map ..."
  cd ..
  ./${appName}-deploy.overrides.sh

  echo "Updating config map ..."
  oc -n ${projectNamespace} replace -f ./blacklist-conf-configmap_DeploymentConfig.json

  echo "Rolling out ${appName} with updated blacklist..."
  oc -n ${projectNamespace} rollout latest dc/${appName}
else
  echo -e \\n"No updates needed."
fi

rm -f ${blacklistRaw}
