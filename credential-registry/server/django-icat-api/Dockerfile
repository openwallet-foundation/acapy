# TODO: remove the step once a package is available on PyPi
# package pre-requirements
FROM python:3.7-alpine as packager
WORKDIR /tmp/django-icat-api
ADD . .
RUN python setup.py sdist

# building indy cat indy api image
FROM bcgovimages/von-image:py36-1.7-ew-0-s2i
COPY --from=packager /tmp/django-icat-api/dist dist
RUN pip install dist/django-icat-api-0.1.tar.gz
