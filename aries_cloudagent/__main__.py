"""aries_cloudagent package entry point."""

import os
import sys


def init_debug(args):
    """Initialize debugging environment."""

    ENABLE_PTVSD = os.getenv("ENABLE_PTVSD", "").lower()
    ENABLE_PTVSD = ENABLE_PTVSD and ENABLE_PTVSD not in ("false", "0")

    ENABLE_PYDEVD_PYCHARM = os.getenv("ENABLE_PYDEVD_PYCHARM", "").lower()
    ENABLE_PYDEVD_PYCHARM = ENABLE_PYDEVD_PYCHARM and ENABLE_PYDEVD_PYCHARM not in (
        "false",
        "0",
    )
    PYDEVD_PYCHARM_HOST = os.getenv("PYDEVD_PYCHARM_HOST", "localhost")
    PYDEVD_PYCHARM_AGENT_PORT = int(os.getenv("PYDEVD_PYCHARM_AGENT_PORT", 5001))

    # --debug to use microsoft's visual studio remote debugger
    if ENABLE_PTVSD or "--debug" in args:
        try:
            import ptvsd

            ptvsd.enable_attach()
            print("ptvsd is running")
            print("=== Waiting for debugger to attach ===")
            # To pause execution until the debugger is attached:
            ptvsd.wait_for_attach()
        except ImportError:
            print("ptvsd library was not found")

    if ENABLE_PYDEVD_PYCHARM or "--debug-pycharm" in args:
        try:
            import pydevd_pycharm

            print(
                "aca-py remote debugging to "
                f"{PYDEVD_PYCHARM_HOST}:{PYDEVD_PYCHARM_AGENT_PORT}"
            )
            pydevd_pycharm.settrace(
                host=PYDEVD_PYCHARM_HOST,
                port=PYDEVD_PYCHARM_AGENT_PORT,
                stdoutToServer=True,
                stderrToServer=True,
                suspend=False,
            )
        except ImportError:
            print("pydevd_pycharm library was not found")


def run(args):
    """Execute aca-py."""
    from .commands import run_command  # noqa

    if len(args) > 1 and args[1] and args[1][0] != "-":
        command = args[1]
        args = args[2:]
    else:
        command = None
        args = args[1:]

    run_command(command, args)


def main(args):
    """Execute default entry point."""
    if __name__ == "__main__":
        init_debug(args)
        run(args)


main(sys.argv)
