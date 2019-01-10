import runpy
from setuptools import setup, find_packages

PACKAGE_NAME = "indy_catalyst_agent"
version_meta = runpy.run_path("./{}/version.py".format(PACKAGE_NAME))
VERSION = version_meta["__version__"]


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


if __name__ == "__main__":
    setup(
        name=PACKAGE_NAME,
        version=VERSION,
        packages=find_packages(),
        include_package_data=True,
        install_requires=parse_requirements("requirements.txt"),
        python_requires=">=3.6.3",
        scripts=["scripts/icatagent"],
    )
