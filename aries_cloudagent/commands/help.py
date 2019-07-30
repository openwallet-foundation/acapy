"""Help command for indexing available commands."""

from argparse import ArgumentParser
from typing import Sequence


def execute(argv: Sequence[str] = None):
    """Execute the help command."""
    from . import available_commands, load_command

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    for cmd in available_commands():
        if cmd["name"] == "help":
            continue
        module = load_command(cmd["name"])
        subparser = subparsers.add_parser(cmd["name"], help=cmd["summary"])
        module.init_argument_parser(subparser)
    parser.print_help()


if __name__ == "__main__":
    execute()
