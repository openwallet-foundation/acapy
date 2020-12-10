"""Help command for indexing available commands."""

from configargparse import ArgumentParser
from typing import Sequence

from ..version import __version__


def execute(argv: Sequence[str] = None):
    """Execute the help command."""
    from . import available_commands, load_command, PROG

    parser = ArgumentParser(prog=PROG)
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print application version and exit",
    )
    subparsers = parser.add_subparsers()
    for cmd in available_commands():
        if cmd["name"] == "help":
            continue
        module = load_command(cmd["name"])
        subparser = subparsers.add_parser(cmd["name"], help=cmd["summary"])
        module.init_argument_parser(subparser)
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
    else:
        parser.print_help()


def main():
    """Execute the main line."""
    if __name__ == "__main__":
        execute()


main()
