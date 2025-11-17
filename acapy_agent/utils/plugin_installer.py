"""Plugin installer for dynamic plugin installation at runtime."""

import importlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

from importlib.metadata import version as get_package_version, PackageNotFoundError, distributions

from ..version import __version__

LOGGER = logging.getLogger(__name__)


class PluginInstaller:
    """Handles dynamic installation of ACA-Py plugins from the acapy-plugins repository."""

    def __init__(
        self,
        auto_install: bool = True,
        plugin_version: Optional[str] = None,
    ):
        """
        Initialize the plugin installer.

        Args:
            auto_install: Whether to automatically install missing plugins
            plugin_version: Version to use for plugin installation. If None, uses current ACA-Py version.
        """
        self.auto_install = auto_install
        self.plugin_version = plugin_version
        self.installed_plugins: Set[str] = set()

    def _try_get_package_version(self, names: List[str]) -> tuple[Optional[str], Optional[str]]:
        """Try to get package version from multiple name variations. Returns (version, package_name)."""
        for name in names:
            try:
                return get_package_version(name), name
            except PackageNotFoundError:
                continue
        return None, None
    
    def _extract_source_version_from_direct_url(self, direct_url_data: dict) -> Optional[str]:
        """Extract git tag/version from direct_url.json data."""
        vcs_info = direct_url_data.get("vcs_info", {})
        if vcs_info.get("vcs") == "git":
            revision = vcs_info.get("requested_revision")
            if revision and ("." in revision or revision in ["main", "master", "develop"]):
                return revision
        
        url = direct_url_data.get("url", "")
        if "@" in url and "github.com" in url:
            tag = url.split("@")[1].split("#")[0]
            if "." in tag or tag in ["main", "master", "develop"]:
                return tag
        return None
    
    def _get_source_version_from_dist_info(self, package_name: str) -> Optional[str]:
        """Get source version from pip's .dist-info/direct_url.json file."""
        # Try pip show to find location
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                location = next(
                    (line.split(":", 1)[1].strip() for line in result.stdout.split("\n") if line.startswith("Location:")),
                    None
                )
                if location:
                    for item in Path(location).iterdir():
                        if item.is_dir() and item.name.endswith(".dist-info"):
                            direct_url_file = item / "direct_url.json"
                            if direct_url_file.exists():
                                try:
                                    with open(direct_url_file) as f:
                                        source_version = self._extract_source_version_from_direct_url(json.load(f))
                                        if source_version:
                                            return source_version
                                except (json.JSONDecodeError, IOError):
                                    pass
        except Exception:
            pass
        
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
                                source_version = self._extract_source_version_from_direct_url(json.load(f))
                                if source_version:
                                    return source_version
                        except (json.JSONDecodeError, IOError):
                            pass
        
        # Last resort: pip freeze
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if package_name.lower() in line.lower() and "@ git+" in line:
                        git_part = line.split("@ git+")[1]
                        if "@" in git_part:
                            tag = git_part.split("@")[1].split("#")[0]
                            if "." in tag or tag in ["main", "master", "develop"]:
                                return tag
        except Exception:
            pass
        return None
    
    def _get_installed_plugin_version(self, plugin_name: str) -> Optional[dict]:
        """Get version info of an installed plugin (package version and source version/git tag)."""
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
            try:
                module = importlib.import_module(plugin_name)
                if hasattr(module, "__version__"):
                    package_version = str(module.__version__)
            except (ImportError, AttributeError):
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
        """Get the installation source for a plugin from acapy-plugins repository."""
        version_to_use = self.plugin_version if self.plugin_version is not None else __version__
        return (
            f"git+https://github.com/openwallet-foundation/acapy-plugins@{version_to_use}"
            f"#subdirectory={plugin_name}"
        )

    def _install_plugin(self, plugin_source: str, plugin_name: str = None, upgrade: bool = False) -> bool:
        """Install a plugin using pip."""
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir"]
            if upgrade:
                cmd.extend(["--upgrade", "--force-reinstall", "--no-deps"])
            cmd.append(plugin_source)

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                action = "Upgraded" if upgrade else "Installed"
                LOGGER.info("%s plugin: %s", action, plugin_name or plugin_source)
                return True
            else:
                action = "upgrade" if upgrade else "install"
                LOGGER.error("Failed to %s plugin '%s': %s", action, plugin_name or plugin_source, result.stderr)
                return False
        except Exception as e:
            LOGGER.error("Error installing plugin %s: %s", plugin_name or plugin_source, e)
            return False

    def ensure_plugin_installed(self, plugin_name: str) -> bool:
        """
        Ensure a plugin is installed with the correct version. If not, or if version doesn't match, attempt to install it.

        Args:
            plugin_name: The name of the plugin module

        Returns:
            True if plugin is available (was already installed or successfully installed)
        """
        # Get target version
        target_version = self.plugin_version if self.plugin_version is not None else __version__
        
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
        
        # For git-installed packages, we check both package version and source version (git tag).
        # When a version is explicitly specified, we check if the source version matches.
        
        if plugin_exists and not self.plugin_version:
            # No explicit version specified - using current ACA-Py version
            if installed_package_version:
                normalized_installed = installed_package_version.split("+")[0].split("-")[0].strip()
                normalized_target = target_version.split("+")[0].split("-")[0].strip()
                if normalized_installed == normalized_target:
                    self.installed_plugins.add(plugin_name)
                    return True
        elif plugin_exists and self.plugin_version:
            # Explicit version specified - check if source version matches
            if installed_source_version and installed_source_version == target_version:
                self.installed_plugins.add(plugin_name)
                return True

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
        if self._install_plugin(plugin_source, plugin_name=plugin_name, upgrade=is_upgrade):
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
        """
        Ensure multiple plugins are installed.

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
    """
    Install plugins from a list of plugin names.

    Args:
        plugin_names: List of plugin module names to install
        auto_install: Whether to automatically install missing plugins
        plugin_version: Version to use for plugin installation. If None, uses current ACA-Py version.

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
    """
    Get the installed version information of a plugin, including package version and installation source.

    Args:
        plugin_name: The name of the plugin module

    Returns:
        Dictionary with 'package_version' and optionally 'source_version' (git tag), or None if not found
    """
    installer = PluginInstaller(auto_install=False)
    return installer._get_installed_plugin_version(plugin_name)


def list_plugin_versions(plugin_names: List[str] = None) -> dict:
    """
    Get version information for a list of plugins, or all installed plugins.

    Args:
        plugin_names: Optional list of plugin names to check. If None, attempts to detect installed plugins.

    Returns:
        Dictionary mapping plugin names to their version info dicts (or None if version cannot be determined)
    """
    installer = PluginInstaller(auto_install=False)
    result = {}

    if plugin_names:
        for plugin_name in plugin_names:
            version_info = installer._get_installed_plugin_version(plugin_name)
            result[plugin_name] = version_info
    else:
        # Try to detect installed plugins - this is limited without knowing what's installed
        # For now, just return empty dict - callers should provide plugin names
        pass

    return result

