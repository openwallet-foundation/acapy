# A simple makefile purely to demonstrate building the new docker images

CONTAINER_RUNTIME ?= docker
IMAGE_NAME=ghcr.io/hyperledger/aries-cloudagent-python
PYTHON_VERSION=3.6.13
PYTHON_VERSION_MAJ_MIN=3.6
RUST_VERSION=1.46
ACAPY_VERSION=0.7.4
ACAPY_REQS=[askar,bbs]
INDY_VERSION=1.16.0
INDY_SDK_URL=https://codeload.github.com/hyperledger/indy-sdk/tar.gz/refs/tags/v$(INDY_VERSION)
INDY_IMAGE_NAME=ghcr.io/hyperledger/indy-python

all: indy-python indy standard

indy-python:
	$(CONTAINER_RUNTIME) build -t $(INDY_IMAGE_NAME):latest \
		--build-arg python_version=$(PYTHON_VERSION) \
		--build-arg rust_version=$(RUST_VERSION) \
		--build-arg indy_version=$(INDY_VERSION) \
		--build-arg indy_sdk_url=$(INDY_SDK_URL) \
		-f Dockerfile.indy-base .
	$(CONTAINER_RUNTIME) tag $(INDY_IMAGE_NAME):latest \
		$(INDY_IMAGE_NAME):py$(PYTHON_VERSION)-$(INDY_VERSION)
	$(CONTAINER_RUNTIME) tag $(INDY_IMAGE_NAME):latest \
		$(INDY_IMAGE_NAME):py$(PYTHON_VERSION_MAJ_MIN)-$(INDY_VERSION)

indy:
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):indy-latest \
		--build-arg python_version=$(PYTHON_VERSION) \
		--build-arg indy_version=$(INDY_VERSION) \
		--build-arg acapy_version=$(ACAPY_VERSION) \
		--build-arg acapy_reqs=$(ACAPY_REQS) \
		-f Dockerfile.indy .
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):indy-latest \
		$(IMAGE_NAME):py$(PYTHON_VERSION)-indy-$(INDY_VERSION)-$(ACAPY_VERSION)
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):indy-latest \
		$(IMAGE_NAME):py$(PYTHON_VERSION_MAJ_MIN)-indy-$(INDY_VERSION)-$(ACAPY_VERSION)

standard:
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):latest \
		--build-arg python_version=$(PYTHON_VERSION) \
		--build-arg acapy_version=$(ACAPY_VERSION) \
		--build-arg acapy_reqs=$(ACAPY_REQS) \
		-f Dockerfile .
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):latest \
		$(IMAGE_NAME):py$(PYTHON_VERSION)-$(ACAPY_VERSION)
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):latest \
		$(IMAGE_NAME):py$(PYTHON_VERSION_MAJ_MIN)-$(ACAPY_VERSION)

.PHONY: all indy-python indy standard
