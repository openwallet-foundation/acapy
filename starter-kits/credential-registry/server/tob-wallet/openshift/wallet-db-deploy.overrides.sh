# ======================================================
# Special Deployment Parameters needed for DB Deployment
# ------------------------------------------------------
# The results need to be encoded as OpenShift template
# parameters for use with oc process.
# ======================================================

generateUsername() {
  # Generate a random username and Base64 encode the result ...
  _userName=USER_$( cat /dev/urandom | LC_CTYPE=C tr -dc 'a-zA-Z0-9' | fold -w 4 | head -n 1 )
  _userName=$(echo -n "${_userName}"|base64)
  echo ${_userName}
}

generatePassword() {
  # Generate a random password and Base64 encode the result ...
  _password=$( cat /dev/urandom | LC_CTYPE=C tr -dc 'a-zA-Z0-9_' | fold -w 16 | head -n 1 )
  _password=$(echo -n "${_password}"|base64)  
  echo ${_password}
}

_userName=$(generateUsername)
_password=$(generatePassword)
_adminPassword=$(generatePassword)

SPECIALDEPLOYPARMS="-p POSTGRESQL_USER=${_userName} -p POSTGRESQL_PASSWORD=${_password} -p POSTGRESQL_ADMIN_PASSWORD=${_adminPassword}"
echo ${SPECIALDEPLOYPARMS}

