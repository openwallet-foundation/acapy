"""Plugin installer for dynamic plugin installation at runtime."""

import importlib
import json
import logging
import os
import re
import subprocess
import sys
from importlib.metadata import (
    PackageNotFoundError,
    distributions,
)
from importlib.metadata import (
    version as get_package_version,
)
from pathlib import Path
from shutil import which
from typing import List, Optional, Set
from urllib.parse import urlparse

from ..version import __version__

LOGGER = logging.getLogger(__name__)

# Valid plugin name pattern: alphanumeric, underscore, hyphen, dot
# Must start with letter or underscore
VALID_PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")
PLUGIN_REPO_URL = "https://github.com/openwallet-foundation/acapy-plugins"


def _validate_plugin_name(plugin_name: str) -> bool:
    """Validate that a plugin name is safe for use in URLs and file paths.

    Args:
        plugin_name: The plugin name to validate

    Returns:
        True if valid, False otherwise

    """
    if not plugin_name or len(plugin_name) > 100:
        return False
    return bool(VALID_PLUGIN_NAME_PATTERN.match(plugin_name))


def _sanitize_url_component(component: str) -> str:
    """Sanitize a URL component by removing unsafe characters.

    Args:
        component: The URL component to sanitize

    Returns:
        Sanitized component

    """
    # Remove any characters that could be used for URL injection
    return re.sub(r"[^a-zA-Z0-9_.-]", "", component)


def _detect_package_manager() -> Optional[str]:
    """Detect which package manager is being used (poetry, pip, etc.).

    Returns:
        "poetry" if Poetry is detected, None otherwise

    """
    # Check if poetry is available
    if not which("poetry"):
        return None

    # Check if we're in a Poetry-managed virtual environment
    # Poetry typically sets VIRTUAL_ENV to a path containing ".venv" or in Poetry's cache
    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        venv_path_obj = Path(venv_path)
        # Check if this looks like a Poetry-managed venv
        # Poetry venvs are often named like "project-name-<hash>-py3.13"
        if venv_path_obj.name.endswith(".venv") or "poetry" in str(venv_path).lower():
            # Check if pyproject.toml exists nearby (Poetry projects have it at root)
            parent = venv_path_obj.parent
            if (parent / "pyproject.toml").exists() or (
                (venv_path_obj.parent.parent.parent / "pyproject.toml")
            ).exists():
                return "poetry"

    # Check if we're in a Poetry project by looking for pyproject.toml
    # Look in current directory or project root
    search_paths = [Path.cwd()]

    # Also check from the acapy_agent module location (project root)
    try:
        from .. import __file__ as module_file

        module_path = Path(module_file).resolve()
        # Go up from acapy_agent/utils/plugin_installer.py to project root
        project_root = module_path.parent.parent.parent
        if project_root not in search_paths:
            search_paths.append(project_root)
    except Exception:
        pass

    # Check each potential project root for pyproject.toml
    for root_path in search_paths:
        pyproject_file = root_path / "pyproject.toml"
        if pyproject_file.exists():
            # Check if pyproject.toml has [tool.poetry] section
            try:
                with open(pyproject_file, "r") as f:
                    content = f.read()
                    if "[tool.poetry]" in content or '[tool."poetry.core"]' in content:
                        return "poetry"
            except Exception:
                continue

    return None


def _get_pip_command_base() -> List[str]:
    """Get the appropriate pip command base for the current environment.

    Returns:
        List of command parts to run pip
        (e.g., ["poetry", "run", "pip"] or [sys.executable, "-m", "pip"])

    """
    package_manager = _detect_package_manager()
    if package_manager == "poetry":
        # Use poetry run pip in Poetry environments
        return ["poetry", "run", "pip"]
    else:
        # Use sys.executable -m pip for regular Python environments
        return [sys.executable, "-m", "pip"]


def _get_pip_command() -> List[str]:
    """Get the appropriate pip install command for the current environment.

    Returns:
        List of command parts to run pip install

    """
    cmd = _get_pip_command_base()
    cmd.append("install")
    return cmd


