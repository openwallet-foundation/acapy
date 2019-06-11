import base64
import hashlib
import json as _json
import logging
import re
import time
from collections import namedtuple
from datetime import datetime
from importlib import import_module

from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from icat_hooks.models.HookableCredential import HookableCredential

from api_v2.models.Address import Address
from api_v2.models.Attribute import Attribute
from api_v2.models.Claim import Claim
from api_v2.models.Credential import Credential as CredentialModel
from api_v2.models.CredentialSet import CredentialSet
from api_v2.models.CredentialType import CredentialType
from api_v2.models.Issuer import Issuer
from api_v2.models.Name import Name
from api_v2.models.Schema import Schema
from api_v2.models.Topic import Topic
from api_v2.models.TopicRelationship import TopicRelationship

LOGGER = logging.getLogger(__name__)

PROCESSOR_FUNCTION_BASE_PATH = "api_v2.processor"

SUPPORTED_MODELS_MAPPING = {
    "attribute": Attribute,
    "address": Address,
    "category": Attribute,
    "name": Name,
}

SchemaKey = namedtuple("SchemaKey", "origin_did name version")


def schema_key(s_id: str) -> SchemaKey:
    """
    Return schema key (namedtuple) convenience for schema identifier components.

    :param s_id: schema identifier
    :return: schema key (namedtuple) object
    """

    s_key = s_id.split(":")
    s_key.pop(1)  # take out indy-sdk schema marker: 2 marks indy-sdk schema id

    return SchemaKey(*s_key)


class CredentialException(Exception):
    pass


class Credential(object):
    """A python-idiomatic representation of an indy credential

    Claim values are made available as class members.

    for example:

    ```json
    "postal_code": {
        "raw": "N2L 6P3",
        "encoded": "1062703188233012330691500488799027"
    }
    ```

    becomes:

    ```python
    self.postal_code = "N2L 6P3"
    ```

    on the class object.

    Arguments:
        credential_data {object} -- Valid credential data as sent by an issuer
    """

    def __init__(
        self,
        credential_data: object,
        request_metadata: dict = None,
        wallet_id: str = None,
    ) -> None:
        self._raw = credential_data
        self._schema_id = credential_data["schema_id"]
        self._cred_def_id = credential_data["cred_def_id"]
        self._rev_reg_id = credential_data["rev_reg_id"]
        self._signature = credential_data["signature"]
        self._signature_correctness_proof = credential_data[
            "signature_correctness_proof"
        ]
        self._req_metadata = request_metadata
        self._rev_reg = credential_data["rev_reg"]
        self._wallet_id = wallet_id
        self._witness = credential_data["witness"]

        self._claim_attributes = []

        # Parse claim attributes into array
        # Values are available as class attributes
        claim_data = credential_data["values"]
        for claim_attribute in claim_data:
            self._claim_attributes.append(claim_attribute)

    def __getattr__(self, name: str):
        """Make claim values accessible on class instance"""
        try:
            if isinstance(self.raw["values"][name], dict):
                claim_value = self.raw["values"][name]["raw"]
            else:
                claim_value = self.raw["values"][name]
            return claim_value
        except KeyError:
            raise AttributeError(
                "'Credential' object has no attribute '{}'".format(name)
            )

    @property
    def raw(self) -> dict:
        """Accessor for raw credential data

        Returns:
            dict -- Python dict representation of raw credential data
        """
        return self._raw

    @property
    def json(self) -> str:
        """Accessor for json credential data

        Returns:
            str -- JSON representation of raw credential data
        """
        return _json.dumps(self._raw)

    @property
    def schema_origin_did(self) -> str:
        """Accessor for schema origin did

        Returns:
            str -- origin did
        """
        return schema_key(self._schema_id).origin_did

    @property
    def origin_did(self) -> str:
        """Accessor for the cred def origin did

        Returns:
            str -- origin did
        """
        if self._cred_def_id:
            key = self._cred_def_id.split(":")
            return key[0]
        return None

    @property
    def schema_name(self) -> str:
        """Accessor for schema name

        Returns:
            str -- schema name
        """
        return schema_key(self._schema_id).name

    @property
    def schema_version(self) -> str:
        """Accessor for schema version

        Returns:
            str -- schema version
        """
        return schema_key(self._schema_id).version

    @property
    def claim_attributes(self) -> list:
        """Accessor for claim attributes

        Returns:
            list -- claim attributes
        """
        return self._claim_attributes

    @property
    def cred_def_id(self) -> str:
        """Accessor for credential definition ID

        Returns:
            str -- the cred def ID
        """
        return self._cred_def_id

    @property
    def request_metadata(self) -> dict:
        return self._request_metadata

    @property
    def wallet_id(self) -> str:
        """Accessor for credential wallet ID, after storage

        Returns:
            str -- the wallet ID of the credential
        """
        return self._wallet_id

    @wallet_id.setter
    def wallet_id(self, val: str):
        self._wallet_id = val


