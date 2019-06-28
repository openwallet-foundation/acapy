## How to generate documentation

Ensure the `sphinx_rtd_theme` theme is installed

```
pip install -U sphinx-rtd-theme
```

Ensure the sphinx tool is installed and run:

To rebuild the project and settings from scratch:
```
sphinx-apidoc -f -M -F -o  . .. '../setup.py'
```

```
sphinx-apidoc -f -M -o  . .. '../setup.py'
```

To auto-generate the module documentation then run:

```
make html
```
or
```
sphinx-build -b html -a -E -c ./ ./ ./_build
```

To build the html.