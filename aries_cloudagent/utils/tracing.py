import json
import logging
import time
import requests

from ..transport.inbound.message import InboundMessage
from ..transport.outbound.message import OutboundMessage
from ..messaging.agent_message import AgentMessage


LOGGER = logging.getLogger(__name__)


def trace_event(
        context, 
        message, 
        handler: str = None,
        ellapsed_milli: int = None,
        outcome: str = None,
        raise_errors: bool = False):
    """
    Log a trace event to a configured target.

    Args:
        context: The application context, attributes of interest are:
            context["trace.enabled"]: True if we are logging events
            context["trace.target"]: Trace target ("log", "message" or an http endpoint)
            context["trace.tag"]: Tag to be included in trace output
        message: the current message, can be an AgentMessage, InboundMessage or OutboundMessage
        event: Dict that will be converted to json and posted to the target
    """

    if context.get("trace.enabled"):
        # build the event to log
        # TODO check instance type of message to determine how to get message and thread id's
        event = {
            "message_id": message._id if message else "",
            "thread_id": message._thread.thid if message else "",
            "traced_type": message._type if message else "",
            "timestamp": time.time(),
            "handler": handler,
            "ellapsed_milli": ellapsed_milli,
            "outcome": outcome,
        }
        event_str = json.dumps(event)

        try:
            # check our target
            if context["trace.target"] == "message":
                # TODO, just log for now
                LOGGER.setLevel(logging.INFO)
                LOGGER.info(" %s %s", context["trace.tag"], event_str)
            elif context["trace.target"] == "log":
                # write to standard log file
                LOGGER.setLevel(logging.INFO)
                LOGGER.info(" %s %s", context["trace.tag"], event_str)
            else:
                # should be an http endpoint
                resp = requests.post(
                    context["trace.target"] + (context["trace.tag"] if context["trace.tag"] else ""),
                    data=event_str,
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            if raise_errors:
                raise
            LOGGER.error(
                "Error logging trace %s %s %s",
                context["trace.target"],
                context["trace.tag"],
                event_str
            )
            LOGGER.exception(e)

    else:
        # trace is not enabled so just return
        pass
