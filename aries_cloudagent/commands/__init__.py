from importlib import import_module
from typing import Sequence


def available_commands():
    return [
        {"name": "help", "summary": "Print available commands"},
        {"name": "provision", "summary": "Provision an agent"},
        {"name": "start", "summary": "Start a new agent process"},
    ]


def load_command(command: str):
    module = None
    module_path = None
    for cmd in available_commands():
        if cmd["name"] == command:
            module = cmd["name"]
            if "module" in cmd:
                module_path = cmd["module"]
            break
    if module and not module_path:
        module_path = f"{__package__}.{module}"
    if module_path:
        return import_module(module_path)


def run_command(command: str, argv: Sequence[str] = None):
    module = load_command(command) or load_command("help")
    module.execute(argv)
