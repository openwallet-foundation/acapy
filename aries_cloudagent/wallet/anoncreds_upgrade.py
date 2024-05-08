"""Functions for upgrading records to anoncreds."""

import asyncio
import json
import logging
from typing import Optional

from anoncreds import (
    CredentialDefinition,
    CredentialDefinitionPrivate,
    KeyCorrectnessProof,
    RevocationRegistryDefinitionPrivate,
    Schema,
)
from aries_askar import AskarError
from indy_credx import LinkSecret

from ..anoncreds.issuer import (
    CATEGORY_CRED_DEF,
    CATEGORY_CRED_DEF_KEY_PROOF,
    CATEGORY_CRED_DEF_PRIVATE,
    CATEGORY_SCHEMA,
)
from ..anoncreds.models.anoncreds_cred_def import CredDef, CredDefState
from ..anoncreds.models.anoncreds_revocation import (
    RevList,
    RevListState,
    RevRegDef,
    RevRegDefState,
    RevRegDefValue,
)
from ..anoncreds.models.anoncreds_schema import SchemaState
from ..anoncreds.revocation import (
    CATEGORY_REV_LIST,
    CATEGORY_REV_REG_DEF,
    CATEGORY_REV_REG_DEF_PRIVATE,
)
from ..cache.base import BaseCache
from ..core.profile import Profile
from ..indy.credx.holder import CATEGORY_LINK_SECRET, IndyCredxHolder
from ..ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    GET_SCHEMA,
    IndyLedgerRequestsExecutor,
)
from ..messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ..messaging.schemas.util import SCHEMA_SENT_RECORD_TYPE
from ..multitenant.base import BaseMultitenantManager
from ..revocation.models.issuer_cred_rev_record import IssuerCredRevRecord
from ..revocation.models.issuer_rev_reg_record import IssuerRevRegRecord
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..storage.type import (
    RECORD_TYPE_ACAPY_STORAGE_TYPE,
    RECORD_TYPE_ACAPY_UPGRADING,
    STORAGE_TYPE_VALUE_ANONCREDS,
)
from .singletons import IsAnoncredsSingleton, UpgradeInProgressSingleton

LOGGER = logging.getLogger(__name__)

UPGRADING_RECORD_IN_PROGRESS = "anoncreds_in_progress"
UPGRADING_RECORD_FINISHED = "anoncreds_finished"

# Number of times to retry upgrading records
max_retries = 5


class SchemaUpgradeObj:
    """Schema upgrade object."""

    def __init__(
        self,
        schema_id: str,
        schema: Schema,
        name: str,
        version: str,
        issuer_id: str,
        old_record_id: str,
    ):
        """Initialize schema upgrade object."""
        self.schema_id = schema_id
        self.schema = schema
        self.name = name
        self.version = version
        self.issuer_id = issuer_id
        self.old_record_id = old_record_id


class CredDefUpgradeObj:
    """Cred def upgrade object."""

    def __init__(
        self,
        cred_def_id: str,
        cred_def: CredentialDefinition,
        cred_def_private: CredentialDefinitionPrivate,
        key_proof: KeyCorrectnessProof,
        revocation: Optional[bool] = None,
        askar_cred_def: Optional[any] = None,
        max_cred_num: Optional[int] = None,
    ):
        """Initialize cred def upgrade object."""
        self.cred_def_id = cred_def_id
        self.cred_def = cred_def
        self.cred_def_private = cred_def_private
        self.key_proof = key_proof
        self.revocation = revocation
        self.askar_cred_def = askar_cred_def
        self.max_cred_num = max_cred_num


class RevRegDefUpgradeObj:
    """Rev reg def upgrade object."""

    def __init__(
        self,
        rev_reg_def_id: str,
        rev_reg_def: RevRegDef,
        rev_reg_def_private: RevocationRegistryDefinitionPrivate,
        active: bool = False,
    ):
        """Initialize rev reg def upgrade object."""
        self.rev_reg_def_id = rev_reg_def_id
        self.rev_reg_def = rev_reg_def
        self.rev_reg_def_private = rev_reg_def_private
        self.active = active


class RevListUpgradeObj:
    """Rev entry upgrade object."""

    def __init__(
        self,
        rev_list: RevList,
        pending: list,
        rev_reg_def_id: str,
        cred_rev_records: list,
    ):
        """Initialize rev entry upgrade object."""
        self.rev_list = rev_list
        self.pending = pending
        self.rev_reg_def_id = rev_reg_def_id
        self.cred_rev_records = cred_rev_records


