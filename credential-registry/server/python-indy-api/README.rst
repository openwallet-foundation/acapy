========
api_indy
========

api_indy is a Python app which provides the Indy agent integration capabilities 
for Indy Catalyst Credential Registry.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Move the indy_api folder (remove from TheOrgBook repo) into this directory

2. Run "python setup.py sdist" to create a distribution

3. Include the following in your Docker build pipeline to build the OrgBook image:

build-api() {
  #
  # tob-api
  #
  echo -e "\nBuilding indy cat api image ..."
  docker build -q \
    -t 'indycat-api-build' \
    -f '../django-icat-api/Dockerfile' '../django-icat-api/'
  echo -e "\nBuilding indy cat indy api image ..."
  docker build -q \
    -t 'indycat-indyapi-build' \
    -f '../python-indy-api/Dockerfile' '../python-indy-api/'
  BASE_IMAGE="indycat-indyapi-build"
  #BASE_IMAGE="bcgovimages/von-image:py36-1.7-ew-0-s2i"
  echo -e "\nBuilding django image from ${BASE_IMAGE}..."
  ${S2I_EXE} build \
    -e "HTTP_PROXY=${HTTP_PROXY}" \
    -e "HTTPS_PROXY=${HTTPS_PROXY}" \
    -e "PIP_NO_CACHE_DIR=" \
    -v "${COMPOSE_PROJECT_NAME}_tob-pip-cache:/home/indy/.cache/pip" \
    '../tob-api' \
    "$BASE_IMAGE" \
    'django'
}

4. Follow the rest of the Indy Catalyst instructions!
