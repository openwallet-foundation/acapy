"""The classloader provides utilties to dynamically load classes and modules."""

import inspect
import pkg_resources
import sys

from importlib import import_module
from types import ModuleType
from typing import Sequence, Type

from .error import BaseError


class ModuleLoadError(BaseError):
    """Module load error."""


class ClassNotFoundError(BaseError):
    """Class not found error."""


class ClassLoader:
    """Class used to load classes from modules dynamically."""

    @classmethod
    def load_module(cls, mod_path: str) -> ModuleType:
        """
        Load a module by its absolute path.

        Args:
            mod_path: the absolute module path

        Returns:
            The resolved module or `None` if the module cannot be found

        Raises:
            ModuleLoadError: If there was an error loading the module

        """
        if mod_path in sys.modules:
            return sys.modules[mod_path]

        if "." in mod_path:
            parent_mod_path, mod_name = mod_path.rsplit(".", 1)
            parent_mod = cls.load_module(parent_mod_path)
            if not parent_mod:
                return None
            parent_path = parent_mod.__path__
        else:
            parent_path = None

        # Load the module spec first
        # this means that a later ModuleNotFoundError indicates a code issue
        spec = None
        for finder in sys.meta_path:
            if hasattr(finder, "find_spec"):
                spec = finder.find_spec(mod_path, parent_path)
                if spec is not None:
                    break
        if not spec:
            return None

        try:
            return import_module(mod_path)
        except ModuleNotFoundError as e:
            raise ModuleLoadError(
                f"Unable to import module {mod_path}: {str(e)}"
            ) from e

    @classmethod
    def load_class(cls, class_name: str, default_module: str = None):
        """
        Resolve a complete class path (ie. typing.Dict) to the class itself.

        Args:
            class_name: Class name
            default_module:  (Default value = None)

        Returns:
            The resolved class

        Raises:
            ClassNotFoundError: If the class could not be resolved at path
            ModuleLoadError: If there was an error loading the module

        """

        if "." in class_name:
            # import module and find class
            mod_path, class_name = class_name.rsplit(".", 1)
        elif default_module:
            mod_path = default_module
        else:
            raise ClassNotFoundError(
                f"Cannot resolve class name with no default module: {class_name}"
            )

        mod = cls.load_module(mod_path)
        if not mod:
            raise ClassNotFoundError(f"Module '{mod_path}' not found")

        resolved = getattr(mod, class_name, None)
        if not resolved:
            raise ClassNotFoundError(
                f"Class '{class_name}' not defined in module: {mod_path}"
            )
        if not isinstance(resolved, type):
            raise ClassNotFoundError(
                f"Resolved value is not a class: {mod_path}.{class_name}"
            )
        return resolved

    @classmethod
    def load_subclass_of(cls, base_class: Type, mod_path: str):
        """
        Resolve an implementation of a base path within a module.

        Args:
            base_class: the base class being implemented
            mod_path: the absolute module path

        Returns:
            The resolved class

        Raises:
            ClassNotFoundError: If the module or class implementation could not be found
            ModuleLoadError: If there was an error loading the module

        """

        mod = cls.load_module(mod_path)
        if not mod:
            raise ClassNotFoundError(f"Module '{mod_path}' not found")

        # Find an the first declared class that inherits from
        try:
            imported_class = next(
                obj
                for name, obj in inspect.getmembers(mod, inspect.isclass)
                if issubclass(obj, base_class) and obj is not base_class
            )
        except StopIteration:
            raise ClassNotFoundError(
                f"Could not resolve a class that inherits from {base_class}"
            ) from None
        return imported_class

    @classmethod
    def scan_subpackages(cls, package: str) -> Sequence[str]:
        """Return a list of sub-packages defined under a named package."""
        # FIXME use importlib.resources in python 3.7
        if "." in package:
            package, sub_pkg = package.split(".", 1)
        else:
            sub_pkg = "."
        if not pkg_resources.resource_isdir(package, sub_pkg):
            raise ModuleLoadError(f"Undefined package {package}")
        found = []
        for sub_path in pkg_resources.resource_listdir(package, sub_pkg):
            if pkg_resources.resource_exists(
                package, f"{sub_pkg}/{sub_path}/__init__.py"
            ):
                found.append(f"{package}.{sub_pkg}.{sub_path}")
        return found