async def get_schema_upgrade_object(
    profile: Profile, schema_id: str, askar_schema
) -> SchemaUpgradeObj:
    """Get schema upgrade object."""

    async with profile.session() as session:
        schema_id = askar_schema.tags.get("schema_id")
        issuer_did = askar_schema.tags.get("schema_issuer_did")
        # Need to get schema from the ledger because the attribute names
        # are not stored in the wallet
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)

    _, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        schema_id,
        txn_record_type=GET_SCHEMA,
    )
    async with ledger:
        schema_from_ledger = await ledger.get_schema(schema_id)

    return SchemaUpgradeObj(
        schema_id,
        Schema.create(
            schema_id,
            askar_schema.tags.get("schema_name"),
            issuer_did,
            schema_from_ledger["attrNames"],
        ),
        askar_schema.tags.get("schema_name"),
        askar_schema.tags.get("schema_version"),
        issuer_did,
        askar_schema.id,
    )


async def get_cred_def_upgrade_object(
    profile: Profile, askar_cred_def
) -> CredDefUpgradeObj:
    """Get cred def upgrade object."""
    cred_def_id = askar_cred_def.tags.get("cred_def_id")
    async with profile.session() as session:
        # Need to get cred_def from the ledger because the tag
        # is not stored in the wallet and don't know wether it supports revocation
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
    _, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        cred_def_id,
        txn_record_type=GET_CRED_DEF,
    )
    async with ledger:
        cred_def_from_ledger = await ledger.get_credential_definition(cred_def_id)

    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        askar_cred_def_private = await storage.get_record(
            CATEGORY_CRED_DEF_PRIVATE, cred_def_id
        )
        askar_cred_def_key_proof = await storage.get_record(
            CATEGORY_CRED_DEF_KEY_PROOF, cred_def_id
        )

    cred_def = CredDef(
        issuer_id=askar_cred_def.tags.get("issuer_did"),
        schema_id=askar_cred_def.tags.get("schema_id"),
        tag=cred_def_from_ledger["tag"],
        type=cred_def_from_ledger["type"],
        value=cred_def_from_ledger["value"],
    )

    return CredDefUpgradeObj(
        cred_def_id,
        cred_def,
        askar_cred_def_private.value,
        askar_cred_def_key_proof.value,
        cred_def_from_ledger["value"].get("revocation", None),
        askar_cred_def=askar_cred_def,
    )


async def get_rev_reg_def_upgrade_object(
    profile: Profile,
    cred_def_upgrade_obj: CredDefUpgradeObj,
    askar_issuer_rev_reg_def,
    is_active: bool,
) -> RevRegDefUpgradeObj:
    """Get rev reg def upgrade object."""
    rev_reg_def_id = askar_issuer_rev_reg_def.tags.get("revoc_reg_id")

    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        askar_reg_rev_def_private = await storage.get_record(
            CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
        )

    revoc_reg_def_values = json.loads(askar_issuer_rev_reg_def.value)

    reg_def_value = RevRegDefValue(
        revoc_reg_def_values["revoc_reg_def"]["value"]["publicKeys"],
        revoc_reg_def_values["revoc_reg_def"]["value"]["maxCredNum"],
        revoc_reg_def_values["revoc_reg_def"]["value"]["tailsLocation"],
        revoc_reg_def_values["revoc_reg_def"]["value"]["tailsHash"],
    )

    rev_reg_def = RevRegDef(
        issuer_id=askar_issuer_rev_reg_def.tags.get("issuer_did"),
        cred_def_id=cred_def_upgrade_obj.cred_def_id,
        tag=revoc_reg_def_values["tag"],
        type=revoc_reg_def_values["revoc_def_type"],
        value=reg_def_value,
    )

    return RevRegDefUpgradeObj(
        rev_reg_def_id, rev_reg_def, askar_reg_rev_def_private.value, is_active
    )


