======
api_v2
======

api_v2 is a Django app which provides the back-end storage and search capabilities 
for Indy Catalyst Credential Registry.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Add "api_v2" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'api_v2',
    ]

2. Include the api_v2 URLconf in your project urls.py like this::

    path("api/v2/", include("api_v2.urls")),

3. Move the api_v2 folder (remove from TheOrgBook repo) into this directory

4. Run "python setup.py sdist" to create a distribution

5. Include the following in your Docker build pipeline to build the OrgBook image:

build-api() {
  #
  # tob-api
  #
  echo -e "\nBuilding indy cat api image ..."
  docker build -q \
    -t 'indycat-api-build' \
    -f '../../../../credential-registry/server/django-icat-api/Dockerfile' '../../../../credential-registry/server/django-icat-api/'
  BASE_IMAGE="indycat-api-build"
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
