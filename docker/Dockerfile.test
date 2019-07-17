FROM ubuntu:18.04

RUN apt-get update -y && \
	apt-get install -y --no-install-recommends \
	python3 \
	python3-pip \
	python3-setuptools \
	libsodium23 && \
	rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

ADD requirements.txt requirements.dev.txt ./

RUN pip3 install --no-cache-dir \
	-r requirements.txt \
	-r requirements.dev.txt

ADD . .

ENTRYPOINT ["/bin/bash", "-c", "pytest \"$@\"", "--"]