class CredentialClaims:
    def __init__(self, cred: CredentialModel):
        self._cred = cred
        self._claims = {}
        self._load_claims()

    def _load_claims(self):
        claims = getattr(self._cred, "_claims_cache", None)
        if claims is None:
            claims = {}
            for claim in self._cred.claims.all():
                claims[claim.name] = claim.value
            setattr(self._cred, "_claims_cache", claims)
        self._claims = claims

    def __getattr__(self, name: str):
        """Make claim values accessible on class instance"""
        try:
            return self._claims[name]
        except KeyError:
            raise AttributeError(
                "'Credential' object has no attribute '{}'".format(name)
            )


class CredentialManager(object):
    """
    Handles processing of incoming credentials. Populates application
    database based on rules provided by issuer are registration.
    """

    def __init__(self) -> None:
        self._cred_type_cache = {}

    @classmethod
    def get_claims(cls, credential):
        if isinstance(credential, Credential):
            return credential
        elif isinstance(credential, CredentialModel):
            return CredentialClaims(credential)

    @classmethod
    def process_mapping(cls, rules, credential):
        """
        Takes our mapping rules and returns a value from credential
        """
        if not rules:
            return None

        # Get required values from config
        try:
            _input = rules["input"]
            _from = rules["from"]
        except KeyError:
            raise CredentialException(
                "Every mapping must specify 'input' and 'from' values."
            )

        # Processor is optional
        processor = rules.get("processor")

        claims = cls.get_claims(credential)

        # Get model field value from string literal or claim value
        if _from == "value":
            mapped_value = _input
        elif _from == "claim":
            try:
                mapped_value = getattr(claims, _input)
            except AttributeError:
                raise CredentialException(
                    "Credential does not contain the configured claim '{}'".format(
                        _input
                    )
                )
        else:
            raise CredentialException(
                "Supported field from values are 'value' and 'claim'"
                + " but received '{}'".format(_from)
            )

        # If we have a processor config, build pipeline of functions
        # and run field value through pipeline
        if processor is not None:
            pipeline = []
            # Construct pipeline by dot notation. Last token is the
            # function name and all preceeding dots denote path of
            # module starting from `PROCESSOR_FUNCTION_BASE_PATH``
            for function_path_with_name in processor:
                function_path, function_name = function_path_with_name.rsplit(".", 1)

                # Does the file exist?
                try:
                    function_module = import_module(
                        "{}.{}".format(PROCESSOR_FUNCTION_BASE_PATH, function_path)
                    )
                except ModuleNotFoundError:
                    raise CredentialException(
                        "No processor module named '{}'".format(function_path)
                    )

                # Does the function exist?
                try:
                    function = getattr(function_module, function_name)
                except AttributeError:
                    raise CredentialException(
                        "Module '{}' has no function '{}'.".format(
                            function_path, function_name
                        )
                    )

                # Build up a list of functions to call
                pipeline.append(function)

            # We want to run the pipeline in logical order
            pipeline.reverse()

            # Run pipeline
            while len(pipeline) > 0:
                function = pipeline.pop()
                mapped_value = function(mapped_value)

        return mapped_value

    def get_credential_type(self, credential: (Credential, CredentialModel)):
        """
        Fetch the credential type for the incoming credential
        """
        LOGGER.debug(">>> get credential context")
        start_time = time.perf_counter()
        result = None
        type_id = getattr(credential, "credential_type_id", None)
        if type_id:
            result = self._cred_type_cache.get(type_id)
            if not result:
                result = CredentialType.objects.get(pk=type_id)
                self._cred_type_cache[type_id] = result
        elif isinstance(credential, Credential):
            cache_key = (credential.cred_def_id,)
            result = self._cred_type_cache.get(cache_key)
            if not result:
                try:
                    issuer = Issuer.objects.get(did=credential.origin_did)
                    schema = Schema.objects.get(
                        origin_did=credential.schema_origin_did,
                        name=credential.schema_name,
                        version=credential.schema_version,
                    )
                except Issuer.DoesNotExist:
                    raise CredentialException(
                        "Issuer with did '{}' does not exist.".format(
                            credential.origin_did
                        )
                    )
                except Schema.DoesNotExist:
                    raise CredentialException(
                        "Schema with origin_did"
                        + " '{}', name '{}', and version '{}' ".format(
                            credential.schema_origin_did,
                            credential.schema_name,
                            credential.schema_version,
                        )
                        + " does not exist."
                    )

                result = CredentialType.objects.get(schema=schema, issuer=issuer)
                self._cred_type_cache[cache_key] = result
        LOGGER.debug(
            "<<< get credential context: " + str(time.perf_counter() - start_time)
        )
        if not result:
            raise CredentialException("Credential type not found")
        return result

    def process(
        self, credential: Credential, check_from_did: str = None
    ) -> CredentialModel:
        """
        Processes incoming credential data and returns related Topic

        Returns:
            Credential -- the processed database credential
        """
        if check_from_did and check_from_did != credential.origin_did:
            raise CredentialException(
                "Credential origin DID '{}' does not match request origin DID '{}'".format(
                    credential.origin_did, check_from_did
                )
            )
        credential_type = self.get_credential_type(credential)

        return self.populate_application_database(credential_type, credential)

    def reprocess(self, credential: CredentialModel):
        """
        Reprocesses an existing credential in order to update the related search models
        """
        credential_type = self.get_credential_type(credential)
        processor_config = credential_type.processor_config

        with transaction.atomic():
            if not credential.credential_set:
                cardinality = self.credential_cardinality(credential, processor_config)
                self.update_credential_set(credential_type, credential, cardinality)
            self.remove_search_models(credential)
            self.create_search_models(credential, processor_config)

    @classmethod
    def find_or_create_topic(cls, topic_spec: dict, retry=True):
        """
        Create a Topic, allowing for other threads which may have created it first
        """
        try:
            return (Topic.objects.get(**topic_spec), False)
        except Topic.DoesNotExist:
            try:
                return (Topic.objects.create(**topic_spec), True)
            except ValidationError:
                if not retry:
                    raise CredentialException(
                        "Django validation error while creating topic"
                    )
            except IntegrityError:
                if not retry:
                    raise CredentialException("Database error while creating topic")
        return cls.find_or_create_topic(topic_spec, retry=False)

    @classmethod
    def resolve_credential_topics(
        cls, credential, processor_config
    ) -> (Topic, Topic, bool, bool):
        """
        Resolve the related topic(s) for a credential based on the processor config
        """
        topic_defs = processor_config["topic"]
        # We accept object or array for topic def
        if type(topic_defs) is dict:
            topic_defs = [topic_defs]

        topic_created = False
        related_topic_created = False
        result = (None, None, topic_created, related_topic_created)

        # Issuer can register multiple topic selectors to fall back on
        # We use the first valid topic and related parent if applicable
        for topic_def in topic_defs:
            related_topic = None
            topic = None

            related_topic_name = cls.process_mapping(
                topic_def.get("related_name"), credential
            )
            related_topic_source_id = cls.process_mapping(
                topic_def.get("related_source_id"), credential
            )
            related_topic_type = cls.process_mapping(
                topic_def.get("related_type"), credential
            )

            topic_name = cls.process_mapping(topic_def.get("name"), credential)
            topic_source_id = cls.process_mapping(
                topic_def.get("source_id"), credential
            )
            topic_type = cls.process_mapping(topic_def.get("type"), credential)

            # Get parent topic if possible
            if related_topic_name:
                try:
                    related_topic = Topic.objects.get(
                        credentials__names__text=related_topic_name
                    )
                except Topic.DoesNotExist:
                    continue
            elif related_topic_source_id and related_topic_type:
                try:
                    related_topic = Topic.objects.get(
                        source_id=related_topic_source_id, type=related_topic_type
                    )
                except Topic.DoesNotExist:
                    pass

            # Current topic if possible
            if topic_name:
                try:
                    topic = Topic.objects.get(credentials__names__text=topic_name)
                except Topic.DoesNotExist:
                    continue
            elif topic_source_id and topic_type:
                # Create a new topic if our query comes up empty
                topic_spec = {"source_id": topic_source_id, "type": topic_type}

                # need to return the fact that the new Topic was created
                (topic, topic_created) = cls.find_or_create_topic(topic_spec)

            # We stick with the first topic that we resolve
            if topic:
                if not related_topic and related_topic_source_id and related_topic_type:
                    topic_spec = {
                        "source_id": related_topic_source_id,
                        "type": related_topic_type,
                    }
                    (related_topic, related_topic_created) = cls.find_or_create_topic(
                        topic_spec
                    )
                result = (topic, related_topic, topic_created, related_topic_created)
        return result

    @classmethod
    def credential_cardinality(cls, credential, processor_config):
        """
        Extract the credential cardinality values and hash
        """
        fields = processor_config.get("cardinality_fields") or []
        values = {}
        if fields:
            claims = cls.get_claims(credential)
            for field in fields:
                try:
                    values[field] = getattr(claims, field)
                except AttributeError:
                    raise CredentialException(
                        "Issuer configuration specifies field '{}' in cardinality_fields "
                        "value does not exist in credential. Values are: {}".format(
                            field, ", ".join(list(credential.claim_attributes))
                        )
                    )
        if values:
            hash_fields = ["{}::{}".format(k, values[k]) for k in values]
            hash = base64.b64encode(
                hashlib.sha256(",".join(hash_fields).encode("utf-8")).digest()
            )
            return {"values": values, "hash": hash}
        return None

    @classmethod
    def process_config_date(cls, config, credential, field_name):
        date_value = cls.process_mapping(config.get(field_name), credential)
        date_result = None
        if date_value:
            try:
                # could be seconds since epoch
                date_result = datetime.utcfromtimestamp(int(date_value))
            except ValueError:
                # Django method to parse a date string. Must be in ISO8601 format
                try:
                    date_result = parse_datetime(date_value)
                    if not date_result:
                        date_result = parse_date(date_value)
                        if not date_result:
                            raise ValueError()
                        date_result = datetime.combine(date_result, datetime.min.time())
                        date_result = timezone.make_aware(date_result)
                except re.error:
                    raise CredentialException(
                        "Error parsing {}: {}".format(field_name, date_value)
                    )
                except ValueError:
                    raise CredentialException(
                        "Credential {} is invalid: {}".format(field_name, date_value)
                    )
            if not date_result.tzinfo:
                # interpret as UTC
                date_result = date_result.replace(tzinfo=timezone.utc)
            else:
                # convert to UTC
                date_result = date_result.astimezone(timezone.utc)
        return date_result

    @classmethod
    def process_credential_properties(cls, credential, processor_config) -> dict:
        """
        Generate a dictionary of additional credential properties from the processor config
        """
        config = processor_config.get("credential")
        args = {}
        if config:
            effective_date = cls.process_config_date(
                config, credential, "effective_date"
            )
            if effective_date:
                args["effective_date"] = effective_date

            revoked_date = cls.process_config_date(config, credential, "revoked_date")
            if revoked_date:
                if revoked_date > datetime.utcnow().replace(tzinfo=timezone.utc):
                    raise CredentialException(
                        "Credential revoked_date must be in the past, not: {}".format(
                            revoked_date
                        )
                    )
                args["revoked_date"] = revoked_date
                args["revoked"] = True

            inactive = cls.process_mapping(config.get("inactive"), credential)
            if inactive:
                args["inactive"] = bool(inactive)
        return args

    @classmethod
    def create_search_models(
        cls,
        credential: CredentialModel,
        processor_config,
        search_model_map=None,
        save=True,
    ):
        """
        Create search model instances using mapping from issuer config

        Returns: a list of the unsaved model instances
        """
        mapping = processor_config.get("mapping") or []
        if search_model_map is None:
            search_model_map = SUPPORTED_MODELS_MAPPING
        result = []

        for model_mapper in mapping:
            model_name = model_mapper["model"]

            try:
                Model = search_model_map[model_name]
                model = Model()
            except KeyError:
                raise CredentialException(
                    "Unsupported model type '{}'".format(model_name)
                )

            for field, field_mapper in model_mapper["fields"].items():
                setattr(model, field, cls.process_mapping(field_mapper, credential))
            if model_name == "category":
                model.format = "category"

            # skip blank in names and attributes
            if model_name == "name" and (model.text is None or model.text is ""):
                continue
            if (model_name == "category" or model_name == "attribute") and (
                not model.type or model.value is None or model.value is ""
            ):
                continue

            model.credential = credential
            if save:
                model.save()
            result.append(model)
        return result

    @classmethod
    def remove_search_models(
        cls, credential: CredentialModel, search_model_map=None, raw_delete=True
    ):
        """
        Delete any existing search model instances
        """
        if search_model_map is None:
            search_model_map = SUPPORTED_MODELS_MAPPING
        for model_key, model_cls in search_model_map.items():
            if model_key == "category":
                continue
            rows = model_cls.objects.filter(credential=credential)
            if raw_delete:
                # Don't trigger search reindex (yet)
                rows._raw_delete(using=DEFAULT_DB_ALIAS)
            else:
                rows.delete()

    @classmethod
    def update_credential_set(
        cls,
        credential_type: CredentialType,
        credential: CredentialModel,
        cardinality=None,
    ) -> CredentialSet:
        if credential.credential_set:
            return credential.credential_set
        existing_set_query = {
            "cardinality_hash": cardinality["hash"] if cardinality else None,
            "credential_type": credential_type,
            "topic": credential.topic,
        }
        try:
            cred_set = CredentialSet.objects.get(**existing_set_query)
            latest_cred = credential

            for prev_cred in cred_set.credentials.filter(revoked=False).order_by(
                "effective_date"
            ):
                if prev_cred.effective_date <= credential.effective_date:
                    prev_cred.latest = False
                    prev_cred.revoked = True
                    prev_cred.revoked_by = credential
                    prev_cred.revoked_date = credential.effective_date
                    prev_cred.save()
                else:
                    latest_cred = prev_cred
                    if not credential.revoked:
                        credential.revoked = True
                        credential.revoked_by = prev_cred
                        credential.revoked_date = prev_cred.effective_date

            cred_set.latest_credential = latest_cred
            cred_set.first_effective_date = (
                credential.effective_date
                if cred_set.first_effective_date is None
                else min(cred_set.first_effective_date, credential.effective_date)
            )

            if latest_cred.revoked:
                cred_set.last_effective_date = (
                    latest_cred.revoked_date
                    if cred_set.last_effective_date is None
                    else max(cred_set.last_effective_date, latest_cred.revoked_date)
                )
            else:
                cred_set.last_effective_date = None

            cred_set.save()
            credential.credential_set = cred_set
            credential.latest = latest_cred == credential
            credential.save()

            if latest_cred != credential and not latest_cred.latest:
                latest_cred.latest = True
                latest_cred.save()

        except CredentialSet.DoesNotExist:
            updates = existing_set_query.copy()
            updates["first_effective_date"] = credential.effective_date
            updates["last_effective_date"] = (
                credential.revoked_date if credential.revoked else None
            )
            updates["latest_credential"] = credential
            cred_set = CredentialSet.objects.create(**updates)
            credential.credential_set = cred_set
            credential.latest = True
            credential.save()
        return cred_set

    @classmethod
    def populate_application_database(
        cls, credential_type: CredentialType, credential: Credential
    ) -> CredentialModel:
        LOGGER.warn(">>> store cred in local database")
        start_time = time.perf_counter()
        processor_config = credential_type.processor_config

        (
            topic,
            related_topic,
            topic_created,
            related_topic_created,
        ) = cls.resolve_credential_topics(credential, processor_config)

        # If we couldn't resolve _any_ topics from the configuration,
        # we can't continue
        if not topic:
            raise CredentialException(
                "Issuer registration 'topic' must specify at least one valid topic name "
                "OR topic type and topic source_id"
            )

        with transaction.atomic():
            # Acquire a lock on the topic to block competing credentials
            # This lock is released when the transaction ends
            Topic.objects.select_for_update().get(pk=topic.id)

            cardinality = cls.credential_cardinality(credential, processor_config)

            # We always create a new credential model to represent the current credential
            # The issuer may specify an effective date from a claim. Otherwise, defaults to now.

            credential_args = {
                "cardinality_hash": cardinality["hash"] if cardinality else None,
                "credential_def_id": credential.cred_def_id,
                "credential_type": credential_type,
                "wallet_id": credential.wallet_id,
            }
            credential_args.update(
                cls.process_credential_properties(credential, processor_config)
            )

            db_credential = topic.credentials.create(**credential_args)

            # Create and associate claims for this credential
            cred_claims = {}
            for claim_attribute in credential.claim_attributes:
                claim_value = getattr(credential, claim_attribute)
                cred_claims[claim_attribute] = claim_value
                Claim.objects.create(
                    credential=db_credential, name=claim_attribute, value=claim_value
                )

            # Create topic relationship if needed
            if related_topic is not None:
                try:
                    TopicRelationship.objects.create(
                        credential=db_credential,
                        topic=topic,
                        related_topic=related_topic,
                    )
                except IntegrityError:
                    raise CredentialException(
                        "Relationship between topics '{}' and '{}' already exist.".format(
                            topic.id, related_topic.id
                        )
                    )

            # Assign to credential set
            cls.update_credential_set(credential_type, db_credential, cardinality)

            # Save search models
            cls.create_search_models(db_credential, processor_config)

            # Update last issue date for credential type
            credential_type.last_issue_date = datetime.now(timezone.utc)
            credential_type.save()

            # add to the set of "hookable credentials"
            # TODO make this a configurable step of the process
            if topic_created:
                topic_status = "New"
            else:
                topic_status = "Stream"
            hookable_cred_data = {
                "cred_def_id": credential.cred_def_id,
                "schema_name": credential.schema_name,
                "attributes": cred_claims,
            }
            hookable_cred = HookableCredential(
                topic_status=topic_status,
                corp_num=topic.source_id,
                credential_type=credential_type.schema.name,
                credential_json=hookable_cred_data,
            )
            hookable_cred.save()

        LOGGER.warn(
            "<<< store cred in local database: " + str(time.perf_counter() - start_time)
        )

        return db_credential
