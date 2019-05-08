from unittest import TestCase

from ..base import BaseSettings, SettingsError
from ..settings import Settings


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

    def test_get_formats(self):
        """Test retrieval with formatting."""
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
