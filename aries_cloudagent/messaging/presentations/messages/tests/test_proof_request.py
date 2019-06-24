# from ..proof_request import ProofRequest
# from ....message_types import MessageTypes
#
# from unittest import mock, TestCase
#
#
# class TestProofRequest(TestCase):
#
#     proof_request_json = "proof_request_json"
#
#     def test_init(self):
#         proof_request = ProofRequest(self.proof_request_json)
#         assert proof_request.proof_request_json == self.proof_request_json
#
#     def test_type(self):
#         proof_request = ProofRequest(self.proof_request_json)
#
#         assert proof_request._type == MessageTypes.PROOF_REQUEST.value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.proofs.messages."
#         + "proof_request.ProofRequestSchema.load"
#     )
#     def test_deserialize(self, proof_request_schema_load):
#         obj = {"obj": "obj"}
#
#         proof_request = ProofRequest.deserialize(obj)
#         proof_request_schema_load.assert_called_once_with(obj)
#
#         assert proof_request is proof_request_schema_load.return_value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.proofs.messages."
#         + "proof_request.ProofRequestSchema.dump"
#     )
#     def test_serialize(self, proof_request_schema_dump):
#         proof_request = ProofRequest(self.proof_request_json)
#
#         proof_request_dict = proof_request.serialize()
#         proof_request_schema_dump.assert_called_once_with(proof_request)
#
#         assert proof_request_dict is proof_request_schema_dump.return_value
#
#
# class TestProofRequestSchema(TestCase):
#     proof_request = ProofRequest("proof_request_json")
#
#     def test_make_model(self):
#         data = self.proof_request.serialize()
#         model_instance = ProofRequest.deserialize(data)
#         assert isinstance(model_instance, ProofRequest)
