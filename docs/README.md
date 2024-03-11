# The ACA-Py `docs` Folder

The Aries Cloud Agent Python docs folder contains the source content for the
ACA-Py documentation site [aca-py.org] and for the ACA-Py source code internals
documentation project at ReadTheDocs, published at [https://aries-cloud-agent-python.readthedocs.io].

[aca-py.org]: https://aca-py.org
[https://aries-cloud-agent-python.readthedocs.io]: https://aries-cloud-agent-python.readthedocs.io

This following covers how the two sets of documents are managed and how to update them.

- For the [aca-py.org] documentation, see the guidance in the website generator
repository, [aries-acapy-docs], for how to update the repository to account for
a new release of ACA-Py.
- For the [ACA-Py ReadTheDocs documentation], see the guidance in the [update RTD] markdown file
in this repository.

To generate and locally run the docs website, use docker as follows:

- Get a [Material for Mkdocs] docker image with the necessary extensions by running from the ACA_Py root folder:
  - `docker build -f docs/mkdocs-dockerfile.yml -t squidfunk/mkdocs-material .`
- Run the resulting docker image from the root folder to generate the website on the current branch:
  - `docker run --rm -it -p 8000:8000 --name mkdocs-material -v ${PWD}:/docs squidfunk/mkdocs-material`
  - Open your browser: [http://localhost:8000](http://localhost:8000) and test out the docs.

[aries-acapy-docs]: https://github.com/hyperledger/aries-acapy-docs
[ACA-Py ReadTheDocs documentation]: https://aries-cloud-agent-python.readthedocs.io
[update RTD]: ./UpdateRTD.md
[Material for Mkdocs]: https://squidfunk.github.io/mkdocs-material/
