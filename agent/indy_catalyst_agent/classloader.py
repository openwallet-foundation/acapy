import inspect
import logging


from importlib import import_module


class ModuleLoadError(Exception):
    pass


class ClassNotFoundError(Exception):
    pass


class ClassLoader:
    def __init__(self, base_path, super_class):
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        self.super_class = super_class

    def load(self, module_path, load_relative=False):
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
