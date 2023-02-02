from ..localization_decorator import LocalizationDecorator

from unittest import TestCase


class TestThreadDecorator(TestCase):
    LOCALE = "en-ca"
    LOCALIZABLE = ["a", "b"]
    CATALOGS = ["http://192.168.56.111/my-project/catalog.json"]

    def test_init(self):
        decorator = LocalizationDecorator()
        assert decorator.locale is None
        assert decorator.localizable == []
        assert decorator.catalogs == []

        decorator = LocalizationDecorator(
            locale=TestThreadDecorator.LOCALE,
            localizable=TestThreadDecorator.LOCALIZABLE,
            catalogs=TestThreadDecorator.CATALOGS,
        )
        assert decorator.locale == TestThreadDecorator.LOCALE
        assert decorator.localizable == TestThreadDecorator.LOCALIZABLE
        assert decorator.catalogs == TestThreadDecorator.CATALOGS

    def test_serialize_load(self):
        decorator = LocalizationDecorator(
            locale=TestThreadDecorator.LOCALE,
            localizable=TestThreadDecorator.LOCALIZABLE,
            catalogs=TestThreadDecorator.CATALOGS,
        )

        dumped = decorator.serialize()
        loaded = LocalizationDecorator.deserialize(dumped)

        assert loaded.locale == self.LOCALE
        assert loaded.localizable == self.LOCALIZABLE
        assert loaded.catalogs == self.CATALOGS
