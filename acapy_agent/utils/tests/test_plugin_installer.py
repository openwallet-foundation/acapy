"""Unit tests for plugin installer functionality."""

import sys
from importlib.metadata import PackageNotFoundError
from unittest import TestCase
from unittest.mock import MagicMock, Mock, mock_open, patch

from ..plugin_installer import (
    PluginInstaller,
    _detect_package_manager,
    _get_pip_command,
    _get_pip_command_base,
    _sanitize_url_component,
    _validate_plugin_name,
    get_plugin_version,
    install_plugins_from_config,
)


class TestValidatePluginName(TestCase):
    """Test plugin name validation."""

    def test_valid_plugin_names(self):
        """Test that valid plugin names pass validation."""
        valid_names = [
            "webvh",
            "plugin_name",
            "plugin-name",
            "plugin.name",
            "Plugin123",
            "plugin_123",
            "_plugin",
            "a" * 100,  # Max length
        ]
        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(_validate_plugin_name(name))

    def test_invalid_plugin_names(self):
        """Test that invalid plugin names fail validation."""
        invalid_names = [
            "",
            None,
            "plugin/name",  # Contains slash
            "plugin name",  # Contains space
            "plugin@name",  # Contains @
            "plugin#name",  # Contains #
            "plugin?name",  # Contains ?
            "123plugin",  # Starts with number
            "-plugin",  # Starts with hyphen
            "a" * 101,  # Too long
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(_validate_plugin_name(name))


class TestSanitizeUrlComponent(TestCase):
    """Test URL component sanitization."""

    def test_sanitize_valid_components(self):
        """Test sanitization of valid components."""
        test_cases = [
            ("webvh", "webvh"),
            ("plugin-name", "plugin-name"),
            ("plugin_name", "plugin_name"),
            ("1.3.2", "1.3.2"),
            ("plugin.name", "plugin.name"),
        ]
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                self.assertEqual(_sanitize_url_component(input_val), expected)

    def test_sanitize_unsafe_components(self):
        """Test sanitization removes unsafe characters."""
        test_cases = [
            ("plugin/name", "pluginname"),
            ("plugin name", "pluginname"),
            ("plugin@name", "pluginname"),
            ("plugin#name", "pluginname"),
            ("plugin?name", "pluginname"),
            ("plugin:name", "pluginname"),
        ]
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                self.assertEqual(_sanitize_url_component(input_val), expected)


class TestDetectPackageManager(TestCase):
    """Test package manager detection."""

    @patch("acapy_agent.utils.plugin_installer.which")
    @patch.dict("os.environ", {}, clear=True)
    @patch("acapy_agent.utils.plugin_installer.Path")
    def test_no_poetry_available(self, mock_path, mock_which):
        """Test when Poetry is not available."""
        mock_which.return_value = None
        result = _detect_package_manager()
        self.assertIsNone(result)

    @patch("acapy_agent.utils.plugin_installer.which")
    @patch.dict("os.environ", {"VIRTUAL_ENV": "/path/to/venv"})
    @patch("acapy_agent.utils.plugin_installer.Path")
    def test_poetry_detected_from_venv(self, mock_path_class, mock_which):
        """Test Poetry detection from virtual environment."""
        mock_which.return_value = "/usr/bin/poetry"

        # Mock Path for venv path
        mock_venv_path = MagicMock()
        mock_venv_path.name = "project-name-hash-py3.13"
        mock_venv_path.parent = MagicMock()
        mock_venv_path.parent.__truediv__ = MagicMock(
            return_value=MagicMock(exists=lambda: True)
        )

        # Mock Path class to return venv path when called
        mock_path_class.return_value = mock_venv_path

        # Mock reading pyproject.toml
        with patch("builtins.open", mock_open(read_data="[tool.poetry]\nname = 'test'")):
            result = _detect_package_manager()
            self.assertEqual(result, "poetry")

    @patch("acapy_agent.utils.plugin_installer.which")
    @patch.dict("os.environ", {}, clear=True)
    @patch("acapy_agent.utils.plugin_installer.Path")
    def test_poetry_detected_from_pyproject(self, mock_path_class, mock_which):
        """Test Poetry detection from pyproject.toml."""
        mock_which.return_value = "/usr/bin/poetry"

        # Mock Path.cwd() to have pyproject.toml
        mock_cwd = MagicMock()
        mock_pyproject = MagicMock()
        mock_pyproject.exists.return_value = True
        mock_cwd.__truediv__ = MagicMock(return_value=mock_pyproject)
        mock_path_class.cwd.return_value = mock_cwd

        # Mock reading pyproject.toml
        with patch("builtins.open", mock_open(read_data="[tool.poetry]\nname = 'test'")):
            result = _detect_package_manager()
            self.assertEqual(result, "poetry")

    @patch("acapy_agent.utils.plugin_installer.which")
    @patch.dict("os.environ", {"VIRTUAL_ENV": "/path/to/.venv"})
    @patch("acapy_agent.utils.plugin_installer.Path")
    def test_poetry_detected_from_venv_parent_path(self, mock_path_class, mock_which):
        """Test Poetry detection from venv parent path."""
        mock_which.return_value = "/usr/bin/poetry"

        # Mock venv path with .venv name
        mock_venv_path = MagicMock()
        mock_venv_path.name = ".venv"
        mock_venv_path.parent = MagicMock()
        mock_pyproject_parent = MagicMock()
        mock_pyproject_parent.exists.return_value = True
        mock_venv_path.parent.__truediv__ = MagicMock(return_value=mock_pyproject_parent)

        mock_path_class.return_value = mock_venv_path

        with patch("builtins.open", mock_open(read_data="[tool.poetry]\nname = 'test'")):
            result = _detect_package_manager()
            self.assertEqual(result, "poetry")

    @patch("acapy_agent.utils.plugin_installer.which")
    @patch.dict("os.environ", {}, clear=True)
    @patch("acapy_agent.utils.plugin_installer.Path")
    def test_poetry_detection_pyproject_read_exception(self, mock_path_class, mock_which):
        """Test Poetry detection when reading pyproject.toml raises exception."""
        mock_which.return_value = "/usr/bin/poetry"

        mock_cwd = MagicMock()
        mock_pyproject = MagicMock()
        mock_pyproject.exists.return_value = True
        mock_cwd.__truediv__ = MagicMock(return_value=mock_pyproject)
        mock_path_class.cwd.return_value = mock_cwd

        # Mock open to raise exception
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            result = _detect_package_manager()
            # Should continue searching other paths
            self.assertIsNone(result)  # No other paths configured in test


class TestGetPipCommandBase(TestCase):
    """Test pip command base construction."""

    @patch("acapy_agent.utils.plugin_installer._detect_package_manager")
    def test_poetry_command(self, mock_detect):
        """Test Poetry command construction."""
        mock_detect.return_value = "poetry"
        result = _get_pip_command_base()
        self.assertEqual(result, ["poetry", "run", "pip"])

    @patch("acapy_agent.utils.plugin_installer._detect_package_manager")
    def test_regular_pip_command(self, mock_detect):
        """Test regular pip command construction."""
        mock_detect.return_value = None
        result = _get_pip_command_base()
        self.assertEqual(result, [sys.executable, "-m", "pip"])

    @patch("acapy_agent.utils.plugin_installer._get_pip_command_base")
    def test_get_pip_command(self, mock_base):
        """Test pip install command construction."""
        mock_base.return_value = [sys.executable, "-m", "pip"]
        result = _get_pip_command()
        self.assertEqual(result, [sys.executable, "-m", "pip", "install"])


class TestPluginInstaller(TestCase):
    """Test PluginInstaller class."""

    def test_init_defaults(self):
        """Test PluginInstaller initialization with defaults."""
        installer = PluginInstaller()
        self.assertTrue(installer.auto_install)
        self.assertIsNone(installer.plugin_version)
        self.assertEqual(installer.installed_plugins, set())

    def test_init_with_version(self):
        """Test PluginInstaller initialization with version."""
        installer = PluginInstaller(auto_install=True, plugin_version="1.3.2")
        self.assertTrue(installer.auto_install)
        self.assertEqual(installer.plugin_version, "1.3.2")

    def test_get_plugin_source_default_version(self):
        """Test plugin source URL construction with default version."""
        installer = PluginInstaller()
        with patch("acapy_agent.utils.plugin_installer.__version__", "1.4.0"):
            result = installer._get_plugin_source("webvh")
            self.assertIn(
                "git+https://github.com/openwallet-foundation/acapy-plugins", result
            )
            self.assertIn("@1.4.0#subdirectory=webvh", result)

    def test_get_plugin_source_custom_version(self):
        """Test plugin source URL construction with custom version."""
        installer = PluginInstaller(plugin_version="1.3.2")
        result = installer._get_plugin_source("webvh")
        self.assertIn("@1.3.2#subdirectory=webvh", result)

    def test_get_plugin_source_invalid_name(self):
        """Test plugin source URL construction with invalid name."""
        installer = PluginInstaller()
        with self.assertRaises(ValueError) as context:
            installer._get_plugin_source("plugin/name")
        self.assertIn("Invalid plugin name", str(context.exception))

    def test_try_get_package_version_success(self):
        """Test successful package version lookup."""
        installer = PluginInstaller()
        with patch("acapy_agent.utils.plugin_installer.get_package_version") as mock_get:
            mock_get.side_effect = [PackageNotFoundError(), "1.2.3"]
            version, name = installer._try_get_package_version(["package1", "package2"])
            self.assertEqual(version, "1.2.3")
            self.assertEqual(name, "package2")

    def test_try_get_package_version_not_found(self):
        """Test package version lookup when not found."""
        installer = PluginInstaller()
        with patch("acapy_agent.utils.plugin_installer.get_package_version") as mock_get:
            mock_get.side_effect = PackageNotFoundError()
            version, name = installer._try_get_package_version(["package1"])
            self.assertIsNone(version)
            self.assertIsNone(name)

    def test_extract_source_version_from_direct_url_vcs_info(self):
        """Test source version extraction from vcs_info."""
        installer = PluginInstaller()
        direct_url_data = {
            "vcs_info": {
                "vcs": "git",
                "requested_revision": "1.3.2",
            },
            "url": "git+https://github.com/org/repo@1.3.2#subdirectory=plugin",
        }
        result = installer._extract_source_version_from_direct_url(direct_url_data)
        self.assertEqual(result, "1.3.2")

    def test_extract_source_version_from_direct_url_from_url(self):
        """Test source version extraction from URL."""
        installer = PluginInstaller()
        # URL format with @ in netloc: git+https://github.com@1.3.2/org/repo
        direct_url_data = {
            "vcs_info": {"vcs": "git"},
            "url": "git+https://github.com@1.3.2/org/repo#subdirectory=plugin",
        }
        result = installer._extract_source_version_from_direct_url(direct_url_data)
        # Should successfully extract version from netloc
        self.assertEqual(result, "1.3.2")

    def test_extract_source_version_from_direct_url_invalid(self):
        """Test source version extraction with invalid URL."""
        installer = PluginInstaller()
        direct_url_data = {
            "vcs_info": {"vcs": "git"},
            "url": "not-a-valid-url",
        }
        result = installer._extract_source_version_from_direct_url(direct_url_data)
        self.assertIsNone(result)

    def test_extract_source_version_from_direct_url_exception(self):
        """Test source version extraction when URL parsing raises exception."""
        installer = PluginInstaller()
        # Create a URL that will cause urlparse to work but rsplit to fail
        direct_url_data = {
            "vcs_info": {"vcs": "git"},
            "url": "git+https://github.com/org/repo",  # No @ tag
        }
        result = installer._extract_source_version_from_direct_url(direct_url_data)
        # Should return None when no version tag found
        self.assertIsNone(result)

    def test_extract_source_version_from_direct_url_branch(self):
        """Test source version extraction with branch name."""
        installer = PluginInstaller()
        direct_url_data = {
            "vcs_info": {
                "vcs": "git",
                "requested_revision": "main",
            },
        }
        result = installer._extract_source_version_from_direct_url(direct_url_data)
        self.assertEqual(result, "main")

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command_base")
    def test_get_source_version_from_dist_info_pip_show(
        self, mock_cmd_base, mock_subprocess
    ):
        """Test source version extraction via pip show."""
        installer = PluginInstaller()
        mock_cmd_base.return_value = ["pip"]
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Location: /path/to/package\n",
        )

        mock_path = MagicMock()
        mock_dist_info = MagicMock()
        mock_dist_info.is_dir.return_value = True
        mock_dist_info.name = "package-1.0.0.dist-info"
        mock_direct_url_file = MagicMock()
        mock_direct_url_file.exists.return_value = True
        mock_dist_info.__truediv__ = MagicMock(return_value=mock_direct_url_file)
        mock_path.iterdir.return_value = [mock_dist_info]

        with (
            patch("acapy_agent.utils.plugin_installer.Path", return_value=mock_path),
            patch(
                "builtins.open",
                mock_open(
                    read_data='{"url": "git+https://github.com/org/repo@1.3.2#subdirectory=plugin"}'
                ),
            ),
            patch.object(
                installer,
                "_extract_source_version_from_direct_url",
                return_value="1.3.2",
            ),
        ):
            result = installer._get_source_version_from_dist_info("package")
            self.assertEqual(result, "1.3.2")

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command_base")
    def test_get_source_version_from_dist_info_pip_show_failure(
        self, mock_cmd_base, mock_subprocess
    ):
        """Test source version extraction when pip show fails."""
        installer = PluginInstaller()
        mock_cmd_base.return_value = ["pip"]
        mock_subprocess.return_value = Mock(returncode=1, stdout="")

        # Test with distributions fallback
        mock_dist = MagicMock()
        mock_dist.metadata = {"Name": "package", "version": "1.0.0"}
        mock_dist.location = "/path/to/dist"
        mock_dist.version = "1.0.0"

        mock_dist_path = MagicMock()
        mock_direct_url_file = MagicMock()
        mock_direct_url_file.exists.return_value = True
        mock_dist_path.__truediv__ = MagicMock(return_value=mock_direct_url_file)

        with (
            patch(
                "acapy_agent.utils.plugin_installer.distributions",
                return_value=[mock_dist],
            ),
            patch("acapy_agent.utils.plugin_installer.Path") as mock_path_class,
            patch(
                "builtins.open",
                mock_open(
                    read_data='{"vcs_info": {"vcs": "git", "requested_revision": "1.3.2"}}'
                ),
            ),
        ):
            mock_path_class.return_value = mock_dist_path
            mock_dist_path.parent = mock_dist_path
            result = installer._get_source_version_from_dist_info("package")
            self.assertEqual(result, "1.3.2")

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command_base")
    def test_get_source_version_from_dist_info_pip_freeze(
        self, mock_cmd_base, mock_subprocess
    ):
        """Test source version extraction via pip freeze."""
        installer = PluginInstaller()
        mock_cmd_base.return_value = ["pip"]
        # First call fails (pip show), second succeeds (pip freeze)
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout=""),  # pip show fails
            Mock(
                returncode=0,
                stdout="package==1.0.0 @ git+https://github.com@1.3.2/org/repo#subdirectory=plugin\n",
            ),  # pip freeze succeeds with @ in netloc format
        ]

        with patch("acapy_agent.utils.plugin_installer.distributions", return_value=[]):
            result = installer._get_source_version_from_dist_info("package")
            self.assertEqual(result, "1.3.2")

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command_base")
    def test_get_source_version_from_dist_info_pip_freeze_exception(
        self, mock_cmd_base, mock_subprocess
    ):
        """Test source version extraction when pip freeze raises exception."""
        installer = PluginInstaller()
        mock_cmd_base.return_value = ["pip"]
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout=""),  # pip show fails
            Exception("Unexpected error"),  # pip freeze raises exception
        ]

        with patch("acapy_agent.utils.plugin_installer.distributions", return_value=[]):
            result = installer._get_source_version_from_dist_info("package")
            self.assertIsNone(result)

    def test_get_installed_plugin_version_not_found(self):
        """Test version lookup when plugin not found."""
        installer = PluginInstaller()
        with (
            patch.object(
                installer, "_try_get_package_version", return_value=(None, None)
            ),
            patch(
                "acapy_agent.utils.plugin_installer.importlib.import_module"
            ) as mock_import,
        ):
            mock_import.side_effect = ImportError("No module named 'test_plugin'")
            result = installer._get_installed_plugin_version("test_plugin")
            self.assertIsNone(result)

    def test_get_installed_plugin_version_found(self):
        """Test version lookup when plugin found."""
        installer = PluginInstaller()
        with (
            patch.object(
                installer,
                "_try_get_package_version",
                return_value=("1.2.3", "test-plugin"),
            ),
            patch.object(
                installer, "_get_source_version_from_dist_info", return_value="1.3.2"
            ),
        ):
            result = installer._get_installed_plugin_version("test_plugin")
            self.assertEqual(result["package_version"], "1.2.3")
            self.assertEqual(result["source_version"], "1.3.2")

    def test_get_installed_plugin_version_from_module(self):
        """Test version lookup from module __version__ attribute."""
        installer = PluginInstaller()
        mock_module = MagicMock()
        mock_module.__version__ = "1.5.0"

        with (
            patch.object(
                installer, "_try_get_package_version", return_value=(None, None)
            ),
            patch(
                "acapy_agent.utils.plugin_installer.importlib.import_module",
                return_value=mock_module,
            ),
        ):
            result = installer._get_installed_plugin_version("test_plugin")
            self.assertEqual(result["package_version"], "1.5.0")
            # No package_name, so no source_version
            self.assertNotIn("source_version", result)

    def test_get_installed_plugin_version_no_package_name(self):
        """Test version lookup when package name is None."""
        installer = PluginInstaller()
        mock_module = MagicMock()
        mock_module.__version__ = "1.5.0"

        with (
            patch.object(
                installer, "_try_get_package_version", return_value=("1.2.3", None)
            ),
            patch(
                "acapy_agent.utils.plugin_installer.importlib.import_module",
                return_value=mock_module,
            ),
        ):
            result = installer._get_installed_plugin_version("test_plugin")
            self.assertEqual(result["package_version"], "1.2.3")
            # No package_name, so no source_version lookup
            self.assertNotIn("source_version", result)

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command")
    def test_install_plugin_success(self, mock_cmd, mock_subprocess):
        """Test successful plugin installation."""
        installer = PluginInstaller()
        mock_cmd.return_value = ["pip", "install"]
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        result = installer._install_plugin(
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin",
            plugin_name="plugin",
        )
        self.assertTrue(result)
        mock_subprocess.assert_called_once()

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command")
    def test_install_plugin_failure(self, mock_cmd, mock_subprocess):
        """Test failed plugin installation."""
        installer = PluginInstaller()
        mock_cmd.return_value = ["pip", "install"]
        mock_subprocess.return_value = Mock(returncode=1, stderr="Error occurred")

        result = installer._install_plugin(
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin",
            plugin_name="plugin",
        )
        self.assertFalse(result)

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command")
    def test_install_plugin_upgrade(self, mock_cmd, mock_subprocess):
        """Test plugin upgrade."""
        installer = PluginInstaller()
        mock_cmd.return_value = ["pip", "install"]
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        installer._install_plugin(
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin",
            plugin_name="plugin",
            upgrade=True,
        )

        # Check that --upgrade flag was included
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("--upgrade", call_args)
        self.assertIn("--force-reinstall", call_args)
        self.assertIn("--no-deps", call_args)

    @patch("acapy_agent.utils.plugin_installer.subprocess.run")
    @patch("acapy_agent.utils.plugin_installer._get_pip_command")
    def test_install_plugin_exception(self, mock_cmd, mock_subprocess):
        """Test plugin installation exception handling."""
        installer = PluginInstaller()
        mock_cmd.return_value = ["pip", "install"]
        mock_subprocess.side_effect = Exception("Unexpected error")

        result = installer._install_plugin(
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin",
            plugin_name="plugin",
        )
        self.assertFalse(result)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch.object(PluginInstaller, "_get_plugin_source")
    @patch.object(PluginInstaller, "_install_plugin")
    def test_ensure_plugin_installed_not_installed(
        self, mock_install, mock_get_source, mock_get_version, mock_import
    ):
        """Test ensuring plugin is installed when not installed."""
        installer = PluginInstaller(auto_install=True)
        # First call raises ImportError (not installed), second succeeds (after install)
        mock_import.side_effect = [
            ImportError("No module named 'test_plugin'"),
            MagicMock(),  # After installation, import succeeds
        ]
        mock_get_version.return_value = None
        mock_get_source.return_value = (
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin"
        )
        mock_install.return_value = True

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertTrue(result)
        mock_install.assert_called_once()
        # Should be called twice: once to check if installed, once after install
        self.assertEqual(mock_import.call_count, 2)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    def test_ensure_plugin_installed_already_installed_matching_version(
        self, mock_get_version, mock_import
    ):
        """Test ensuring plugin when already installed with matching version."""
        installer = PluginInstaller(auto_install=True, plugin_version="1.3.2")
        mock_import.return_value = MagicMock()
        mock_get_version.return_value = {
            "package_version": "1.0.0",
            "source_version": "1.3.2",
        }

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertTrue(result)
        self.assertIn("test_plugin", installer.installed_plugins)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch.object(PluginInstaller, "_get_plugin_source")
    @patch.object(PluginInstaller, "_install_plugin")
    def test_ensure_plugin_installed_version_mismatch(
        self, mock_install, mock_get_source, mock_get_version, mock_import
    ):
        """Test ensuring plugin when version mismatch detected."""
        installer = PluginInstaller(auto_install=True, plugin_version="1.3.2")
        mock_import.return_value = MagicMock()
        mock_get_version.return_value = {
            "package_version": "1.0.0",
            "source_version": "1.3.1",  # Different version
        }
        mock_get_source.return_value = (
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin"
        )
        mock_install.return_value = True

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertTrue(result)
        mock_install.assert_called_once()

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    def test_ensure_plugin_installed_auto_install_disabled(
        self, mock_get_version, mock_import
    ):
        """Test ensuring plugin when auto-install is disabled."""
        installer = PluginInstaller(auto_install=False)
        mock_import.side_effect = ImportError("No module named 'test_plugin'")
        mock_get_version.return_value = None

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertFalse(result)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch("acapy_agent.utils.plugin_installer.__version__", "1.4.0")
    def test_ensure_plugin_installed_version_match_no_explicit_version(
        self, mock_get_version, mock_import
    ):
        """Test ensuring plugin when version matches without explicit version."""
        installer = PluginInstaller(auto_install=True, plugin_version=None)
        mock_import.return_value = MagicMock()
        # Using current version (normalized)
        mock_get_version.return_value = {"package_version": "1.4.0"}

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertTrue(result)
        self.assertIn("test_plugin", installer.installed_plugins)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch.object(PluginInstaller, "_get_plugin_source")
    @patch.object(PluginInstaller, "_install_plugin")
    def test_ensure_plugin_installed_import_fails_after_install(
        self, mock_install, mock_get_source, mock_get_version, mock_import
    ):
        """Test ensuring plugin when import fails after installation."""
        installer = PluginInstaller(auto_install=True)
        # First call: not installed, second call: still fails after install
        mock_import.side_effect = ImportError("No module named 'test_plugin'")
        mock_get_version.return_value = None
        mock_get_source.return_value = (
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin"
        )
        mock_install.return_value = True  # Installation "succeeds"

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertFalse(result)
        self.assertNotIn("test_plugin", installer.installed_plugins)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch.object(PluginInstaller, "_get_plugin_source")
    @patch.object(PluginInstaller, "_install_plugin")
    def test_ensure_plugin_installed_installation_fails(
        self, mock_install, mock_get_source, mock_get_version, mock_import
    ):
        """Test ensuring plugin when installation fails."""
        installer = PluginInstaller(auto_install=True)
        mock_import.side_effect = ImportError("No module named 'test_plugin'")
        mock_get_version.return_value = None
        mock_get_source.return_value = (
            "git+https://github.com/org/repo@1.3.2#subdirectory=plugin"
        )
        mock_install.return_value = False  # Installation fails

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertFalse(result)

    @patch("acapy_agent.utils.plugin_installer.importlib.import_module")
    @patch.object(PluginInstaller, "_get_installed_plugin_version")
    @patch.object(PluginInstaller, "_get_plugin_source")
    @patch.object(PluginInstaller, "_install_plugin")
    @patch("acapy_agent.utils.plugin_installer.__version__", "1.4.0")
    def test_ensure_plugin_installed_version_inconclusive(
        self, mock_install, mock_get_source, mock_get_version, mock_import
    ):
        """Test ensuring plugin when version check is inconclusive."""
        installer = PluginInstaller(auto_install=True, plugin_version=None)
        mock_import.return_value = MagicMock()
        # Version doesn't match or is None
        mock_get_version.return_value = {"package_version": "1.3.0"}
        mock_get_source.return_value = (
            "git+https://github.com/org/repo@1.4.0#subdirectory=plugin"
        )
        mock_install.return_value = True

        result = installer.ensure_plugin_installed("test_plugin")
        self.assertTrue(result)
        # Should reinstall due to version mismatch
        mock_install.assert_called_once()

    def test_ensure_plugin_installed_invalid_name(self):
        """Test ensuring plugin with invalid name."""
        installer = PluginInstaller()
        with self.assertRaises(ValueError):
            installer.ensure_plugin_installed("plugin/name")

    def test_ensure_plugins_installed_success(self):
        """Test ensuring multiple plugins are installed."""
        installer = PluginInstaller(auto_install=True)
        with patch.object(installer, "ensure_plugin_installed", return_value=True):
            failed = installer.ensure_plugins_installed(["plugin1", "plugin2"])
            self.assertEqual(failed, [])

    def test_ensure_plugins_installed_partial_failure(self):
        """Test ensuring plugins when some fail."""
        installer = PluginInstaller(auto_install=True)

        def side_effect(plugin_name):
            # Return False for plugin1 (fails), True for plugin2 (succeeds)
            return plugin_name == "plugin2"

        with patch.object(installer, "ensure_plugin_installed", side_effect=side_effect):
            failed = installer.ensure_plugins_installed(["plugin1", "plugin2"])
            self.assertEqual(failed, ["plugin1"])


