# TODO: remove the step once a package is available on PyPi
# package pre-requirements
FROM python:3.7-alpine as packager
WORKDIR /tmp/python-indy-api
ADD . .
RUN python setup.py sdist

# build indy cat api image
FROM indycat-api-build
COPY --from=packager /tmp/python-indy-api/dist dist
RUN pip install dist/python-indy-api-0.1.tar.gz
