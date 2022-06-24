import pytest

from unittest import TestCase

from aries_cloudagent.config.plugin_settings import PluginSettings

from ..base import SettingsError
from ..settings import Settings
from ..plugin_settings import PLUGIN_CONFIG_KEY


class TestSettings(TestCase):
    def setUp(self):
        self.test_key = "TEST"
        self.test_value = "VALUE"
        self.test_settings = {self.test_key: self.test_value}
        self.test_instance = Settings(self.test_settings)

    def test_settings_init(self):
        """Test settings initialization."""
        for key in self.test_settings:
            assert key in self.test_instance
            assert self.test_instance[key] == self.test_settings[key]
            assert (
                self.test_instance.get_value(self.test_key) == self.test_settings[key]
            )
        with self.assertRaises(KeyError):
            self.test_instance["MISSING"]
        assert len(self.test_instance) == 1
        assert len(self.test_instance.copy()) == 1

    def test_get_formats(self):
        """Test retrieval with formatting."""
        assert "Settings" in str(self.test_instance)
        with pytest.raises(TypeError):
            self.test_instance[0]  # cover wrong type
        self.test_instance["BOOL"] = "true"
        assert self.test_instance.get_bool("BOOL") is True
        self.test_instance["BOOL"] = "false"
        assert self.test_instance.get_bool("BOOL") is False
        self.test_instance["INT"] = "5"
        assert self.test_instance.get_int("INT") is 5
        assert self.test_instance.get_str("INT") == "5"
        with self.assertRaises(TypeError):
            self.test_instance[None] = 1
        with self.assertRaises(ValueError):
            self.test_instance[""] = 1

    def test_remove(self):
        """Test value removal."""
        del self.test_instance[self.test_key]
        with self.assertRaises(KeyError):
            self.test_instance[self.test_key]
        self.test_instance[self.test_key] = self.test_value
        self.test_instance.clear_value(self.test_key)
        with self.assertRaises(KeyError):
            self.test_instance[self.test_key]

    def test_set_default(self):
        """Test default value."""
        self.test_instance.set_default(self.test_key, "RANDOM")
        assert self.test_instance[self.test_key] == self.test_value
        self.test_instance.set_default("BOOL", "True")
        assert self.test_instance["BOOL"] == "True"

    def test_plugin_setting_retrieval(self):
        plugin_setting_values = {
            "value0": 0,
            "value1": 1,
            "value2": 2,
            "value3": 3,
            "value4": 4,
        }
        self.test_instance[PLUGIN_CONFIG_KEY] = {"my_plugin": plugin_setting_values}

        plugin_settings = self.test_instance.for_plugin("my_plugin")
        assert isinstance(plugin_settings, PluginSettings)
        assert plugin_settings._values == plugin_setting_values
        for key in plugin_setting_values:
            assert key in plugin_settings
            assert plugin_settings[key] == plugin_setting_values[key]
            assert plugin_settings.get_value(key) == plugin_setting_values[key]
        with self.assertRaises(KeyError):
            plugin_settings["MISSING"]
        assert len(plugin_settings) == 5
        assert len(plugin_settings) == 5
