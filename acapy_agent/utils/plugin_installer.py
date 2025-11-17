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

    def _get_installed_plugin_version(self, plugin_name: str) -> Optional[dict]:
        """
        Get the version information of an installed plugin, including package version and installation source.
        
        Args:
            plugin_name: The name of the plugin module
            
        Returns:
            Dictionary with 'package_version' and optionally 'source_version' (git tag), or None if not found
        """
        result = {}
        
        try:
            # Try to get version from package metadata (pip installed packages)
            # First try the module name directly
            package_name_to_check = None
            try:
                version = get_package_version(plugin_name)
                package_name_to_check = plugin_name
                result["package_version"] = version
                LOGGER.debug("Found version for plugin '%s' via metadata: %s", plugin_name, version)
            except PackageNotFoundError:
                pass
            
            # Try common package name variations
            if "package_version" not in result:
                package_name = plugin_name.replace("_", "-")
                try:
                    version = get_package_version(package_name)
                    package_name_to_check = package_name
                    result["package_version"] = version
                    LOGGER.debug("Found version for plugin '%s' via metadata (as %s): %s", plugin_name, package_name, version)
                except PackageNotFoundError:
                    pass
            
            # Try acapy-plugin- prefix
            if "package_version" not in result:
                try:
                    prefixed_name = f"acapy-plugin-{plugin_name.replace('_', '-')}"
                    version = get_package_version(prefixed_name)
                    package_name_to_check = prefixed_name
                    result["package_version"] = version
                    LOGGER.debug("Found version for plugin '%s' via metadata (as %s): %s", plugin_name, prefixed_name, version)
                except PackageNotFoundError:
                    pass
            
            # Try to get version from module's __version__ attribute
            if "package_version" not in result:
                try:
                    module = importlib.import_module(plugin_name)
                    if hasattr(module, "__version__"):
                        version = str(module.__version__)
                        result["package_version"] = version
                        LOGGER.debug("Found version for plugin '%s' via __version__ attribute: %s", plugin_name, version)
                except (ImportError, AttributeError) as e:
                    LOGGER.debug("Could not get __version__ from plugin '%s': %s", plugin_name, e)
            
            # Try to get installation source (git tag) from pip metadata
            if package_name_to_check:
                try:
                    # First, try pip show to get direct URL information
                    try:
                        pip_show_result = subprocess.run(
                            [sys.executable, "-m", "pip", "show", package_name_to_check],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if pip_show_result.returncode == 0:
                            # Check for "Location:" field to find the package directory
                            location = None
                            for line in pip_show_result.stdout.split("\n"):
                                if line.startswith("Location:"):
                                    location = line.split(":", 1)[1].strip()
                                    break
                            
                            # Try to find direct_url.json in all possible locations
                            if location:
                                location_path = Path(location)
                                # Try to find .dist-info directory for this package
                                for item in location_path.iterdir():
                                    if item.is_dir() and item.name.endswith(".dist-info"):
                                        direct_url_file = item / "direct_url.json"
                                        if direct_url_file.exists():
                                            try:
                                                with open(direct_url_file, "r") as f:
                                                    direct_url_data = json.load(f)
                                                    # direct_url.json can have different formats
                                                    # Format 1: {"url": "git+https://...@tag#subdirectory=..."}
                                                    # Format 2: {"vcs_info": {...}, "url": "..."}
                                                    url_info = direct_url_data.get("url", "")
                                                    
                                                    # Try to extract from vcs_info if available
                                                    vcs_info = direct_url_data.get("vcs_info", {})
                                                    if vcs_info and vcs_info.get("vcs") == "git":
                                                        requested_revision = vcs_info.get("requested_revision")
                                                        if requested_revision:
                                                            result["source_version"] = requested_revision
                                                            LOGGER.debug("Found source version from vcs_info for plugin '%s': %s", plugin_name, requested_revision)
                                                            break
                                                    
                                                    # Fallback: Extract from URL
                                                    if url_info and "@" in url_info and "github.com" in url_info:
                                                        parts = url_info.split("@")
                                                        if len(parts) > 1:
                                                            tag_part = parts[1].split("#")[0] if "#" in parts[1] else parts[1]
                                                            # Check if it looks like a version tag (not a commit hash)
                                                            if "." in tag_part or tag_part in ["main", "master", "develop"]:
                                                                result["source_version"] = tag_part
                                                                LOGGER.debug("Found source version from URL for plugin '%s': %s", plugin_name, tag_part)
                                                                break
                                            except (json.JSONDecodeError, IOError) as e:
                                                LOGGER.debug("Could not read direct_url.json for plugin '%s': %s", plugin_name, e)
                    except Exception as e:
                        LOGGER.debug("Could not get installation source from pip show for plugin '%s': %s", plugin_name, e)
                    
                    # Fallback: Try to find distribution and check direct_url.json
                    if "source_version" not in result:
                        for dist in distributions():
                            if dist.metadata["Name"].lower() == package_name_to_check.lower():
                                # Try multiple path formats for direct_url.json
                                dist_location = Path(dist.location)
                                package_name = dist.metadata["Name"]
                                package_version = dist.version
                                
                                # Try different naming conventions for .dist-info directory
                                dist_info_names = [
                                    f"{package_name}-{package_version}.dist-info",
                                    f"{package_name.replace('-', '_')}-{package_version}.dist-info",
                                    f"{package_name.replace('.', '_')}-{package_version}.dist-info",
                                ]
                                
                                for dist_info_name in dist_info_names:
                                    dist_info_dir = dist_location / dist_info_name
                                    direct_url_file = dist_info_dir / "direct_url.json"
                                    
                                    if direct_url_file.exists():
                                        try:
                                            with open(direct_url_file, "r") as f:
                                                direct_url_data = json.load(f)
                                                vcs_info = direct_url_data.get("vcs_info", {})
                                                if vcs_info and vcs_info.get("vcs") == "git":
                                                    requested_revision = vcs_info.get("requested_revision")
                                                    if requested_revision:
                                                        result["source_version"] = requested_revision
                                                        LOGGER.debug("Found source version from direct_url.json vcs_info for plugin '%s': %s", plugin_name, requested_revision)
                                                        break
                                                
                                                url_info = direct_url_data.get("url", "")
                                                if url_info and "@" in url_info and "github.com" in url_info:
                                                    parts = url_info.split("@")
                                                    if len(parts) > 1:
                                                        tag_part = parts[1].split("#")[0] if "#" in parts[1] else parts[1]
                                                        if "." in tag_part or tag_part in ["main", "master", "develop"]:
                                                            result["source_version"] = tag_part
                                                            LOGGER.debug("Found source version from direct_url.json URL for plugin '%s': %s", plugin_name, tag_part)
                                                            break
                                        except (json.JSONDecodeError, IOError) as e:
                                            LOGGER.debug("Could not read direct_url.json for plugin '%s': %s", plugin_name, e)
                                
                                if "source_version" in result:
                                    break
                    
                    # Last fallback: Try pip freeze to get installation source
                    if "source_version" not in result:
                        try:
                            pip_freeze_result = subprocess.run(
                                [sys.executable, "-m", "pip", "freeze"],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            if pip_freeze_result.returncode == 0:
                                for line in pip_freeze_result.stdout.split("\n"):
                                    # Look for package installed from git
                                    # Format: package==version @ git+https://github.com/...@tag#subdirectory=...
                                    # or: package @ git+https://github.com/...@tag#subdirectory=...
                                    line_lower = line.lower()
                                    if (package_name_to_check.lower() in line_lower or 
                                        package_name_to_check.replace("-", "_").lower() in line_lower) and "@ git+" in line:
                                        # Extract the git URL part
                                        if "@ git+" in line:
                                            git_part = line.split("@ git+")[1]
                                            if "@" in git_part:
                                                tag_part = git_part.split("@")[1].split("#")[0] if "#" in git_part.split("@")[1] else git_part.split("@")[1]
                                                if "." in tag_part or tag_part in ["main", "master", "develop"]:
                                                    result["source_version"] = tag_part
                                                    LOGGER.debug("Found source version from pip freeze for plugin '%s': %s", plugin_name, tag_part)
                                                    break
                        except Exception as e:
                            LOGGER.debug("Could not get installation source from pip freeze for plugin '%s': %s", plugin_name, e)
                            
                except Exception as e:
                    LOGGER.debug("Could not get installation source for plugin '%s': %s", plugin_name, e)
            
            # Return the result if we found at least package_version
            if "package_version" in result:
                return result
                
        except Exception as e:
            LOGGER.debug("Error determining version for plugin '%s': %s", plugin_name, e)
        
        LOGGER.debug("Could not determine version for plugin '%s' using any method", plugin_name)
        return None

    def _get_plugin_source(self, plugin_name: str) -> str:
        """Get the installation source for a plugin from acapy-plugins repository."""
        # Install from acapy-plugins repo
        # Use provided version or current ACA-Py version
        version_to_use = self.plugin_version if self.plugin_version is not None else __version__
        plugin_source = (
            f"git+https://github.com/openwallet-foundation/acapy-plugins@{version_to_use}"
            f"#subdirectory={plugin_name}"
        )
        LOGGER.info(
            "Installing plugin '%s' from acapy-plugins repository (version %s)",
            plugin_name,
            version_to_use,
        )
        LOGGER.debug("Installation source: %s", plugin_source)
        return plugin_source

    def _install_plugin(self, plugin_source: str, plugin_name: str = None, upgrade: bool = False) -> bool:
        """
        Install a plugin using pip.

        Args:
            plugin_source: The pip installable source (package name, git URL, etc.)
            plugin_name: Optional plugin name for logging
            upgrade: Whether to upgrade/reinstall if already installed

        Returns:
            True if installation succeeded, False otherwise
        """
        try:
            # Extract version from source for logging
            version_info = ""
            if "@" in plugin_source:
                # Extract version/tag from git URL or package version
                parts = plugin_source.split("@")
                if len(parts) > 1:
                    version_part = parts[1].split("#")[0] if "#" in parts[1] else parts[1]
                    version_info = f" (version: {version_part})"
            
            log_name = plugin_name if plugin_name else plugin_source
            if upgrade:
                LOGGER.info("Upgrading plugin '%s'%s", log_name, version_info)
                LOGGER.debug("Upgrade source: %s", plugin_source)
            else:
                LOGGER.info("Installing plugin '%s'%s", log_name, version_info)
                LOGGER.debug("Installation source: %s", plugin_source)

            # Use pip programmatically to install
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-cache-dir",
            ]
            
            if upgrade:
                # Use --upgrade --force-reinstall to ensure correct version
                cmd.extend(["--upgrade", "--force-reinstall", "--no-deps"])
            
            cmd.append(plugin_source)

            # Run pip install
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                if upgrade:
                    LOGGER.info("Successfully upgraded plugin '%s'%s", log_name, version_info)
                else:
                    LOGGER.info("Successfully installed plugin '%s'%s", log_name, version_info)
                return True
            else:
                action = "upgrade" if upgrade else "install"
                LOGGER.error(
                    "Failed to %s plugin '%s'%s: %s", action, log_name, version_info, result.stderr
                )
                return False

        except Exception as e:
            LOGGER.error("Error installing plugin %s: %s", plugin_source, e)
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
            # If plugin exists and is importable, assume it's fine (might be from git/main)
            if installed_package_version:
                # Try to match with ACA-Py version if possible
                normalized_installed = installed_package_version.split("+")[0].split("-")[0].strip()
                normalized_target = target_version.split("+")[0].split("-")[0].strip()
                if normalized_installed == normalized_target:
                    LOGGER.info(
                        "Plugin '%s' is already installed with correct version: %s",
                        plugin_name,
                        installed_package_version,
                    )
                    self.installed_plugins.add(plugin_name)
                    return True
            # Plugin exists but version doesn't match or can't be determined
            # Since we're using current ACA-Py version, reinstall to be safe
            LOGGER.info(
                "Plugin '%s' exists but version check inconclusive. "
                "Reinstalling to ensure correct version (%s)...",
                plugin_name,
                target_version,
            )
        elif plugin_exists and self.plugin_version:
            # Explicit version specified - check if source version matches
            if installed_source_version and installed_source_version == target_version:
                # Source version matches - check if we should still reinstall
                LOGGER.info(
                    "Plugin '%s' is already installed from source version %s (package version: %s). "
                    "Skipping reinstallation.",
                    plugin_name,
                    installed_source_version,
                    installed_package_version or "unknown",
                )
                self.installed_plugins.add(plugin_name)
                return True
            elif installed_package_version:
                # Try to compare package versions
                normalized_installed = installed_package_version.split("+")[0].split("-")[0].strip()
                normalized_target = target_version.split("+")[0].split("-")[0].strip()
                # Check if it looks like a version number match (not a git ref)
                try:
                    if (normalized_installed.count(".") >= 1 and 
                        normalized_target.count(".") >= 1 and
                        normalized_installed == normalized_target):
                        # Package version matches, but source might be different
                        # Still reinstall to ensure correct git tag
                        LOGGER.info(
                            "Plugin '%s' package version matches (%s) but checking source version...",
                            plugin_name,
                            installed_package_version,
                        )
                except Exception:
                    pass
            # Version mismatch or can't determine - upgrade
            if installed_source_version:
                LOGGER.info(
                    "Plugin '%s' source version mismatch: installed=%s, target=%s. "
                    "Upgrading to version %s...",
                    plugin_name,
                    installed_source_version,
                    target_version,
                    target_version,
                )
            elif installed_package_version:
                LOGGER.info(
                    "Plugin '%s' version mismatch: installed=%s, target=%s. "
                    "Upgrading to version %s...",
                    plugin_name,
                    installed_package_version,
                    target_version,
                    target_version,
                )
            else:
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
            
            # Check version after successful import
            verified_version_info = self._get_installed_plugin_version(plugin_name)
            if verified_version_info:
                verified_package_version = verified_version_info.get("package_version")
                verified_source_version = verified_version_info.get("source_version")
                
                # Check if source version matches (for git-installed packages)
                if verified_source_version and verified_source_version == target_version:
                    self.installed_plugins.add(plugin_name)
                    if is_upgrade:
                        LOGGER.info(
                            "Plugin '%s' successfully upgraded to source version %s (package version: %s)",
                            plugin_name,
                            verified_source_version,
                            verified_package_version or "unknown",
                        )
                    else:
                        LOGGER.info(
                            "Plugin '%s' successfully installed (source version: %s, package version: %s)",
                            plugin_name,
                            verified_source_version,
                            verified_package_version or "unknown",
                        )
                    return True
                elif verified_package_version:
                    # Normalize package versions for comparison
                    normalized_installed = verified_package_version.split("+")[0].split("-")[0].strip()
                    normalized_target = target_version.split("+")[0].split("-")[0].strip()
                    
                    if normalized_installed == normalized_target:
                        self.installed_plugins.add(plugin_name)
                        if is_upgrade:
                            LOGGER.info(
                                "Plugin '%s' successfully upgraded (package version: %s)",
                                plugin_name,
                                verified_package_version,
                            )
                        else:
                            LOGGER.info(
                                "Plugin '%s' successfully installed (package version: %s)",
                                plugin_name,
                                verified_package_version,
                            )
                        return True
                    else:
                        LOGGER.warning(
                            "Plugin '%s' installed package version (%s) doesn't match target (%s), "
                            "but plugin is importable. Continuing with installed version.",
                            plugin_name,
                            verified_package_version,
                            target_version,
                        )
                        self.installed_plugins.add(plugin_name)
                        return True
                else:
                    # Version info available but no package or source version
                    self.installed_plugins.add(plugin_name)
                    if is_upgrade:
                        LOGGER.info(
                            "Plugin '%s' reinstalled successfully (version cannot be verified, target was %s)",
                            plugin_name,
                            target_version,
                        )
                    else:
                        LOGGER.info(
                            "Plugin '%s' installed successfully (version cannot be verified, target was %s)",
                            plugin_name,
                            target_version,
                        )
                    return True
            else:
                # Can't determine version, but plugin is importable - consider it successful
                if is_upgrade:
                    LOGGER.info(
                        "Plugin '%s' reinstalled successfully (version cannot be verified, target was %s)",
                        plugin_name,
                        target_version,
                    )
                else:
                    LOGGER.info(
                        "Plugin '%s' installed successfully (version cannot be verified, target was %s)",
                        plugin_name,
                        target_version,
                    )
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

