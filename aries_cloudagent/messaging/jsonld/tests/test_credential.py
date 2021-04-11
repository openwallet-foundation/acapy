import json

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .. import credential as test_module

TEST_VERKEY = "5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"


class TestCredential(AsyncTestCase):
    async def test_did_key(self):
        did_key = test_module.did_key(TEST_VERKEY)
        assert did_key.startswith("did:key:z")
        assert did_key == test_module.did_key(did_key)

    async def test_verify_jws_header(self):
        test_module.verify_jws_header(
            json.loads(
                test_module.b64decode(
                    "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19"
                )
            )
        )

        with self.assertRaises(test_module.BadJWSHeaderError):
            test_module.verify_jws_header(
                json.loads(
                    test_module.b64decode(  # {... "b64": True ...}
                        "eyJhbGciOiJFZERTQSIsImI2NCI6dHJ1ZSwiY3JpdCI6WyJiNjQiXX0="
                    )
                )
            )
