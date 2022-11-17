from typing import Coroutine, Union

from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....messaging.models.base_record import BaseRecord
from .message import ProblemReport


async def internal_error(
    err: BaseError,
    http_error_class,
    record: Union[ConnRecord, BaseRecord],
    outbound_handler: Coroutine,
    code: str = None,
):
    """Send problem report and raise corresponding HTTP error."""
    if record:
        error_result = ProblemReport(
            description={"en": err.roll_up, "code": code or "abandoned"}
        )
        thid = getattr(record, "thread_id", None)
        if thid:
            error_result.assign_thread_id(thid)
        await outbound_handler(error_result, connection_id=record.connection_id)

    raise http_error_class(reason=err.roll_up) from err
