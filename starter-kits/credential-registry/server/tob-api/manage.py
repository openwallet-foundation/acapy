#!/usr/bin/env python
"""
Command-line utility for administrative tasks.
"""

import os
import sys

# if os.environ.get("DEBUG") == "true":
#     print("\nDebugging is enabled\n")
#     import ptvsd

#     ptvsd.enable_attach(address=("0.0.0.0", 3000))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tob_api.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