class TestTopLevelFunctions(TestCase):
    """Test top-level functions."""

    @patch("acapy_agent.utils.plugin_installer.PluginInstaller")
    def test_install_plugins_from_config(self, mock_installer_class):
        """Test install_plugins_from_config function."""
        mock_installer = MagicMock()
        mock_installer.ensure_plugins_installed.return_value = []
        mock_installer_class.return_value = mock_installer

        result = install_plugins_from_config(
            ["plugin1", "plugin2"], auto_install=True, plugin_version="1.3.2"
        )
        self.assertEqual(result, [])
        mock_installer_class.assert_called_once_with(
            auto_install=True, plugin_version="1.3.2"
        )
        mock_installer.ensure_plugins_installed.assert_called_once_with(
            ["plugin1", "plugin2"]
        )

    @patch("acapy_agent.utils.plugin_installer.PluginInstaller")
    def test_get_plugin_version(self, mock_installer_class):
        """Test get_plugin_version function."""
        mock_installer = MagicMock()
        mock_installer._get_installed_plugin_version.return_value = {
            "package_version": "1.0.0",
            "source_version": "1.3.2",
        }
        mock_installer_class.return_value = mock_installer

        result = get_plugin_version("test_plugin")
        self.assertEqual(result["package_version"], "1.0.0")
        self.assertEqual(result["source_version"], "1.3.2")

    def test_install_plugins_from_config_empty_list(self):
        """Test install_plugins_from_config with empty list."""
        result = install_plugins_from_config([])
        self.assertEqual(result, [])

    def test_list_plugin_versions(self):
        """Test list_plugin_versions function."""
        from ..plugin_installer import list_plugin_versions

        installer = PluginInstaller(auto_install=False)
        with (
            patch.object(
                installer,
                "_get_installed_plugin_version",
                return_value={"package_version": "1.0.0"},
            ),
            patch(
                "acapy_agent.utils.plugin_installer.PluginInstaller",
                return_value=installer,
            ),
        ):
            result = list_plugin_versions(["plugin1", "plugin2"])
            self.assertEqual(len(result), 2)
            self.assertIn("plugin1", result)
            self.assertIn("plugin2", result)

    def test_list_plugin_versions_no_names(self):
        """Test list_plugin_versions with no plugin names."""
        from ..plugin_installer import list_plugin_versions

        result = list_plugin_versions(None)
        self.assertEqual(result, {})
