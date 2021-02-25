"""V2.0 indy issue-credential cred format."""

import uuid
import json
from typing import Coroutine, Mapping

from ..manager import V20CredManagerError
from .....core.profile import Profile
from .....messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....storage.base import BaseStorage
from .....indy.issuer import IndyIssuer
from .....cache.base import BaseCache
from .....ledger.base import BaseLedger
from ..messages.cred_format import V20CredFormat


class IndyCredFormat:
    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile instance.

        Returns:
            The profile instance for this credential manager

        """
        return self._profile

    async def _match_sent_cred_def_id(self, tag_query: Mapping[str, str]) -> str:
        """Return most recent matching id of cred def that agent sent to ledger."""

        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=CRED_DEF_SENT_RECORD_TYPE, tag_query=tag_query
            )
        if not found:
            raise V20CredManagerError(
                f"Issuer has no operable cred def for proposal spec {tag_query}"
            )
        return max(found, key=lambda r: int(r.tags["epoch"])).tags["cred_def_id"]

    async def create_proposal(
        self, filter: Mapping[str, str]
    ) -> Coroutine[V20CredFormat, AttachDecorator]:
        id = uuid()

        return (
            V20CredFormat(attach_id=id, format_=V20CredFormat.Format.INDY),
            AttachDecorator.data_base64(filter, ident=id),
        )

    async def create_offer(
        self, cred_proposal_message
    ) -> Coroutine[V20CredFormat, AttachDecorator]:
        issuer = self.profile.inject(IndyIssuer)
        ledger = self.profile.inject(BaseLedger)
        cache = self.profile.inject(BaseCache, required=False)

        cred_def_id = await self._match_sent_cred_def_id(
            V20CredFormat.Format.INDY.get_attachment_data(
                cred_proposal_message.formats,
                cred_proposal_message.filters_attach,
            )
        )

        async def _create():
            offer_json = await issuer.create_credential_offer(cred_def_id)
            return json.loads(offer_json)

        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
            schema = await ledger.get_schema(schema_id)
        schema_attrs = {attr for attr in schema["attrNames"]}
        preview_attrs = {
            attr for attr in cred_proposal_message.cred_preview.attr_dict()
        }
        if preview_attrs != schema_attrs:
            raise V20CredManagerError(
                f"Preview attributes {preview_attrs} "
                f"mismatch corresponding schema attributes {schema_attrs}"
            )

        cred_offer = None
        cache_key = f"credential_offer::{cred_def_id}"

        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    cred_offer = entry.result
                else:
                    cred_offer = await _create(cred_def_id)
                    await entry.set_result(cred_offer, 3600)
        if not cred_offer:
            cred_offer = await _create(cred_def_id)

        id = uuid()
        return (
            V20CredFormat(attach_id=id, format_=V20CredFormat.Format.INDY),
            AttachDecorator.data_base64(cred_offer, ident=id),
        )
