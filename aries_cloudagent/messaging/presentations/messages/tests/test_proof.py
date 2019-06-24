# from ..proof import Proof
# from ....message_types import MessageTypes
#
# from unittest import mock, TestCase
#
#
# class TestProof(TestCase):
#     proof_json = "proof_json"
#     request_nonce = "request_nonce"
#
#     def test_init(self):
#         proof = Proof(self.proof_json, self.request_nonce)
#         assert proof.proof_json == self.proof_json
#         assert proof.request_nonce == self.request_nonce
#
#     def test_type(self):
#         proof = Proof(self.proof_json, self.request_nonce)
#
#         assert proof._type == MessageTypes.PROOF.value
#
#     @mock.patch("aries_cloudagent.messaging.proofs.messages.proof.ProofSchema.load")
#     def test_deserialize(self, proof_schema_load):
#         obj = {"obj": "obj"}
#
#         proof = Proof.deserialize(obj)
#         proof_schema_load.assert_called_once_with(obj)
#
#         assert proof is proof_schema_load.return_value
#
#     @mock.patch("aries_cloudagent.messaging.proofs.messages.proof.ProofSchema.dump")
#     def test_serialize(self, proof_schema_dump):
#         proof = Proof(self.proof_json, self.request_nonce)
#
#         proof_dict = proof.serialize()
#         proof_schema_dump.assert_called_once_with(proof)
#
#         assert proof_dict is proof_schema_dump.return_value
#
#
# class TestProofSchema(TestCase):
#     proof = Proof("proof_json", "request_nonce")
#
#     def test_make_model(self):
#         data = self.proof.serialize()
#         model_instance = Proof.deserialize(data)
#         assert isinstance(model_instance, Proof)
