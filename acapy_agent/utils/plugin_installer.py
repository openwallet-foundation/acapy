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
from subprocess import CompletedProcess
from typing import List, Optional, Set
from urllib.parse import urlparse

from ..version import __version__

LOGGER = logging.getLogger(__name__)

# Valid plugin name pattern: alphanumeric, underscore, hyphen, dot
# Must start with letter or underscore
VALID_PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")
PLUGIN_REPO_URL = "https://github.com/openwallet-foundation/acapy-plugins"
PYPROJECT_TOML = "pyproject.toml"
PIP_FREEZE_GIT_MARKER = "@ git+"


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


def _validate_plugin_source(plugin_source: str) -> bool:
    """Validate that a plugin source URL is safe for use in subprocess calls.

    Args:
        plugin_source: The plugin source URL to validate

    Returns:
        True if valid, False otherwise

    """
    if not plugin_source or len(plugin_source) > 500:
        return False

    # Check for shell injection characters
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    if any(char in plugin_source for char in dangerous_chars):
        return False

    # Validate it's a git+ URL format (expected from _get_plugin_source)
    # Format: git+https://github.com/...@version#subdirectory=...
    # Or allow standard pip package names
    if plugin_source.startswith("git+"):
        # Parse and validate git URL structure
        try:
            # Extract the base URL part (after git+)
            url_with_version = plugin_source[4:]  # Remove "git+"
            url_part = (
                url_with_version.split("@")[0]
                if "@" in url_with_version
                else url_with_version.split("#")[0]
            )
            # Must start with https:// for security
            if url_part.startswith("https://"):
                parsed = urlparse(url_part)
                # Must have a valid netloc (domain)
                if parsed.netloc:
                    return True
        except Exception:
            return False
    elif re.match(r"^[a-zA-Z0-9_.-]+$", plugin_source):
        # Allow simple package names (alphanumeric, dots, hyphens, underscores)
        return True

    return False


def _is_poetry_venv(venv_path: str) -> bool:
    """Check if the virtual environment path indicates Poetry management.

    Args:
        venv_path: Path to the virtual environment

    Returns:
        True if this looks like a Poetry-managed venv

    """
    venv_path_obj = Path(venv_path)
    # Check if this looks like a Poetry-managed venv
    # Poetry venvs are often named like "project-name-<hash>-py3.13"
    if not (venv_path_obj.name.endswith(".venv") or "poetry" in str(venv_path).lower()):
        return False

    # Check if pyproject.toml exists nearby (Poetry projects have it at root)
    parent = venv_path_obj.parent
    return (parent / PYPROJECT_TOML).exists() or (
        venv_path_obj.parent.parent.parent / PYPROJECT_TOML
    ).exists()


def _is_poetry_pyproject(pyproject_file: Path) -> bool:
    """Check if pyproject.toml file indicates Poetry usage.

    Args:
        pyproject_file: Path to pyproject.toml file

    Returns:
        True if pyproject.toml contains Poetry configuration

    """
    if not pyproject_file.exists():
        return False

    try:
        with open(pyproject_file, "r") as f:
            content = f.read()
            return "[tool.poetry]" in content or '[tool."poetry.core"]' in content
    except Exception:
        return False


