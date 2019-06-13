"""The classloader provides utilties to dynamically load classes and modules."""

import inspect
import logging

from importlib import import_module

from .error import BaseError


class ModuleLoadError(BaseError):
    """Module load error."""


class ClassNotFoundError(BaseError):
    """Class not found error."""


class ClassLoader:
    """Class used to load classes from modules dynamically."""

    def __init__(self, base_path, super_class):
        """
        Initialize a ClassLoader instance.

        Args:
            base_path: The base dotted path to look for a relative import
            super_class: Look for a class that inherits from this class
        """
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        self.super_class = super_class

    def load(self, module_path, load_relative=False):
        """
        Load module by module path.

        Args:
            module_path: Dotted path to module
            load_relative: Should the method check in the
            configured base path for relative import

        Return:
            The loaded class

        Raises:
            ModuleLoadError: If there is an error loading the class
            ClassNotFoundError: If there is no class to load at specified path

        """
        # We can try to load the module relative to a given base path
        if load_relative:
            relative_module_path = ".".join([self.base_path, module_path])
            try:
                return self.load(relative_module_path)
            except ModuleLoadError:
                pass

        try:
            imported_module = import_module(module_path)
        except ModuleNotFoundError:
            error_message = f"Unable to import module {module_path}"
            self.logger.debug(error_message)
            raise ModuleLoadError(error_message)

        # Find an the first declared class that inherits from
        try:
            imported_class = next(
                obj
                for name, obj in inspect.getmembers(imported_module, inspect.isclass)
                if issubclass(obj, self.super_class) and obj is not self.super_class
            )
        except StopIteration:
            error_message = (
                f"Could not resolve a class that inherits from {self.super_class}"
            )
            self.logger.debug(error_message)
            raise ClassNotFoundError(error_message)

        return imported_class

    # TODO: dedupe logic in these functions
    @classmethod
    def load_module(cls, mod_path: str, default_module: str = None):
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

        try:
            mod = import_module(mod_path)
        except ModuleNotFoundError:
            raise ModuleLoadError(f"Unable to import module: {mod_path}")

        return mod

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

        # TODO: Add option to enforce inheritance of specified base class

        if "." in class_name:
            # import module and find class
            mod_path, class_name = class_name.rsplit(".", 1)
        elif default_module:
            mod_path = default_module
        else:
            raise ClassNotFoundError(f"Cannot resolve class name: {class_name}")

        try:
            mod = import_module(mod_path)
        except ModuleNotFoundError:
            raise ModuleLoadError(f"Unable to import module: {mod_path}")

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