class PluginInstaller:
    """Handles dynamic installation of ACA-Py plugins from acapy-plugins."""

    def __init__(
        self,
        auto_install: bool = True,
        plugin_version: Optional[str] = None,
    ):
        """Initialize the plugin installer.

        Args:
            auto_install: Whether to automatically install missing plugins
            plugin_version: Version to use for plugin installation.
                If None, uses current ACA-Py version.

        """
        self.auto_install = auto_install
        self.plugin_version = plugin_version
        self.installed_plugins: Set[str] = set()

    def _try_get_package_version(
        self, names: List[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Try to get package version from multiple name variations.

        Returns:
            (version, package_name) tuple

        """
        for name in names:
            try:
                return get_package_version(name), name
            except PackageNotFoundError:
                continue
        return None, None

    def _extract_source_version_from_direct_url(
        self, direct_url_data: dict
    ) -> Optional[str]:
        """Extract git tag/version from direct_url.json data."""
        vcs_info = direct_url_data.get("vcs_info", {})
        if vcs_info.get("vcs") == "git":
            revision = vcs_info.get("requested_revision")
            if revision and (
                "." in revision or revision in ["main", "master", "develop"]
            ):
                return revision

        if url := direct_url_data.get("url", ""):
            try:
                # Parse URL properly instead of using string splits
                parsed = urlparse(url)
                if parsed.scheme and "@" in parsed.netloc:
                    # Extract tag/revision from netloc (e.g., git+https://...@tag)
                    netloc_parts = parsed.netloc.rsplit("@", 1)
                    if len(netloc_parts) == 2:
                        tag = netloc_parts[1]
                        # Validate tag is safe
                        if "." in tag or tag in ["main", "master", "develop"]:
                            # Additional validation: tag should be alphanumeric
                            # or contain dots/hyphens
                            if re.match(r"^[a-zA-Z0-9._-]+$", tag):
                                return tag
            except Exception:
                LOGGER.debug("Failed to parse URL: %s", url)
        return None

    def _get_source_version_from_dist_info(self, package_name: str) -> Optional[str]:
        """Get source version from pip's .dist-info/direct_url.json file."""
        # Try pip show to find location
        try:
            cmd = _get_pip_command_base()
            cmd.extend(["show", package_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                location = next(
                    (
                        line.split(":", 1)[1].strip()
                        for line in result.stdout.split("\n")
                        if line.startswith("Location:")
                    ),
                    None,
                )
                if location:
                    for item in Path(location).iterdir():
                        if item.is_dir() and item.name.endswith(".dist-info"):
                            direct_url_file = item / "direct_url.json"
                            if direct_url_file.exists():
                                try:
                                    with open(direct_url_file) as f:
                                        source_version = (
                                            self._extract_source_version_from_direct_url(
                                                json.load(f)
                                            )
                                        )
                                        if source_version:
                                            return source_version
                                except (json.JSONDecodeError, IOError):
                                    pass
        except Exception as e:
            LOGGER.exception(f"Error while trying to locate direct_url.json for package '{package_name}': {e}")

        # Fallback: search distributions
        for dist in distributions():
            if dist.metadata["Name"].lower() == package_name.lower():
                dist_location = Path(dist.location)
                pkg_name, pkg_version = dist.metadata["Name"], dist.version
                for name_variant in [
                    f"{pkg_name}-{pkg_version}.dist-info",
                    f"{pkg_name.replace('-', '_')}-{pkg_version}.dist-info",
                    f"{pkg_name.replace('.', '_')}-{pkg_version}.dist-info",
                ]:
                    direct_url_file = dist_location / name_variant / "direct_url.json"
                    if direct_url_file.exists():
                        try:
                            with open(direct_url_file) as f:
                                source_version = (
                                    self._extract_source_version_from_direct_url(
                                        json.load(f)
                                    )
                                )
                                if source_version:
                                    return source_version
                        except (json.JSONDecodeError, IOError) as e:
                            LOGGER.debug(
                                "Failed to read or parse direct_url.json for %s: %s", direct_url_file, e
                            )

        # Last resort: pip freeze
        try:
            cmd = _get_pip_command_base()
            cmd.append("freeze")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if package_name.lower() in line.lower() and "@ git+" in line:
                        # Parse git URL properly
                        try:
                            # Extract git URL from pip freeze line
                            # Format: package==version @ git+https://...@tag#subdirectory=...
                            if "@ git+" in line:
                                git_url_part = line.split("@ git+", 1)[1]
                                parsed = urlparse(f"git+{git_url_part}")
                                if "@" in parsed.netloc:
                                    netloc_parts = parsed.netloc.rsplit("@", 1)
                                    if len(netloc_parts) == 2:
                                        tag = netloc_parts[1]
                                        # Validate tag is safe
                                        if (
                                            "." in tag
                                            or tag in ["main", "master", "develop"]
                                        ) and re.match(r"^[a-zA-Z0-9._-]+$", tag):
                                            return tag
                        except Exception:
                            LOGGER.debug(
                                "Failed to parse git URL from pip freeze line: %s", line
                            )
                            continue
        except Exception as e:
            LOGGER.debug("Exception occurred while running pip freeze to get source version for %s: %s", package_name, e, exc_info=True)
        return None

    def _get_installed_plugin_version(self, plugin_name: str) -> Optional[dict]:
        """Get version info of an installed plugin.

        Returns package version and source version (git tag) if available.
        """
        result = {}

        # Try to get package version from various name variations
        name_variants = [
            plugin_name,
            plugin_name.replace("_", "-"),
            f"acapy-plugin-{plugin_name.replace('_', '-')}",
        ]
        package_version, package_name = self._try_get_package_version(name_variants)

        if not package_version:
            # Try __version__ attribute
            # Note: We avoid importing the module if possible to prevent side effects
            # Only try this as a last resort
            try:
                # Check if module is already loaded before importing
                if plugin_name in sys.modules:
                    module = sys.modules[plugin_name]
                else:
                    # Only import if not already loaded to avoid side effects
                    module = importlib.import_module(plugin_name)
                if hasattr(module, "__version__"):
                    package_version = str(module.__version__)
            except (ImportError, AttributeError, Exception):
                # Catch all exceptions to prevent any side effects from breaking
                # version lookup
                pass

        if not package_version:
            return None

        result["package_version"] = package_version

        # Try to get source version (git tag) if we found a package name
        if package_name:
            source_version = self._get_source_version_from_dist_info(package_name)
            if source_version:
                result["source_version"] = source_version

        return result

    def _get_plugin_source(self, plugin_name: str) -> str:
        """Get the installation source for a plugin from acapy-plugins repository.

        Args:
            plugin_name: The plugin name (must be validated before calling)

        Returns:
            Git URL for installing the plugin

        Raises:
            ValueError: If plugin_name is invalid or unsafe

        """
        # Validate plugin name to prevent URL injection
        if not _validate_plugin_name(plugin_name):
            raise ValueError(
                f"Invalid plugin name: '{plugin_name}'. "
                "Plugin names must contain only alphanumeric characters, "
                "underscores, hyphens, and dots, and must start with a letter "
                "or underscore."
            )

        # Sanitize version if provided
        version_to_use = (
            self.plugin_version if self.plugin_version is not None else __version__
        )
        version_to_use = _sanitize_url_component(str(version_to_use))

        # Sanitize plugin name (though it should already be valid)
        sanitized_plugin_name = _sanitize_url_component(plugin_name)

        # Construct URL with validated and sanitized components
        return (
            f"git+{PLUGIN_REPO_URL}@{version_to_use}#subdirectory={sanitized_plugin_name}"
        )

    def _install_plugin(
        self, plugin_source: str, plugin_name: str, upgrade: bool = False
    ) -> bool:
        """Install a plugin using pip or poetry run pip."""
        try:
            # Extract version from source for logging
            version_info = ""
            if "@" in plugin_source:
                parts = plugin_source.split("@")
                if len(parts) > 1:
                    version_part = parts[1].split("#")[0] if "#" in parts[1] else parts[1]
                    version_info = f" (version: {version_part})"

            # Log before installation
            if upgrade:
                LOGGER.info(
                    "Upgrading plugin '%s'%s",
                    plugin_name or plugin_source,
                    version_info,
                )
            else:
                LOGGER.info(
                    "Installing plugin '%s'%s",
                    plugin_name or plugin_source,
                    version_info,
                )

            # Detect package manager and use appropriate command
            cmd = _get_pip_command()
            cmd.extend(["--no-cache-dir"])
            if upgrade:
                cmd.extend(["--upgrade", "--force-reinstall", "--no-deps"])
            cmd.append(plugin_source)

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                action = "Upgraded" if upgrade else "Installed"
                LOGGER.info(
                    "Successfully %s plugin '%s'%s",
                    action.lower(),
                    plugin_name or plugin_source,
                    version_info,
                )
                return True
            else:
                action = "upgrade" if upgrade else "install"
                LOGGER.error(
                    "Failed to %s plugin '%s'%s: %s",
                    action,
                    plugin_name or plugin_source,
                    version_info,
                    result.stderr,
                )
                return False
        except Exception as e:
            LOGGER.error(
                "Error installing plugin %s: %s", plugin_name or plugin_source, e
            )
            return False

    def ensure_plugin_installed(self, plugin_name: str) -> bool:
        """Ensure a plugin is installed with the correct version.

        If not installed or version doesn't match, attempt to install it.

        Args:
            plugin_name: The name of the plugin module (must be validated)

        Returns:
            True if plugin is available (was already installed or successfully installed)

        Raises:
            ValueError: If plugin_name is invalid or unsafe

        """
        # Validate plugin name before processing
        if not _validate_plugin_name(plugin_name):
            raise ValueError(
                f"Invalid plugin name: '{plugin_name}'. "
                "Plugin names must contain only alphanumeric characters, "
                "underscores, hyphens, and dots, and must start with a letter "
                "or underscore."
            )

        # Get target version
        target_version = (
            self.plugin_version if self.plugin_version is not None else __version__
        )

        # Check if plugin can be imported (exists)
        plugin_exists = False
        try:
            importlib.import_module(plugin_name)
            plugin_exists = True
        except ImportError:
            plugin_exists = False

        # Get installed version info if plugin exists
        installed_version_info = None
        installed_package_version = None
        installed_source_version = None
        if plugin_exists:
            installed_version_info = self._get_installed_plugin_version(plugin_name)
            if installed_version_info:
                installed_package_version = installed_version_info.get("package_version")
                installed_source_version = installed_version_info.get("source_version")

        # For git-installed packages, we check both package version and source
        # version (git tag). When a version is explicitly specified, we check
        # if the source version matches.

        if plugin_exists and not self.plugin_version:
            # No explicit version specified - using current ACA-Py version
            if installed_package_version:
                normalized_installed = (
                    installed_package_version.split("+")[0].split("-")[0].strip()
                )
                normalized_target = target_version.split("+")[0].split("-")[0].strip()
                if normalized_installed == normalized_target:
                    LOGGER.debug(
                        "Plugin '%s' already installed with matching version: %s",
                        plugin_name,
                        installed_package_version,
                    )
                    self.installed_plugins.add(plugin_name)
                    return True
            # Version check inconclusive - reinstall to be safe
            LOGGER.info(
                "Plugin '%s' exists but version check inconclusive. "
                "Reinstalling to ensure correct version (%s)...",
                plugin_name,
                target_version,
            )
        elif plugin_exists and self.plugin_version:
            # Explicit version specified - check if source version matches
            if installed_source_version and installed_source_version == target_version:
                LOGGER.info(
                    "Plugin '%s' already installed from source version %s "
                    "(package version: %s)",
                    plugin_name,
                    installed_source_version,
                    installed_package_version or "unknown",
                )
                self.installed_plugins.add(plugin_name)
                return True
            # Version mismatch detected - log upgrade details
            if installed_source_version:
                LOGGER.info(
                    "Plugin '%s' source version mismatch detected: "
                    "installed=%s, target=%s. Upgrading plugin...",
                    plugin_name,
                    installed_source_version,
                    target_version,
                )
            elif installed_package_version:
                # Source version not available, but package version exists
                # Still upgrade since we want specific git tag/version
                LOGGER.info(
                    "Plugin '%s' needs upgrade: current package version=%s, "
                    "target version=%s. Upgrading plugin...",
                    plugin_name,
                    installed_package_version,
                    target_version,
                )
            else:
                # Can't determine version, upgrade to ensure correct version
                LOGGER.info(
                    "Plugin '%s' is installed but version cannot be determined. "
                    "Upgrading to ensure correct version (%s)...",
                    plugin_name,
                    target_version,
                )
        elif not plugin_exists:
            # Plugin doesn't exist - install it
            LOGGER.info(
                "Plugin '%s' not found. Installing version %s...",
                plugin_name,
                target_version,
            )

        if not self.auto_install:
            LOGGER.warning(
                "Plugin '%s' is not installed and auto-install is disabled", plugin_name
            )
            return False

        # Determine if this is an upgrade (plugin exists)
        is_upgrade = plugin_exists

        # Get installation source from acapy-plugins repo
        plugin_source = self._get_plugin_source(plugin_name)

        # Attempt installation (with upgrade to ensure correct version)
        if self._install_plugin(
            plugin_source, plugin_name=plugin_name, upgrade=is_upgrade
        ):
            # Verify installation - first check if it can be imported
            try:
                importlib.import_module(plugin_name)
            except ImportError as e:
                LOGGER.error(
                    "Plugin '%s' was installed but cannot be imported: %s",
                    plugin_name,
                    e,
                )
                return False

            # Plugin installed and importable - success
            self.installed_plugins.add(plugin_name)
            return True
        else:
            LOGGER.error(
                "Failed to install plugin '%s' (version %s)",
                plugin_name,
                target_version,
            )

        return False

    def ensure_plugins_installed(self, plugin_names: List[str]) -> List[str]:
        """Ensure multiple plugins are installed.

        Args:
            plugin_names: List of plugin module names

        Returns:
            List of plugin names that failed to install

        """
        failed = []
        for plugin_name in plugin_names:
            if not self.ensure_plugin_installed(plugin_name):
                failed.append(plugin_name)

        return failed


def install_plugins_from_config(
    plugin_names: List[str],
    auto_install: bool = True,
    plugin_version: Optional[str] = None,
) -> List[str]:
    """Install plugins from a list of plugin names.

    Args:
        plugin_names: List of plugin module names to install
        auto_install: Whether to automatically install missing plugins
        plugin_version: Version to use for plugin installation.
            If None, uses current ACA-Py version.

    Returns:
        List of plugin names that failed to install

    """
    if not plugin_names:
        return []

    installer = PluginInstaller(
        auto_install=auto_install,
        plugin_version=plugin_version,
    )

    return installer.ensure_plugins_installed(plugin_names)


def get_plugin_version(plugin_name: str) -> Optional[dict]:
    """Get the installed version information of a plugin.

    Includes package version and installation source.

    Args:
        plugin_name: The name of the plugin module

    Returns:
        Dictionary with 'package_version' and optionally 'source_version'
        (git tag), or None if not found. Returns None if any error occurs.

    """
    try:
        installer = PluginInstaller(auto_install=False)
        return installer._get_installed_plugin_version(plugin_name)
    except Exception:
        # Silently fail version lookup - don't break plugin functionality
        LOGGER.debug(
            "Failed to get version info for plugin '%s'", plugin_name, exc_info=True
        )
        return None


def list_plugin_versions(plugin_names: List[str] = None) -> dict:
    """Get version information for a list of plugins, or all installed plugins.

    Args:
        plugin_names: Optional list of plugin names to check.
            If None, attempts to detect installed plugins.

    Returns:
        Dictionary mapping plugin names to their version info dicts
        (or None if version cannot be determined)

    """
    installer = PluginInstaller(auto_install=False)
    result = {}

    if plugin_names:
        for plugin_name in plugin_names:
            version_info = installer._get_installed_plugin_version(plugin_name)
            result[plugin_name] = version_info
    else:
        # Try to detect installed plugins - limited without knowing what's
        # installed
        # For now, just return empty dict - callers should provide plugin names
        pass

    return result
