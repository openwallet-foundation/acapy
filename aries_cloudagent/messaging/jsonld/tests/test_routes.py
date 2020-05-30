from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.wallet.basic import BasicWallet
from ....storage.base import BaseStorage
from .. import routes as test_module


# TODO: Add tests
class TestJSONLDRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)

        self.storage = async_mock.create_autospec(BaseStorage)

        self.context.injector.bind_instance(BaseStorage, self.storage)

        self.wallet = self.wallet = BasicWallet()
        self.context.injector.bind_instance(BaseWallet, self.wallet)

        self.app = {
            "request_context": self.context,
        }

    async def test_verify_credential(self):
        mock_request = async_mock.MagicMock(
            app=self.app,
            json=async_mock.CoroutineMock(
                return_value={  # posted json
                    "verkey": "5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF",  # pulled from the did:key in example
                    "doc": {
                      "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1"
                      ],
                      "id": "http://example.gov/credentials/3732",
                      "type": ["VerifiableCredential", "UniversityDegreeCredential"],
                      "issuer": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                      "issuanceDate": "2020-03-10T04:24:12.164Z",
                      "credentialSubject": {
                        "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                        "degree": {
                          "type": "BachelorDegree",
                          "name": "Bachelor of Science and Arts"
                        }
                      },
                      "proof": {
                        "type": "Ed25519Signature2018",
                        "created": "2020-04-10T21:35:35Z",
                        "verificationMethod": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                        "proofPurpose": "assertionMethod",
                        "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..l9d0YHjcFAH2H4dB9xlWFZQLUpixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2LffegtYESTCJEoGVXLqWAA"
                      }
                    }
                }
            ),
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.verify(
                mock_request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with( #expected response
                {"valid": True}
            )

    async def test_sign_credential(self):

        wallet: BaseWallet = await self.app['request_context'].inject(BaseWallet)

        did_info = await wallet.create_local_did()

        mock_request = async_mock.MagicMock(
            app=self.app,
            json=async_mock.CoroutineMock(
                return_value={  # posted json
                    "verkey": did_info.verkey,
                    "doc": {
                        "credential": {
                          "@context": [
                            "https://www.w3.org/2018/credentials/v1",
                            "https://www.w3.org/2018/credentials/examples/v1"
                          ],
                          "id": "http://example.gov/credentials/3732",
                          "type": ["VerifiableCredential", "UniversityDegreeCredential"],
                          "issuer": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                          "issuanceDate": "2020-03-10T04:24:12.164Z",
                          "credentialSubject": {
                            "id": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                            "degree": {
                              "type": "BachelorDegree",
                              "name": "Bachelor of Science and Arts"
                            }
                          }
                        },
                      "options": {
                        "type": "Ed25519Signature2018",
                        "created": "2020-04-10T21:35:35Z",
                        "verificationMethod": "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd",
                        "proofPurpose": "assertionMethod",
                      }
                    }
                }
            ),
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.sign(
                mock_request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once()
            assert 'signed_doc' in mock_response.call_args[0][0]
            assert 'error' not in mock_response.call_args[0][0]
