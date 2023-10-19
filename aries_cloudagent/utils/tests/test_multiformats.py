import pytest
from ..multiformats import multibase, multicodec


def test_encode_decode():
    value = b"Hello World!"
    encoded = multibase.encode(value, "base58btc")
    assert encoded == "z2NEpo7TZRRrLZSi2U"
    decoded = multibase.decode(encoded)
    assert decoded == value


def test_encode_decode_by_encoding():
    value = b"Hello World!"
    encoded = multibase.encode(value, multibase.Encoding.base58btc)
    assert encoded == "z2NEpo7TZRRrLZSi2U"
    decoded = multibase.decode(encoded)
    assert decoded == value


def test_x_unknown_encoding():
    with pytest.raises(ValueError):
        multibase.encode(b"Hello World!", "fancy-encoding")


def test_x_unknown_character():
    with pytest.raises(ValueError):
        multibase.decode("fHello World!")


def test_x_invalid_encoding():
    with pytest.raises(TypeError):
        multibase.encode(b"Hello World!", 123)


def test_wrap_unwrap():
    value = b"Hello World!"
    wrapped = multicodec.wrap("ed25519-pub", value)
    codec, unwrapped = multicodec.unwrap(wrapped)
    assert codec == multicodec.multicodec("ed25519-pub")
    assert unwrapped == value


def test_wrap_unwrap_custom():
    value = b"Hello World!"
    my_codec = multicodec.Multicodec("my-codec", b"\x00\x01")
    wrapped = multicodec.wrap(my_codec, value)
    codec, unwrapped = multicodec.unwrap(wrapped, my_codec)
    assert codec == my_codec
    assert unwrapped == value


def test_wrap_unwrap_by_codec():
    value = b"Hello World!"
    wrapped = multicodec.wrap(multicodec.multicodec("ed25519-pub"), value)
    codec, unwrapped = multicodec.unwrap(wrapped, multicodec.multicodec("ed25519-pub"))
    assert codec == multicodec.multicodec("ed25519-pub")
    assert unwrapped == value


def test_x_unknown_multicodec():
    with pytest.raises(ValueError):
        multicodec.wrap("fancy-multicodec", b"Hello World!")


def test_x_invalid_multicodec():
    with pytest.raises(TypeError):
        multicodec.wrap(123, b"Hello World!")


def test_x_invalid_multicodec_unwrap():
    with pytest.raises(ValueError):
        multicodec.unwrap(b"Hello World!")