async def get_rev_list_upgrade_object(
    profile: Profile, rev_reg_def_upgrade_obj: RevRegDefUpgradeObj
) -> RevListUpgradeObj:
    """Get revocation entry upgrade object."""
    rev_reg = rev_reg_def_upgrade_obj.rev_reg_def
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        askar_cred_rev_records = await storage.find_all_records(
            IssuerCredRevRecord.RECORD_TYPE,
            {"rev_reg_id": rev_reg_def_upgrade_obj.rev_reg_def_id},
        )

    revocation_list = [0] * rev_reg.value.max_cred_num
    for askar_cred_rev_record in askar_cred_rev_records:
        if askar_cred_rev_record.tags.get("state") == "revoked":
            revocation_list[int(askar_cred_rev_record.tags.get("cred_rev_id")) - 1] = 1

    rev_list = RevList(
        issuer_id=rev_reg.issuer_id,
        rev_reg_def_id=rev_reg_def_upgrade_obj.rev_reg_def_id,
        revocation_list=revocation_list,
        current_accumulator=json.loads(
            rev_reg_def_upgrade_obj.askar_issuer_rev_reg_def.value
        )["revoc_reg_entry"]["value"]["accum"],
    )

    return RevListUpgradeObj(
        rev_list,
        json.loads(rev_reg_def_upgrade_obj.askar_issuer_rev_reg_def.value)[
            "pending_pub"
        ],
        rev_reg_def_upgrade_obj.rev_reg_def_id,
        askar_cred_rev_records,
    )


async def upgrade_and_delete_schema_records(
    txn, schema_upgrade_obj: SchemaUpgradeObj
) -> None:
    """Upgrade and delete schema records."""
    schema_anoncreds = schema_upgrade_obj.schema
    await txn.handle.remove("schema_sent", schema_upgrade_obj.old_record_id)
    await txn.handle.replace(
        CATEGORY_SCHEMA,
        schema_upgrade_obj.schema_id,
        schema_anoncreds.to_json(),
        {
            "name": schema_upgrade_obj.name,
            "version": schema_upgrade_obj.version,
            "issuer_id": schema_upgrade_obj.issuer_id,
            "state": SchemaState.STATE_FINISHED,
        },
    )


async def upgrade_and_delete_cred_def_records(
    txn, anoncreds_schema, cred_def_upgrade_obj: CredDefUpgradeObj
) -> None:
    """Upgrade and delete cred def records."""
    cred_def_id = cred_def_upgrade_obj.cred_def_id
    anoncreds_schema = anoncreds_schema.to_dict()
    askar_cred_def = cred_def_upgrade_obj.askar_cred_def
    await txn.handle.remove("cred_def_sent", askar_cred_def.id)
    await txn.handle.replace(
        CATEGORY_CRED_DEF,
        cred_def_id,
        cred_def_upgrade_obj.cred_def.to_json(),
        tags={
            "schema_id": askar_cred_def.tags.get("schema_id"),
            "schema_issuer_id": anoncreds_schema["issuerId"],
            "issuer_id": askar_cred_def.tags.get("issuer_did"),
            "schema_name": anoncreds_schema["name"],
            "schema_version": anoncreds_schema["version"],
            "state": CredDefState.STATE_FINISHED,
            "epoch": askar_cred_def.tags.get("epoch"),
            # TODO We need to keep track of these but tags probably
            # isn't ideal. This suggests that a full record object
            # is necessary for non-private values
            "support_revocation": json.dumps(cred_def_upgrade_obj.revocation),
            "max_cred_num": str(cred_def_upgrade_obj.max_cred_num or 0),
        },
    )
    await txn.handle.replace(
        CATEGORY_CRED_DEF_PRIVATE,
        cred_def_id,
        CredentialDefinitionPrivate.load(
            cred_def_upgrade_obj.cred_def_private
        ).to_json_buffer(),
    )
    await txn.handle.replace(
        CATEGORY_CRED_DEF_KEY_PROOF,
        cred_def_id,
        KeyCorrectnessProof.load(cred_def_upgrade_obj.key_proof).to_json_buffer(),
    )


rev_reg_states_mapping = {
    "init": RevRegDefState.STATE_WAIT,
    "generated": RevRegDefState.STATE_ACTION,
    "posted": RevRegDefState.STATE_FINISHED,
    "active": RevRegDefState.STATE_FINISHED,
    "full": RevRegDefState.STATE_FULL,
    "decommissioned": RevRegDefState.STATE_DECOMMISSIONED,
}


