"""Base class for performing Verifiable Credential validation using credentialSchemas."""
from abc import ABC, abstractmethod
from typing import Dict
from .error import VcSchemaValidatorError
from ..models.credential import VerifiableCredential
import urllib.parse as urllib_parse
import string
import requests
from ....version import __version__



class VcSchemaValidator(ABC):
    """Base class for a single Verifiable Credential Schema Instance."""
    def __init__(self, vc_schema: Dict) -> None:
        """Initializes the VcSchemaValidator."""
        self.schema_type = vc_schema.get('type')
        self.schema_id = vc_schema.get('id')
    
    @property
    def schema_type(self):
        """Getter for schema type."""
        return self._schema_type
    
    @schema_type.setter
    def schema_type(self, type):
        """Checks type is valid."""
        if isinstance(type, str) and type is not None:
            self._schema_type = type
        else: 
            raise VcSchemaValidatorError(
                "type must be defined and a string."
                )
        
    @property
    def schema_id(self):
        """Getter for schema id."""
        return self._schema_id
    
    @schema_id.setter
    def schema_id(self, id):
        """Checks id is valid."""
        if isinstance(id, str) and type is not None:
            self._schema_id = id
        else: 
            raise VcSchemaValidatorError(
                "id must be a string."
                )

    @abstractmethod
    def validate(self, vc: VerifiableCredential):
        """Validate a verifiable credential with its provided credentialSchema.

        :param vc: The Verifiable Credential to validate.
        :raises VcSchemaValidatorError: errors for the invalid VC.
        :returns True if valid.
        """
    
    def fetch(self, url: str, **kwargs):
        """Retrieves a schema JSON document from the given URL.

        :param url: the URL of the schema to fetch
        :return: the Schema JSON object
        """

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
        
        headers = {"Accept": "application/json"}
        headers["User-Agent"] = f"AriesCloudAgent/{__version__}"

        try:
            response = requests.get(url, headers=headers, **kwargs)
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.ConnectionError as e:
            raise VcSchemaValidatorError("A connection error occurred:", str(e))
        except requests.exceptions.HTTPError as e:
            raise VcSchemaValidatorError("An HTTP error occurred:", str(e))
        except requests.exceptions.Timeout as e:
            raise VcSchemaValidatorError("The request timed out:", str(e))     
        except requests.exceptions.RequestException as e:
            raise VcSchemaValidatorError("An error occurred:", str(e))