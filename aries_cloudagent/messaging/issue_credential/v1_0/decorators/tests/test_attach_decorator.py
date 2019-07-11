from ..attach_decorator import AttachDecorator

from datetime import datetime
from unittest import TestCase


class TestAttachDecorator(TestCase):
    append_id = 'image-0'
    mime_type = 'image/png'
    filename = 'potato.png'
    byte_count = 123456
    lastmod_time = datetime.now().replace(microsecond=0)
    description = 'To one trained by "Bob," Truth can be found in a potato'
    data_b64 = {'base64': 'c2FtcGxlIGltYWdlIHdpdGggcGFkZGluZw=='}
    data_links = {'links': ['http://site.ca/link.png']}

    def test_init_embedded_b64(self):
        decorator = AttachDecorator(
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_b64

    def test_serialize_load_embedded_b64(self):

        decorator = AttachDecorator(
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_b64

    def test_init_appended_b64(self):
        decorator = AttachDecorator(
            append_id=self.append_id,
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )
        assert decorator.append_id == self.append_id
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_b64

    def test_serialize_load_appended_b64(self):

        decorator = AttachDecorator(
            append_id=self.append_id,
            mime_type=self.mime_type,
            filename=self.filename,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_b64
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.append_id == self.append_id
        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_b64

    def test_init_appended_links(self):
        decorator = AttachDecorator(
            append_id=self.append_id,
            mime_type=self.mime_type,
            filename=self.filename,
            byte_count=self.byte_count,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_links
        )
        assert decorator.append_id == self.append_id
        assert decorator.mime_type == self.mime_type
        assert decorator.filename == self.filename
        assert decorator.byte_count == self.byte_count
        assert decorator.lastmod_time == self.lastmod_time
        assert decorator.description == self.description
        assert decorator.data == self.data_links

    def test_serialize_load_appended_links(self):

        decorator = AttachDecorator(
            append_id=self.append_id,
            mime_type=self.mime_type,
            filename=self.filename,
            byte_count=self.byte_count,
            lastmod_time=self.lastmod_time,
            description=self.description,
            data=self.data_links
        )

        dumped = decorator.serialize()
        loaded = AttachDecorator.deserialize(dumped)

        assert loaded.append_id == self.append_id
        assert loaded.mime_type == self.mime_type
        assert loaded.filename == self.filename
        assert loaded.byte_count == self.byte_count
        assert loaded.lastmod_time == self.lastmod_time
        assert loaded.description == self.description
        assert loaded.data == self.data_links