async def upgrade_and_delete_rev_reg_def_records(
    txn, rev_reg_def_upgrade_obj: RevRegDefUpgradeObj
) -> None:
    """Upgrade and delete rev reg def records."""
    rev_reg_def_id = rev_reg_def_upgrade_obj.rev_reg_def_id
    askar_issuer_rev_reg_def = rev_reg_def_upgrade_obj.askar_issuer_rev_reg_def
    await txn.handle.remove(IssuerRevRegRecord.RECORD_TYPE, askar_issuer_rev_reg_def.id)
    await txn.handle.replace(
        CATEGORY_REV_REG_DEF,
        rev_reg_def_id,
        rev_reg_def_upgrade_obj.rev_reg_def.to_json(),
        tags={
            "cred_def_id": rev_reg_def_upgrade_obj.rev_reg_def.cred_def_id,
            "issuer_id": askar_issuer_rev_reg_def.tags.get("issuer_did"),
            "state": rev_reg_states_mapping[askar_issuer_rev_reg_def.tags.get("state")],
            "active": json.dumps(rev_reg_def_upgrade_obj.active),
        },
    )
    await txn.handle.replace(
        CATEGORY_REV_REG_DEF_PRIVATE,
        rev_reg_def_id,
        RevocationRegistryDefinitionPrivate.load(
            rev_reg_def_upgrade_obj.rev_reg_def_private
        ).to_json_buffer(),
    )


async def upgrade_and_delete_rev_entry_records(
    txn, rev_list_upgrade_obj: RevListUpgradeObj
) -> None:
    """Upgrade and delete revocation entry records."""
    next_index = 0
    for cred_rev_record in rev_list_upgrade_obj.cred_rev_records:
        if int(cred_rev_record.tags.get("cred_rev_id")) > next_index:
            next_index = int(cred_rev_record.tags.get("cred_rev_id"))
        await txn.handle.remove(IssuerCredRevRecord.RECORD_TYPE, cred_rev_record.id)

    await txn.handle.insert(
        CATEGORY_REV_LIST,
        rev_list_upgrade_obj.rev_reg_def_id,
        value_json={
            "rev_list": rev_list_upgrade_obj.rev_list.serialize(),
            "pending": rev_list_upgrade_obj.pending,
            "next_index": next_index + 1,
        },
        tags={
            "state": RevListState.STATE_FINISHED,
            "pending": json.dumps(rev_list_upgrade_obj.pending is not None),
        },
    )


async def upgrade_all_records_with_transaction(
    txn: any,
    schema_upgrade_objs: list[SchemaUpgradeObj],
    cred_def_upgrade_objs: list[CredDefUpgradeObj],
    rev_reg_def_upgrade_objs: list[RevRegDefUpgradeObj],
    rev_list_upgrade_objs: list[RevListUpgradeObj],
    link_secret: Optional[LinkSecret] = None,
) -> None:
    """Upgrade all objects with transaction."""
    for schema_upgrade_obj in schema_upgrade_objs:
        await upgrade_and_delete_schema_records(txn, schema_upgrade_obj)
    for cred_def_upgrade_obj in cred_def_upgrade_objs:
        await upgrade_and_delete_cred_def_records(
            txn, schema_upgrade_obj.schema, cred_def_upgrade_obj
        )
    for rev_reg_def_upgrade_obj in rev_reg_def_upgrade_objs:
        await upgrade_and_delete_rev_reg_def_records(txn, rev_reg_def_upgrade_obj)
    for rev_list_upgrade_obj in rev_list_upgrade_objs:
        await upgrade_and_delete_rev_entry_records(txn, rev_list_upgrade_obj)

    if link_secret:
        await txn.handle.replace(
            CATEGORY_LINK_SECRET,
            IndyCredxHolder.LINK_SECRET_ID,
            link_secret.to_dict()["value"]["ms"].encode("ascii"),
        )

    await txn.commit()


