"""Guard test: every registered admin API route must enforce authentication.

This scans the source tree for ``web.<method>("/path", handler)`` route
registrations and asserts that each referenced handler is decorated with an
authentication decorator (``@tenant_authentication`` or
``@admin_authentication``). It prevents shipping an admin endpoint without
authentication - the class of bug where a handler is defined but the auth
decorator is simply forgotten (which a decorator's own unit tests cannot catch).
"""

import ast
from pathlib import Path

# Package root (acapy_agent/), derived from this file: tests -> admin -> acapy_agent
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

AUTH_DECORATORS = {"tenant_authentication", "admin_authentication"}
ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "head"}

# Handlers intentionally exposed without authentication.
ALLOWLISTED_HANDLERS = {
    "redirect_handler",  # GET / -> redirects to the API docs
    "liveliness_handler",  # GET /status/live -> orchestration liveness probe
    "readiness_handler",  # GET /status/ready -> orchestration readiness probe
    "websocket_handler",  # GET /ws -> enforces auth inline, not via decorator
}


def _decorator_names(func: ast.AST) -> set:
    """Return the simple names of all decorators on a function def."""
    names = set()
    for dec in func.decorator_list:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _is_web_route_call(node: ast.AST) -> bool:
    """True for a ``web.<method>(...)`` call registering a route."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ROUTE_METHODS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "web"
        and len(node.args) >= 2
    )


def _collect():
    """Scan the package and return (registrations, defs_by_name).

    registrations: list of (handler_name, method, path, source_file)
    defs_by_name: dict mapping function name -> list of (auth_bool, source_file)
    """
    registrations = []
    defs_by_name: dict[str, list] = {}

    for path in PACKAGE_ROOT.rglob("*.py"):
        if "/tests/" in path.as_posix() or path.name.startswith("test_"):
            continue
        source = path.read_text()
        if "web." not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_auth = bool(_decorator_names(node) & AUTH_DECORATORS)
                defs_by_name.setdefault(node.name, []).append((has_auth, path))
            elif _is_web_route_call(node):
                handler = node.args[1]
                if not isinstance(handler, ast.Name):
                    continue  # e.g. self.websocket_handler -> skipped
                path_arg = node.args[0]
                route = (
                    path_arg.value if isinstance(path_arg, ast.Constant) else "<dynamic>"
                )
                registrations.append(
                    (handler.id, node.func.attr.upper(), route, path)
                )

    return registrations, defs_by_name


def test_all_registered_routes_require_authentication():
    registrations, defs_by_name = _collect()

    # Sanity: the scan must actually find the route surface.
    assert len(registrations) > 100, (
        f"Route scan found too few registrations ({len(registrations)}); "
        "the audit heuristic is likely broken."
    )

    gaps = []
    for handler, method, route, source in registrations:
        if handler in ALLOWLISTED_HANDLERS:
            continue
        candidates = defs_by_name.get(handler)
        if not candidates:
            # Handler registered but no def found in scanned sources.
            gaps.append(f"{method} {route} -> {handler} (definition not found)")
            continue
        # Protected if every definition with this name enforces auth.
        if not all(has_auth for has_auth, _ in candidates):
            files = ", ".join(sorted({p.name for _, p in candidates}))
            gaps.append(f"{method} {route} -> {handler} (in {files})")

    assert not gaps, (
        "Registered admin API route handlers missing an authentication decorator "
        "(@tenant_authentication or @admin_authentication). Add the decorator, or "
        "if intentionally public add the handler to ALLOWLISTED_HANDLERS:\n  "
        + "\n  ".join(sorted(gaps))
    )
