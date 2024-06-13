"""Base class for performing Verifiable Credential validation using credentialSchemas."""
from typing import Dict, Optional
from aries_cloudagent.vc.ld_proofs.schema_validators.error import VcSchemaValidatorError
from aries_cloudagent.vc.vc_ld.models.credential import VerifiableCredential
import urllib.parse as urllib_parse
import string
import requests
from ....version import __version__



class VcSchemaValidator:
    """Base class for a single Verifiable Credential Schema Instance."""
    def __init__(self, *, vc_schema: Dict) -> None:
        """Initializes the VcSchemaValidator."""
        self._schema_type = self.check_type(vc_schema.get('type'))
        self._schema_id = self.check_id(vc_schema.get('id'))
    
    @property
    def schema_type(self):
        """Getter for schema type."""
        return self._schema_type
    
    @schema_type.setter
    def schema_type(self, value):
        self.schema_type = self.check_type(value)

    def check_type(self, type) -> str:
        """Checks type is valid."""
        if isinstance(type, str) and type is not None:
            return type
        else: 
            raise VcSchemaValidatorError(
                "type must be defined and a string."
                )
        
    @property
    def schema_id(self):
        """Getter for schema id."""
        return self._schema_id
    
    @schema_id.setter
    def schema_id(self, value):
        self.schema_id = self.check_id(value)
    
    def check_id(self, id) -> str:
        """Checks id is valid."""
        if isinstance(id, str) or type is None:
            return id
        else: 
            raise VcSchemaValidatorError(
                "id must be a string."
                )

    def validate(self, vc: VerifiableCredential):
        """Validate a verifiable credential with its provided credentialSchema.

        :param vc: The Verifiable Credential to validate.
        :raises VcSchemaValidatorError: errors for the invalid VC.
        :returns True if valid.
        """
        raise VcSchemaValidatorError(
            f"{self.schema_type} type is not supported for validating."
        )
    
    def download(self, url: str, options: Optional[Dict], **kwargs):
        """Retrieves a schema JSON document from the given URL.

        :param url: the URL of the schema to download
        :param options: 
        :return: the Schema JSON object
        """
        options = options or {}

        try:
            # validate URL
            pieces = urllib_parse.urlparse(url)
            if (
                not all([pieces.scheme, pieces.netloc])
                or pieces.scheme not in ["http", "https"]
                or set(pieces.netloc)
                > set(string.ascii_letters + string.digits + "-.:")
            ):
                raise VcSchemaValidatorError(
                    'URL could not be dereferenced; only "http" and "https" '             
                    "URLs are supported.", 
                    {"url": url})

        except Exception as cause:
            raise VcSchemaValidatorError(cause)
        headers = options.get("headers")
        if headers is None:
            headers = {"Accept": "application/json"}
        headers["User-Agent"] = f"AriesCloudAgent/{__version__}"
        
        response = requests.get(url, headers=headers, **kwargs)
        return response.json()