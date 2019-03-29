# ================================================================================================================
# Special deployment parameters needed for injecting a user supplied settings into the deployment configuration
# ----------------------------------------------------------------------------------------------------------------
# The results need to be encoded as OpenShift template parameters for use with oc process.
# ================================================================================================================

# ================================================================================================================
# Functions
# ----------------------------------------------------------------------------------------------------------------
printStatusMsg(){
  (
    _msg=${1}
    _yellow='\033[1;33m'
    _nc='\033[0m' # No Color
    printf "\n${_yellow}${_msg}\n${_nc}" >&2
  )
}

readParameter(){
  (
    _msg=${1}
    _paramName=${2}
    _defaultValue=${3}
    _encode=${4}

    _yellow='\033[1;33m'
    _nc='\033[0m' # No Color
    _message=$(echo -e "\n${_yellow}${_msg}\n${_nc}")

    read -r -p $"${_message}" ${_paramName}
    writeParameter "${_paramName}" "${_defaultValue}" "${_encode}"
  )
}

writeParameter(){
  (
    _paramName=${1}
    _defaultValue=${2}
    _encode=${3}

    if [ -z "${_encode}" ]; then
      echo "${_paramName}=${!_paramName:-${_defaultValue}}" >> ${_overrideParamFile}
    else
      # The key/value pair must be contained on a single line
      _encodedValue=$(echo -n "${!_paramName:-${_defaultValue}}"|base64 -w 0)
      echo "${_paramName}=${_encodedValue}" >> ${_overrideParamFile}
    fi
  )
}

generateKey(){
  (
    _length=${1:-48}
    # Format can be `-base64` or `-hex`
    _format=${2:--base64} 

    echo $(openssl rand ${_format} ${_length})
  )
}

generateSeed(){
  (
    _prefix=${1}
    _seed=$(echo "${_prefix}$(generateKey 32)" | fold -w 32 | head -n 1 )
    _seed=$(echo -n "${_seed}")
    echo ${_seed}
  )
}

generateUsername() {
  # Generate a random username ...
  _userName=User_$( generateKey | LC_CTYPE=C tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1 )
  _userName=$(echo -n "${_userName}")
  echo ${_userName}
}

generatePassword() {
  # Generate a random password ...
  _password=$( generateKey | LC_CTYPE=C tr -dc 'a-zA-Z0-9_' | fold -w 20 | head -n 1 )
  _password=$(echo -n "${_password}")
  echo ${_password}
}

initialize(){
  # Define the name of the override param file.
  _scriptName=$(basename ${0%.*})
  export _overrideParamFile=${_scriptName}.param

  printStatusMsg "Initializing ${_scriptName} ..."

  # Remove any previous version of the file ...
  if [ -f ${_overrideParamFile} ]; then
    printStatusMsg "Removing previous copy of ${_overrideParamFile} ..."
    rm -f ${_overrideParamFile}
  fi
}
# ================================================================================================================

# ================================================================================================================
# Main Scipt Starts Here ...
# ----------------------------------------------------------------------------------------------------------------
initialize

# Randomly generate a set of credentials without asking ...
printStatusMsg "Creating a set of random user credentials ..."
writeParameter "USER_ID" $(generateUsername) "true"
writeParameter "USER_PASSWORD" $(generatePassword) "true"
writeParameter "ADMIN_USER_ID" $(generateUsername) "true"
writeParameter "ADMIN_PASSWORD" $(generatePassword) "true"

# Ask the user to supply the sensitive parameters ...
readParameter "WALLET_ENCRYPTION_KEY - Please provide the wallet encryption key for the environment.  If left blank, a 48 character long base64 encoded value will be randomly generated using openssl:" WALLET_ENCRYPTION_KEY $(generateKey) "true"

_walletPrefix="TB"
readParameter "INDY_WALLET_SEED - Please provide the indy wallet seed for the environment.  If left blank, a seed will be randomly generated using openssl:" INDY_WALLET_SEED $(generateSeed ${_walletPrefix}) "true"
readParameter "INDY_WALLET_DID - Please provide the indy wallet did for the environment.  The default is an empty string:" INDY_WALLET_DID "" "true"

# Get the settings for delivering user feedback to the business
readParameter "FEEDBACK_TARGET_EMAIL - Please provide the target email address where user feedback will be sent.  The default is a blank string." FEEDBACK_TARGET_EMAIL ""
readParameter "SMTP_SERVER_ADDRESS - Please provide the address of the outgoing smtp server.  The default is a blank string." SMTP_SERVER_ADDRESS ""

SPECIALDEPLOYPARMS="--param-file=${_overrideParamFile}"
echo ${SPECIALDEPLOYPARMS}
# ================================================================================================================
