# Aries Cloud Agent - Python: Documentation

This `docs` folder has several kinds of documentation about Aries Cloud Agent - Python (ACA-Py).

If you are interested in becoming an Aries Developer and want to use ACA-Py to get started, you
can start by looking at this [Getting Started](/docs/GettingStartedAriesDev/README.md) guide. It covers
a range of topics necessary to understanding how Aries agents work, particularly ACA-Py.

The recommended developer reference documentation is generated from this folder and hosted
at this [ACA-Py Read The Docs](https://aries-cloud-agent-python.readthedocs.io/en/latest/) site.
Head their if you are looking for reference materials.

The remainder of this document describes how to maintain the `Read The Docs` documentation. As
the structure of the ACA-Py code evolves, the RTD files need to be regenerated and possibly
updated, as noted below.

## How to generate ACA-Py Read The Docs (RTD) documentation

### Before you start

To test generate and view the RTD documentation locally, you must install [Sphinx](https://www.sphinx-doc.org/en/master/) and the
[Sphinx RTD theme](https://pypi.org/project/sphinx-rtd-theme/). Both can be installed from PyPi using pip. For example:

``` bash
pip install -U sphinx
pip install -U sphinx-rtd-theme
```

### Generate Module Files

To rebuild the project and settings from scratch (you'll need to move the generated index file up a level):

``` bash
rm -rf generated
sphinx-apidoc -f -M -o  ./generated ../aries_cloudagent/ $(find ../aries_cloudagent/ -name '*tests*')
```

Note that the `find` command that is used to exclude any of the `test` python files from the RTD documentation.

Check the  `git status` in your repo to see if the generator updates, adds or removes any existing RTD modules.

### Reviewing the files locally

To auto-generate the module documentation locally run:

``` bash
sphinx-build -b html -a -E -c ./ ./ ./_build
```

Once generated, go into the `_build` folder and open `index.html` in a browser. Note that the `_build` is
`.gitignore`'d and so will not be part of a git push.

### Look for Errors

This is the hard part; looking for errors in docstrings added by devs. Some tips:

- Ignore any errors in .md files
- Ignore the warnings about including `docs/README.md`
- Ignore an dist-package errors

Other than that, please investigate and fix things that you find. If there are fixes, it's usually
to adhere to the rules around processing docstrings, and especially around JSON samples.

### Checking for missing modules

The file [`index.rst`](index.rst) in this folder drive the RTD generation. It should pick up all the modules
in the source code, starting from the root `../aries_cloudagent` folder. However, some modules
are not picked up automatically from the root and have to be manually added to `index.rst`. To do that:

* Get a list of all generated modules by running: `ls generated | grep "aries_cloudagent.[a-z]*.rst"`
* Compare that list with the modules listed in the "Subpackages" section of the left side menu in your browser, including any listed below the "Submodules".

If any are missing, you likely need to add them to the `index.rst` file in the `toctree` section of the file.
You will see there are already several instances of that, notably "connections" and "protocols".

### Updating the [readthedocs.org](https://readthedocs.org) site

The RTD documentation is **not** currently auto-generated, so a manual re-generation of the documentation
is still required.

> TODO: Automate this when new tags are applied to the repository.