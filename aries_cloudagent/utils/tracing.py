"""Event tracing."""

import json
import logging
import time
import datetime
import requests

from ..transport.inbound.message import InboundMessage
from ..transport.outbound.message import OutboundMessage
from ..messaging.agent_message import AgentMessage
from ..messaging.decorators.trace_decorator import TraceReport, TRACE_MESSAGE_TARGET


LOGGER = logging.getLogger(__name__)
DT_FMT = '%Y-%m-%d %H:%M:%S.%f%z'


def get_timer() -> float:
    """Return a timer."""
    return time.perf_counter()


def tracing_enabled(context, message) -> bool:
    """Determine whether to log trace messages or not."""
    # check if tracing is explicitely on
    if context.get("trace.enabled"):
        return True

    # if there is a trace decorator on the messages then continue to trace
    if message and isinstance(message, AgentMessage):
        if message._trace:
            return True

    # default off
    return False


def trace_event(
        context,
        message,
        handler: str = None,
        outcome: str = None,
        perf_counter: float = None,
        force_trace: bool = False,
        raise_errors: bool = False
) -> float:
    """
    Log a trace event to a configured target.

    Args:
        context: The application context, attributes of interest are:
            context["trace.enabled"]: True if we are logging events
            context["trace.target"]: Trace target
                ("log", "message" or an http endpoint)
            context["trace.tag"]: Tag to be included in trace output
        message: the current message, can be an AgentMessage,
                InboundMessage or OutboundMessage
        event: Dict that will be converted to json and posted to the target
    """

    ret = time.perf_counter()

    if force_trace or tracing_enabled(context, message):
        # build the event to log
        # TODO check instance type of message to determine how to
        # get message and thread id's
        if not handler:
            if context and context.get("trace.label"):
                handler = context.get("trace.label")
            else:
                handler = "aca-py.agent"
        msg_id = ""
        thread_id = ""
        msg_type = ""
        if message and isinstance(message, AgentMessage):
            msg_id = str(message._id)
            thread_id = str(message._thread.thid) if message._thread else msg_id
            msg_type = str(message._type)
        elif message and isinstance(message, InboundMessage):
            # TODO not sure if we can log an InboundMessage before it's "handled"
            msg_id = str(message.session_id) if message.session_id else "N/A"
            thread_id = str(message.session_id) if message.session_id else "N/A"
            msg_type = "InboundMessage"
        elif message and isinstance(message, OutboundMessage):
            msg_id = str(message.reply_thread_id) if message.reply_thread_id else "N/A"
            thread_id = msg_id
            msg_type = "OutboundMessage"
        elif message and isinstance(message, dict):
            msg_id = str(message["msg_id"])
            thread_id = str(message["thread_id"])
            msg_type = str(message["type"])
        else:
            msg_type = str(message)
        ep_time = time.time()
        str_time = datetime.datetime.utcfromtimestamp(ep_time).strftime(DT_FMT)
        event = {
            "msg_id": msg_id,
            "thread_id": thread_id if thread_id else msg_id,
            "traced_type": msg_type,
            "timestamp": ep_time,
            "str_time": str_time,
            "handler": handler,
            "ellapsed_milli": int(1000 * (ret - perf_counter)) if perf_counter else 0,
            "outcome": outcome,
        }
        event_str = json.dumps(event)

        try:
            # check our target - if we get this far we know we are logging the event
            if (context["trace.target"] == TRACE_MESSAGE_TARGET
                    and isinstance(message, AgentMessage)):
                # add a trace report to the existing message
                trace_report = TraceReport(
                    msg_id=event["msg_id"],
                    thread_id=event["thread_id"],
                    traced_type=event["traced_type"],
                    timestamp=event["timestamp"],
                    str_time=event["str_time"],
                    handler=event["handler"],
                    ellapsed_milli=event["ellapsed_milli"],
                    outcome=event["outcome"],
                )
                message.add_trace_report(trace_report)
            elif context["trace.target"] == "log":
                # write to standard log file
                LOGGER.setLevel(logging.INFO)
                LOGGER.info(" %s %s", context["trace.tag"], event_str)
            else:
                # should be an http endpoint
                _ = requests.post(
                    context["trace.target"] +
                    (context["trace.tag"] if context["trace.tag"] else ""),
                    data=event_str,
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            if raise_errors:
                raise
            LOGGER.error(
                "Error logging trace target: %s tag: %s event: %s",
                context.get("trace.target"),
                context.get("trace.tag"),
                event_str
            )
            LOGGER.exception(e)

    else:
        # trace is not enabled so just return
        pass

    return ret