def _get_pyproject_search_paths() -> List[Path]:
    """Get list of paths to search for pyproject.toml.

    Returns:
        List of directory paths to check

    """
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
        # It is safe to ignore errors here; failure to import the module or
        # resolve its path simply means we cannot add an extra search path
        # for pyproject.toml detection.
        pass

    return search_paths


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
    if venv_path and _is_poetry_venv(venv_path):
        return "poetry"

    # Check if we're in a Poetry project by looking for pyproject.toml
    for root_path in _get_pyproject_search_paths():
        if _is_poetry_pyproject(root_path / PYPROJECT_TOML):
            return "poetry"

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

    def _is_valid_revision(self, revision: str) -> bool:
        """Check if a revision/tag string is valid.

        Args:
            revision: The revision or tag to validate

        Returns:
            True if revision is valid

        """
        if not revision:
            return False
        return (
            "." in revision or revision in ["main", "master", "develop"]
        ) and re.match(r"^[a-zA-Z0-9._-]+$", revision)

    def _extract_tag_from_path(self, parsed_url) -> Optional[str]:
        """Extract tag from URL path (standard format).

        Args:
            parsed_url: Parsed URL object

        Returns:
            Tag string if found and valid, None otherwise

        """
        if "@" not in parsed_url.path:
            return None

        path_parts = parsed_url.path.rsplit("@", 1)
        if len(path_parts) != 2:
            return None

        tag = path_parts[1].split("#")[0]  # Remove fragment if present
        return tag if self._is_valid_revision(tag) else None

    def _extract_tag_from_netloc(self, parsed_url) -> Optional[str]:
        """Extract tag from URL netloc (non-standard format).

        Args:
            parsed_url: Parsed URL object

        Returns:
            Tag string if found and valid, None otherwise

        """
        if not parsed_url.scheme or "@" not in parsed_url.netloc:
            return None

        netloc_parts = parsed_url.netloc.rsplit("@", 1)
        if len(netloc_parts) != 2:
            return None

        tag = netloc_parts[1]
        return tag if self._is_valid_revision(tag) else None

    def _extract_version_from_url(self, url: str) -> Optional[str]:
        """Extract version tag from a Git URL.

        Args:
            url: The Git URL to parse

        Returns:
            Version tag if found, None otherwise

        """
        try:
            parsed = urlparse(url)
            # Try standard format first: @version in path
            tag = self._extract_tag_from_path(parsed)
            if tag:
                return tag

            # Fallback: non-standard format with @version in netloc
            tag = self._extract_tag_from_netloc(parsed)
            if tag:
                return tag
        except Exception:
            LOGGER.debug("Failed to parse URL: %s", url)
        return None

    def _extract_source_version_from_direct_url(
        self, direct_url_data: dict
    ) -> Optional[str]:
        """Extract git tag/version from direct_url.json data."""
        # Try vcs_info first (primary method)
        vcs_info = direct_url_data.get("vcs_info", {})
        if vcs_info.get("vcs") == "git":
            revision = vcs_info.get("requested_revision")
            if self._is_valid_revision(revision):
                return revision

        # Fallback: Try to extract version from URL if vcs_info didn't work
        # This handles edge cases where vcs_info.requested_revision might be missing
        url = direct_url_data.get("url", "")
        if url:
            return self._extract_version_from_url(url)

        return None

    def _get_location_from_pip_show(self, package_name: str) -> Optional[str]:
        """Get package location using pip show.

        Args:
            package_name: Name of the package

        Returns:
            Location path if found, None otherwise

        """
        try:
            cmd = _get_pip_command_base()
            cmd.extend(["show", package_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return None

            return next(
                (
                    line.split(":", 1)[1].strip()
                    for line in result.stdout.split("\n")
                    if line.startswith("Location:")
                ),
                None,
            )
        except Exception as e:
            LOGGER.exception(
                f"Error while trying to locate package '{package_name}': {e}"
            )
            return None

    def _read_direct_url_file(self, direct_url_file: Path) -> Optional[str]:
        """Read and extract version from a direct_url.json file.

        Args:
            direct_url_file: Path to direct_url.json file

        Returns:
            Source version if found, None otherwise

        """
        if not direct_url_file.exists():
            return None

        try:
            with open(direct_url_file) as f:
                source_version = self._extract_source_version_from_direct_url(
                    json.load(f)
                )
                return source_version
        except (json.JSONDecodeError, IOError) as e:
            LOGGER.debug(
                "Failed to read or parse direct_url.json for %s: %s",
                direct_url_file,
                e,
            )
            return None

    def _find_direct_url_in_location(self, location: str) -> Optional[str]:
        """Find and read direct_url.json in a package location.

        Args:
            location: Package installation location

        Returns:
            Source version if found, None otherwise

        """
        try:
            location_path = Path(location)
            for item in location_path.iterdir():
                if item.is_dir() and item.name.endswith(".dist-info"):
                    direct_url_file = item / "direct_url.json"
                    source_version = self._read_direct_url_file(direct_url_file)
                    if source_version:
                        return source_version
        except Exception as e:
            LOGGER.warning(
                "Failed to search location '%s' for direct_url.json: %s",
                location,
                e,
            )
        return None

    def _search_distributions_for_direct_url(self, package_name: str) -> Optional[str]:
        """Search installed distributions for direct_url.json.

        Args:
            package_name: Name of the package to search for

        Returns:
            Source version if found, None otherwise

        """
        for dist in distributions():
            if dist.metadata["Name"].lower() != package_name.lower():
                continue

            dist_location = Path(dist.location)
            pkg_name, pkg_version = dist.metadata["Name"], dist.version
            name_variants = [
                f"{pkg_name}-{pkg_version}.dist-info",
                f"{pkg_name.replace('-', '_')}-{pkg_version}.dist-info",
                f"{pkg_name.replace('.', '_')}-{pkg_version}.dist-info",
            ]

            for name_variant in name_variants:
                direct_url_file = dist_location / name_variant / "direct_url.json"
                source_version = self._read_direct_url_file(direct_url_file)
                if source_version:
                    return source_version

        return None

    def _extract_version_from_pip_freeze(self, package_name: str) -> Optional[str]:
        """Extract version from pip freeze output.

        Args:
            package_name: Name of the package

        Returns:
            Source version if found, None otherwise

        """
        try:
            cmd = _get_pip_command_base()
            cmd.append("freeze")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.split("\n"):
                if (
                    package_name.lower() not in line.lower()
                    or PIP_FREEZE_GIT_MARKER not in line
                ):
                    continue

                # Extract git URL from pip freeze line
                # Format: package==version @ git+https://github.com/org/repo@tag#subdirectory=...
                try:
                    git_url_part = line.split(PIP_FREEZE_GIT_MARKER, 1)[1]
                    parsed = urlparse(f"git+{git_url_part}")
                    # Try standard format first, then fallback
                    tag = self._extract_tag_from_path(parsed)
                    if tag:
                        return tag

                    tag = self._extract_tag_from_netloc(parsed)
                    if tag:
                        return tag
                except Exception:
                    LOGGER.debug("Failed to parse git URL from pip freeze line: %s", line)
                    continue
        except Exception as e:
            LOGGER.debug(
                "Exception occurred while running pip freeze to get source version "
                "for %s: %s",
                package_name,
                e,
                exc_info=True,
            )
        return None

    def _get_source_version_from_dist_info(self, package_name: str) -> Optional[str]:
        """Get source version from pip's .dist-info/direct_url.json file."""
        # Strategy 1: Use pip show to find location
        location = self._get_location_from_pip_show(package_name)
        if location:
            source_version = self._find_direct_url_in_location(location)
            if source_version:
                return source_version

        # Strategy 2: Search distributions
        source_version = self._search_distributions_for_direct_url(package_name)
        if source_version:
            return source_version

        # Strategy 3: Last resort - pip freeze
        return self._extract_version_from_pip_freeze(package_name)

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
            except (ImportError, AttributeError):
                # Catch import/attribute errors to prevent side effects from breaking
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

    def _extract_version_info(self, plugin_source: str) -> str:
        """Extract version information from plugin source URL for logging.

        Args:
            plugin_source: The plugin source URL

        Returns:
            Version info string (e.g., " (version: 1.0.0)") or empty string

        """
        if "@" not in plugin_source:
            return ""

        parts = plugin_source.split("@")
        if len(parts) <= 1:
            return ""

        version_part = parts[1].split("#")[0] if "#" in parts[1] else parts[1]
        return f" (version: {version_part})"

    def _log_installation_start(
        self, plugin_name: str, plugin_source: str, version_info: str, upgrade: bool
    ):
        """Log the start of plugin installation.

        Args:
            plugin_name: The plugin name
            plugin_source: The plugin source URL
            version_info: Version information string
            upgrade: Whether this is an upgrade

        """
        display_name = plugin_name or plugin_source
        if upgrade:
            LOGGER.info("Upgrading plugin '%s'%s", display_name, version_info)
        else:
            LOGGER.info("Installing plugin '%s'%s", display_name, version_info)

    def _build_install_command(self, plugin_source: str, upgrade: bool) -> List[str]:
        """Build the pip install command.

        Args:
            plugin_source: The plugin source URL
            upgrade: Whether to upgrade the plugin

        Returns:
            List of command parts

        """
        cmd = _get_pip_command()
        cmd.extend(["--no-cache-dir"])
        if upgrade:
            cmd.extend(["--upgrade", "--force-reinstall", "--no-deps"])
        cmd.append(plugin_source)
        return cmd

    def _handle_install_result(
        self,
        result: CompletedProcess,
        plugin_name: str,
        plugin_source: str,
        version_info: str,
        upgrade: bool,
    ) -> bool:
        """Handle the result of plugin installation.

        Args:
            result: The subprocess result
            plugin_name: The plugin name
            plugin_source: The plugin source URL
            version_info: Version information string
            upgrade: Whether this was an upgrade

        Returns:
            True if installation succeeded, False otherwise

        """
        display_name = plugin_name or plugin_source

        if result.returncode == 0:
            action = "Upgraded" if upgrade else "Installed"
            LOGGER.info(
                "Successfully %s plugin '%s'%s",
                action.lower(),
                display_name,
                version_info,
            )
            return True

        action = "upgrade" if upgrade else "install"
        LOGGER.error(
            "Failed to %s plugin '%s'%s: %s",
            action,
            display_name,
            version_info,
            result.stderr,
        )
        return False

    def _install_plugin(
        self, plugin_source: str, plugin_name: str, upgrade: bool = False
    ) -> bool:
        """Install a plugin using pip or poetry run pip.

        Args:
            plugin_source: The plugin source URL (should come from _get_plugin_source)
            plugin_name: The plugin name
            upgrade: Whether to upgrade the plugin

        Returns:
            True if installation succeeded, False otherwise

        Raises:
            ValueError: If plugin_source is invalid or unsafe

        """
        # Validate plugin_source to prevent command injection
        if not _validate_plugin_source(plugin_source):
            raise ValueError(
                f"Invalid or unsafe plugin_source: '{plugin_source}'. "
                "Plugin sources must be valid git+ URLs or safe package names. "
                "Use _get_plugin_source() to generate safe plugin sources."
            )

        try:
            version_info = self._extract_version_info(plugin_source)
            self._log_installation_start(
                plugin_name, plugin_source, version_info, upgrade
            )

            cmd = self._build_install_command(plugin_source, upgrade)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            return self._handle_install_result(
                result, plugin_name, plugin_source, version_info, upgrade
            )
        except Exception as e:
            LOGGER.error(
                "Error installing plugin %s: %s", plugin_name or plugin_source, e
            )
            return False

    def _check_plugin_exists(self, plugin_name: str) -> bool:
        """Check if a plugin can be imported (exists).

        Args:
            plugin_name: The name of the plugin module

        Returns:
            True if plugin can be imported, False otherwise

        """
        try:
            importlib.import_module(plugin_name)
            return True
        except ImportError:
            return False

    def _get_installed_version_info(
        self, plugin_name: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Get installed version information for a plugin.

        Args:
            plugin_name: The name of the plugin module

        Returns:
            Tuple of (package_version, source_version)

        """
        version_info = self._get_installed_plugin_version(plugin_name)
        if not version_info:
            return None, None

        return (
            version_info.get("package_version"),
            version_info.get("source_version"),
        )

    def _normalize_version(self, version: str) -> str:
        """Normalize version string by removing build/metadata suffixes.

        Args:
            version: Version string to normalize

        Returns:
            Normalized version string

        """
        return version.split("+")[0].split("-")[0].strip()

    def _check_version_matches_implicit(
        self,
        plugin_name: str,
        installed_package_version: Optional[str],
        target_version: str,
    ) -> bool:
        """Check if installed version matches target when no explicit version specified.

        Args:
            plugin_name: The name of the plugin module
            installed_package_version: Installed package version
            target_version: Target version to match

        Returns:
            True if versions match, False otherwise

        """
        if not installed_package_version:
            return False

        normalized_installed = self._normalize_version(installed_package_version)
        normalized_target = self._normalize_version(target_version)

        if normalized_installed == normalized_target:
            LOGGER.debug(
                "Plugin '%s' already installed with matching version: %s",
                plugin_name,
                installed_package_version,
            )
            return True

        return False

    def _check_version_matches_explicit(
        self,
        plugin_name: str,
        installed_source_version: Optional[str],
        installed_package_version: Optional[str],
        target_version: str,
    ) -> bool:
        """Check if installed version matches target when explicit version specified.

        Args:
            plugin_name: The name of the plugin module
            installed_source_version: Installed source version (git tag)
            installed_package_version: Installed package version
            target_version: Target version to match

        Returns:
            True if versions match, False otherwise

        """
        if installed_source_version and installed_source_version == target_version:
            LOGGER.info(
                "Plugin '%s' already installed from source version %s "
                "(package version: %s)",
                plugin_name,
                installed_source_version,
                installed_package_version or "unknown",
            )
            return True

        return False

    def _log_version_mismatch(
        self,
        plugin_name: str,
        installed_source_version: Optional[str],
        installed_package_version: Optional[str],
        target_version: str,
    ):
        """Log version mismatch details.

        Args:
            plugin_name: The name of the plugin module
            installed_source_version: Installed source version (git tag)
            installed_package_version: Installed package version
            target_version: Target version

        """
        if installed_source_version:
            LOGGER.info(
                "Plugin '%s' source version mismatch detected: "
                "installed=%s, target=%s. Upgrading plugin...",
                plugin_name,
                installed_source_version,
                target_version,
            )
        elif installed_package_version:
            LOGGER.info(
                "Plugin '%s' needs upgrade: current package version=%s, "
                "target version=%s. Upgrading plugin...",
                plugin_name,
                installed_package_version,
                target_version,
            )
        else:
            LOGGER.info(
                "Plugin '%s' is installed but version cannot be determined. "
                "Upgrading to ensure correct version (%s)...",
                plugin_name,
                target_version,
            )

    def _verify_plugin_import(self, plugin_name: str) -> bool:
        """Verify that an installed plugin can be imported.

        Args:
            plugin_name: The name of the plugin module

        Returns:
            True if plugin can be imported, False otherwise

        """
        try:
            importlib.import_module(plugin_name)
            return True
        except ImportError as e:
            LOGGER.error(
                "Plugin '%s' was installed but cannot be imported: %s",
                plugin_name,
                e,
            )
            return False

    def _check_and_handle_existing_plugin(
        self,
        plugin_name: str,
        installed_package_version: Optional[str],
        installed_source_version: Optional[str],
        target_version: str,
    ) -> bool:
        """Check if existing plugin version matches and handle accordingly.

        Args:
            plugin_name: The name of the plugin module
            installed_package_version: Installed package version
            installed_source_version: Installed source version
            target_version: Target version to match

        Returns:
            True if plugin is already correctly installed, False if needs installation

        """
        if not self.plugin_version:
            # No explicit version - check package version match
            if self._check_version_matches_implicit(
                plugin_name, installed_package_version, target_version
            ):
                self.installed_plugins.add(plugin_name)
                return True
            LOGGER.info(
                "Plugin '%s' exists but version check inconclusive. "
                "Reinstalling to ensure correct version (%s)...",
                plugin_name,
                target_version,
            )
        else:
            # Explicit version - check source version match
            if self._check_version_matches_explicit(
                plugin_name,
                installed_source_version,
                installed_package_version,
                target_version,
            ):
                self.installed_plugins.add(plugin_name)
                return True
            self._log_version_mismatch(
                plugin_name,
                installed_source_version,
                installed_package_version,
                target_version,
            )
        return False

    def _attempt_plugin_installation(
        self, plugin_name: str, plugin_exists: bool, target_version: str
    ) -> bool:
        """Attempt to install or upgrade a plugin.

        Args:
            plugin_name: The name of the plugin module
            plugin_exists: Whether plugin already exists
            target_version: Target version

        Returns:
            True if installation succeeded, False otherwise

        """
        if not self.auto_install:
            LOGGER.warning(
                "Plugin '%s' is not installed and auto-install is disabled", plugin_name
            )
            return False

        plugin_source = self._get_plugin_source(plugin_name)
        if self._install_plugin(
            plugin_source, plugin_name=plugin_name, upgrade=plugin_exists
        ) and self._verify_plugin_import(plugin_name):
            self.installed_plugins.add(plugin_name)
            return True

        LOGGER.error(
            "Failed to install plugin '%s' (version %s)",
            plugin_name,
            target_version,
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

        target_version = (
            self.plugin_version if self.plugin_version is not None else __version__
        )

        plugin_exists = self._check_plugin_exists(plugin_name)
        installed_package_version, installed_source_version = (
            self._get_installed_version_info(plugin_name)
            if plugin_exists
            else (None, None)
        )

        # Check if version matches (different logic for explicit vs implicit versions)
        if plugin_exists:
            if self._check_and_handle_existing_plugin(
                plugin_name,
                installed_package_version,
                installed_source_version,
                target_version,
            ):
                return True
        else:
            LOGGER.info(
                "Plugin '%s' not found. Installing version %s...",
                plugin_name,
                target_version,
            )

        return self._attempt_plugin_installation(
            plugin_name, plugin_exists, target_version
        )

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
