import json
import logging

from random import randrange

from api_v2.models.Credential import Credential


logger = logging.getLogger(__name__)


class Restriction(object):
    """
    Class representing a proof request restriction
    """

    def __init__(
        self,
        schema_id: str = None,
        schema_issuer_did: str = None,
        schema_name: str = None,
        schema_version: str = None,
        issuer_did: str = None,
        cred_def_id: str = None,
    ):
        self.schema_id = schema_id
        self.schema_issuer_did = schema_issuer_did
        self.schema_name = schema_name
        self.schema_version = schema_version
        self.issuer_did = issuer_did
        self.cred_def_id = cred_def_id

    @property
    def dict(self):
        _dict = {}
        if self.schema_id:
            _dict["schema_id"] = self.schema_id
        if self.schema_issuer_did:
            _dict["schema_issuer_did"] = self.schema_issuer_did
        if self.schema_name:
            _dict["schema_name"] = self.schema_name
        if self.schema_version:
            _dict["schema_version"] = self.schema_version
        if self.issuer_did:
            _dict["issuer_did"] = self.issuer_did
        if self.cred_def_id:
            _dict["cred_def_id"] = self.cred_def_id
        return _dict


class ProofRequest(object):
    """
    Class to manage creation of proof requests
    """

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version

        self.nonce = ""
        while len(self.nonce) < 16:
            self.nonce += str(randrange(10))

        self.requested_attributes = []

    @property
    def dict(self):
        _dict = {}
        _dict["name"] = self.name
        _dict["version"] = self.version
        _dict["nonce"] = self.nonce
        _dict["requested_attributes"] = {}
        _dict["requested_predicates"] = {}
        for requested_attribute in self.requested_attributes:
            _dict["requested_attributes"][
                requested_attribute["name"]
            ] = requested_attribute
        return _dict

    @property
    def json(self):
        return json.dumps(self.dict)

    def add_requested_attribute(self, name: str, *args: tuple) -> None:
        """Add requested attribute to proof request

        Arguments:
            name {str} -- Name of claim
            *restrictions {Restriction} -- Arbitrary number of restrictions

        Returns:
            None
        """
        requested_attribute = {"name": name, "restrictions": []}
        for restriction in args:
            requested_attribute["restrictions"].append(restriction.dict)

        self.requested_attributes.append(requested_attribute)

    def add_requested_predicate(self) -> None:
        raise NotImplemented

    def build_from_credential(self, credential: Credential) -> None:
        claims = credential.claims.all()
        credential_type = credential.credential_type
        schema = credential_type.schema
        visible_fields = credential_type.visible_fields
        visible_fields = visible_fields.split(",") if visible_fields else None

        restrictions = []
        if credential.credential_def_id:
            restrictions.append(Restriction(
                cred_def_id=credential.credential_def_id,
            ))
        else:
            schema = credential_type.schema
            restrictions.append(Restriction(
                schema_name=schema.name, schema_version=schema.version,
            ))

        for claim in claims:
            if visible_fields is None or claim.name in visible_fields:
                self.add_requested_attribute(claim.name, *restrictions)
