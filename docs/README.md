## How to generate documentation

Ensure the `sphinx_rtd_theme` theme is installed

```
pip install -U sphinx-rtd-theme
```

Ensure the sphinx tool is installed and run:

To rebuild the project and settings from scratch (you'll need to move the generated index file up a level):
```
sphinx-apidoc -f -M -F -o  ./generated .. '../setup.py'
```

```
sphinx-apidoc -f -M -o  ./generated .. '../setup.py'
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