async def get_rev_reg_def_upgrade_objs(
    profile: Profile,
    cred_def_upgrade_obj: CredDefUpgradeObj,
    rev_list_upgrade_objs: list[RevListUpgradeObj],
) -> list[RevRegDefUpgradeObj]:
    """Get rev reg def upgrade objects."""

    rev_reg_def_upgrade_objs = []
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        # Must be sorted to find the active rev reg def
        askar_issuer_rev_reg_def_records = sorted(
            await storage.find_all_records(
                IssuerRevRegRecord.RECORD_TYPE,
                {"cred_def_id": cred_def_upgrade_obj.cred_def_id},
            ),
            key=lambda x: json.loads(x.value)["created_at"],
        )
    found_active = False
    for askar_issuer_rev_reg_def in askar_issuer_rev_reg_def_records:
        # active rev reg def is the oldest non-full and active rev reg def
        if (
            not found_active
            and askar_issuer_rev_reg_def.tags.get("state") != "full"
            and askar_issuer_rev_reg_def.tags.get("state") == "active"
        ):
            found_active = True
            is_active = True

        rev_reg_def_upgrade_obj = await get_rev_reg_def_upgrade_object(
            profile,
            cred_def_upgrade_obj,
            askar_issuer_rev_reg_def,
            is_active,
        )
        is_active = False
        rev_reg_def_upgrade_obj.askar_issuer_rev_reg_def = askar_issuer_rev_reg_def

        rev_reg_def_upgrade_objs.append(rev_reg_def_upgrade_obj)

        # add the revocation list upgrade object from reg def upgrade object
        rev_list_upgrade_objs.append(
            await get_rev_list_upgrade_object(profile, rev_reg_def_upgrade_obj)
        )
    return rev_reg_def_upgrade_objs


async def convert_records_to_anoncreds(profile) -> None:
    """Convert and delete old askar records."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        askar_schema_records = await storage.find_all_records(SCHEMA_SENT_RECORD_TYPE)

        schema_upgrade_objs = []
        cred_def_upgrade_objs = []
        rev_reg_def_upgrade_objs = []
        rev_list_upgrade_objs = []

        # Schemas
        for askar_schema in askar_schema_records:
            schema_upgrade_objs.append(
                await get_schema_upgrade_object(profile, askar_schema.id, askar_schema)
            )

        # CredDefs and Revocation Objects
        askar_cred_def_records = await storage.find_all_records(
            CRED_DEF_SENT_RECORD_TYPE, {}
        )
        for askar_cred_def in askar_cred_def_records:
            cred_def_upgrade_obj = await get_cred_def_upgrade_object(
                profile, askar_cred_def
            )
            rev_reg_def_upgrade_objs = await get_rev_reg_def_upgrade_objs(
                profile, cred_def_upgrade_obj, rev_list_upgrade_objs
            )
            # update the cred_def with the max_cred_num from first rev_reg_def
            if rev_reg_def_upgrade_objs:
                cred_def_upgrade_obj.max_cred_num = rev_reg_def_upgrade_objs[
                    0
                ].rev_reg_def.value.max_cred_num
            cred_def_upgrade_objs.append(cred_def_upgrade_obj)

        # Link secret
        link_secret_record = None
        try:
            link_secret_record = await session.handle.fetch(
                CATEGORY_LINK_SECRET, IndyCredxHolder.LINK_SECRET_ID
            )
        except AskarError:
            pass

        link_secret = None
        if link_secret_record:
            link_secret = LinkSecret.load(link_secret_record.raw_value)

        async with profile.transaction() as txn:
            try:
                await upgrade_all_records_with_transaction(
                    txn,
                    schema_upgrade_objs,
                    cred_def_upgrade_objs,
                    rev_reg_def_upgrade_objs,
                    rev_list_upgrade_objs,
                    link_secret,
                )
            except Exception as e:
                await txn.rollback()
                raise e


async def retry_converting_records(
    profile: Profile, upgrading_record: StorageRecord, retry: int, is_subwallet=False
) -> None:
    """Retry converting records to anoncreds."""

    async def fail_upgrade():
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.delete_record(upgrading_record)

    try:
        await convert_records_to_anoncreds(profile)
        await finish_upgrade_by_updating_profile_or_shutting_down(profile, is_subwallet)
        LOGGER.info(f"Upgrade complete via retry for wallet: {profile.name}")
    except Exception as e:
        LOGGER.error(f"Error when upgrading records for wallet {profile.name} : {e} ")
        if retry < max_retries:
            LOGGER.info(f"Retry attempt {retry + 1} to upgrade wallet {profile.name}")
            await asyncio.sleep(1)
            await retry_converting_records(
                profile, upgrading_record, retry + 1, is_subwallet
            )
        else:
            LOGGER.error(
                f"""Failed to upgrade wallet: {profile.name} after 5 retries. 
                Try fixing any connection issues and re-running the update"""
            )
            await fail_upgrade()


async def upgrade_wallet_to_anoncreds_if_requested(
    profile: Profile, is_subwallet=False
) -> None:
    """Get upgrading record and attempt to upgrade wallet to anoncreds."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            upgrading_record = await storage.find_record(
                RECORD_TYPE_ACAPY_UPGRADING, {}
            )
            if upgrading_record.value == UPGRADING_RECORD_FINISHED:
                IsAnoncredsSingleton().set_wallet(profile.name)
                return
        except StorageNotFoundError:
            return

        try:
            LOGGER.info("Upgrade in process for wallet: %s", profile.name)
            await convert_records_to_anoncreds(profile)
            await finish_upgrade_by_updating_profile_or_shutting_down(
                profile, is_subwallet
            )
        except Exception as e:
            LOGGER.error(f"Error when upgrading wallet {profile.name} : {e} ")
            await retry_converting_records(profile, upgrading_record, 0, is_subwallet)


