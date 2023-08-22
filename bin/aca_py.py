#!/usr/bin/env python

import os
import subprocess
import sys


def find_python_executable():
    if "PYTHON" in os.environ:
        return os.environ["PYTHON"]
    python_executable = subprocess.getoutput("command -v python3")
    if not python_executable:
        python_executable = "python"
    return python_executable


def main():
    python_executable = find_python_executable()
    aries_cloudagent_args = sys.argv[1:]
    subprocess.run(
        [python_executable, "-m", "aries_cloudagent"] + aries_cloudagent_args
    )


if __name__ == "__main__":
    main()
