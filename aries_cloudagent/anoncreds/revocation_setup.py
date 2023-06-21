"""Automated setup process for AnonCreds credential definitions with revocation."""

import re

from ..anoncreds.revocation import AnonCredsRevocation
from ..core.profile import Profile
from ..core.event_bus import Event, EventBus
from .events import (
    CRED_DEF_FINISHED_PATTERN,
    REV_REG_DEF_FINISHED_PATTERN,
    REV_LIST_FINISHED_PATTERN,
    CredDefFinishedEvent,
    RevRegDefFinishedEvent,
    RevListFinishedEvent,
)

REGISTRY_TYPE = "CL_ACCUM"
DEFAULT_TAG = "default"


class AnonCredsRevocationSetupManager:
    """Manager for automated setup of revocation support."""

    def __init__(self):
        """Init manager."""

    async def setup(self, profile: Profile):
        """Register event listeners."""
        bus = profile.inject(EventBus)
        bus.subscribe(re.compile(CRED_DEF_FINISHED_PATTERN), self.on_cred_def)
        bus.subscribe(re.compile(REV_REG_DEF_FINISHED_PATTERN), self.on_rev_reg_def)
        bus.subscribe(re.compile(REV_LIST_FINISHED_PATTERN), self.on_rev_list)

    async def on_cred_def(self, profile: Profile, event: CredDefFinishedEvent):
        """Handle cred def finished."""
        payload = event.payload
        if payload.support_revocation and payload.novel and payload.auto_create_rev_reg:
            # this kicks off the revocation registry creation process, which is 3 steps:
            # 1 - create revocation registry (ledger transaction may require endorsement)
            # 2 - upload tails file
            # 3 - create revocation entry (ledger transaction may require endorsement)
            # For a cred def we also automatically create a second "pending" revocation
            # registry, so when the first one fills up we can continue to issue credentials
            # without a delay
            revoc = AnonCredsRevocation(profile)
            await revoc.create_and_register_revocation_registry_definition(
                issuer_id=payload.issuer_id,
                cred_def_id=payload.cred_def_id,
                registry_type=REGISTRY_TYPE,
                max_cred_num=payload.max_cred_num,
                tag=DEFAULT_TAG,
            )

    async def on_rev_reg_def(self, profile: Profile, event: RevRegDefFinishedEvent):
        """Handle rev reg def finished."""
        revoc = AnonCredsRevocation(profile)
        await revoc.upload_tails_file(event.payload.rev_reg_def)
        await revoc.create_and_register_revocation_list(event.payload.rev_reg_def_id)

        # Generate the registry and upload the tails file
        async def generate(rr_record: IssuerRevRegRecord) -> dict:
            await rr_record.generate_registry(profile)
            public_uri = (
                tails_base_url.rstrip("/") + f"/{registry_record.revoc_reg_id}"
            )  # TODO: update to include /hash
            await rr_record.set_tails_file_public_uri(profile, public_uri)
            rev_reg_resp = await rr_record.send_def(
                profile,
                write_ledger=write_ledger,
                endorser_did=endorser_did,
            )
            if write_ledger:
                # Upload the tails file
                await rr_record.upload_tails_file(profile)

                # Post the initial revocation entry
                await notify_revocation_entry_event(profile, record_id, meta_data)
            else:
                transaction_manager = TransactionManager(profile)
                try:
                    revo_transaction = await transaction_manager.create_record(
                        messages_attach=rev_reg_resp["result"],
                        connection_id=connection.connection_id,
                        meta_data=event.payload,
                    )
                except StorageError as err:
                    raise TransactionManagerError(reason=err.roll_up) from err

                # if auto-request, send the request to the endorser
                if profile.settings.get_value("endorser.auto_request"):
                    try:
                        (
                            revo_transaction,
                            revo_transaction_request,
                        ) = await transaction_manager.create_request(
                            transaction=revo_transaction,
                            # TODO see if we need to parameterize these params
                            # expires_time=expires_time,
                            # endorser_write_txn=endorser_write_txn,
                        )
                    except (StorageError, TransactionManagerError) as err:
                        raise TransactionManagerError(reason=err.roll_up) from err

                    responder = profile.inject_or(BaseResponder)
                    if responder:
                        await responder.send(
                            revo_transaction_request,
                            connection_id=connection.connection_id,
                        )
                    else:
                        LOGGER.warning(
                            "Configuration has no BaseResponder: cannot update "
                            "revocation on registry ID: %s",
                            record_id,
                        )

        record_id = meta_data["context"]["issuer_rev_id"]
        async with profile.session() as session:
            registry_record = await IssuerRevRegRecord.retrieve_by_id(
                session, record_id
            )
        await shield(generate(registry_record))

        create_pending_rev_reg = meta_data["processing"].get(
            "create_pending_rev_reg", False
        )
        if write_ledger and create_pending_rev_reg:
            revoc = AnonCredsRevocation(profile)
            await revoc.init_issuer_registry(
                registry_record.issuer_id,
                registry_record.cred_def_id,
                registry_record.max_cred_num,
                registry_record.revoc_def_type,
                endorser_connection_id=endorser_connection_id,
            )

    async def on_rev_list(self, profile: Profile, event: RevListFinishedEvent):
        """Handle rev list finished."""
