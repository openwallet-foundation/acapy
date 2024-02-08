# Poetry Cheat Sheet for Developers

## Introduction to Poetry

Poetry is a dependency management and packaging tool for Python that
aims to simplify and enhance the development process. It offers
features for managing dependencies, virtual environments, and building
and publishing Python packages.

## Virtual Environments with Poetry

Poetry manages virtual environments for your projects to ensure clean
and isolated development environments.

### Creating a Virtual Environment

```bash
poetry install
```

### Activating the Virtual Environment

```bash
poetry shell
```

Alternatively you can source the environment settings in the current shell

```bash
source $(poetry env info --path)/bin/activate
```

for powershell users this would be

```powershell
(& ((poetry env info --path) + "\Scripts\activate.ps1")
```

### Deactivating the Virtual Environment

When using `poetry shell`

```bash
exit
```

When using the `activate` script

```bash
deactivate
```

## Dependency Management

Poetry uses the `pyproject.toml` file to manage dependencies. Add new
dependencies to this file and update existing ones as needed.

### Adding a Dependency

```bash
poetry add package-name
```

### Adding a Development Dependency

```bash
poetry add --dev package-name
```

### Removing a Dependency

```bash
poetry remove package-name
```

### Updating Dependencies

```bash
poetry update
```

## Running Tasks with Poetry

Poetry provides a way to run scripts and commands without activating
the virtual environment explicitly.

### Running a Command

```bash
poetry run command-name
```

### Running a Script

```bash
poetry run python script.py
```

## Building and Publishing with Poetry

Poetry streamlines the process of building and publishing Python packages.

### Building the Package

```bash
poetry build
```

### Publishing the Package

```bash
poetry publish
```

## Using Extras

Extras allow you to specify additional dependencies based on project
requirements.

### Installing with Extras

```bash
poetry install -E extras-name
```

for example

```bash
poetry install -E "askar bbs indy"
```

## Managing Development Dependencies

Development dependencies are useful for tasks like testing, linting,
and documentation generation.

### Installing Development Dependencies

```bash
poetry install --dev
```

## Additional Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [PyPI: The Python Package Index](https://pypi.org/)