async def finish_upgrade(profile: Profile):
    """Finish record by setting records and caches."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            storage_type_record = await storage.find_record(
                type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
            )
            await storage.update_record(
                storage_type_record, STORAGE_TYPE_VALUE_ANONCREDS, {}
            )
        # This should only happen for subwallets
        except StorageNotFoundError:
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_STORAGE_TYPE,
                    STORAGE_TYPE_VALUE_ANONCREDS,
                )
            )
    await finish_upgrading_record(profile)
    IsAnoncredsSingleton().set_wallet(profile.name)
    UpgradeInProgressSingleton().remove_wallet(profile.name)


async def finish_upgrading_record(profile: Profile):
    """Update upgrading record to finished."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            upgrading_record = await storage.find_record(
                RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
            )
            await storage.update_record(upgrading_record, UPGRADING_RECORD_FINISHED, {})
        except StorageNotFoundError:
            return


async def upgrade_subwallet(profile: Profile) -> None:
    """Upgrade subwallet to anoncreds."""
    async with profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        wallet_id = profile.settings.get("wallet.id")
        cache = profile.inject_or(BaseCache)
        await cache.flush()
        settings = {"wallet.type": STORAGE_TYPE_VALUE_ANONCREDS}
        await multitenant_mgr.update_wallet(wallet_id, settings)


async def finish_upgrade_by_updating_profile_or_shutting_down(
    profile: Profile, is_subwallet=False
):
    """Upgrade wallet to anoncreds and set storage type."""
    if is_subwallet:
        await upgrade_subwallet(profile)
        await finish_upgrade(profile)
        LOGGER.info(
            f"""Upgrade of subwallet {profile.settings.get('wallet.name')} has completed. Profile is now askar-anoncreds"""  # noqa: E501
        )
    else:
        await finish_upgrade(profile)
        LOGGER.info(
            f"Upgrade of base wallet {profile.settings.get('wallet.name')} to anoncreds has completed. Shutting down agent."  # noqa: E501
        )
        asyncio.get_event_loop().stop()


async def check_upgrade_completion_loop(profile: Profile, is_subwallet=False):
    """Check if upgrading is complete."""
    async with profile.session() as session:
        while True:
            storage = session.inject(BaseStorage)
            LOGGER.debug(f"Checking upgrade completion for wallet: {profile.name}")
            try:
                upgrading_record = await storage.find_record(
                    RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
                )
                if upgrading_record.value == UPGRADING_RECORD_FINISHED:
                    IsAnoncredsSingleton().set_wallet(profile.name)
                    UpgradeInProgressSingleton().remove_wallet(profile.name)
                    if is_subwallet:
                        await upgrade_subwallet(profile)
                        LOGGER.info(
                            f"""Upgrade of subwallet {profile.settings.get('wallet.name')} has completed. Profile is now askar-anoncreds"""  # noqa: E501
                        )
                        return
                    LOGGER.info(
                        f"Upgrade complete for wallet: {profile.name}, shutting down agent."  # noqa: E501
                    )
                    # Shut down agent if base wallet
                    asyncio.get_event_loop().stop()
            except StorageNotFoundError:
                # If the record is not found, the upgrade failed
                return

            await asyncio.sleep(1)
