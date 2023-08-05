"""Event tracing."""

import datetime
import json
import logging
import time

import requests

from marshmallow import fields

from ..messaging.agent_message import AgentMessage
from ..messaging.decorators.trace_decorator import (
    TRACE_LOG_TARGET,
    TRACE_MESSAGE_TARGET,
    TraceReport,
)
from ..messaging.models.base_record import BaseExchangeRecord
from ..messaging.models.openapi import OpenAPISchema
from ..transport.inbound.message import InboundMessage
from ..transport.outbound.message import OutboundMessage

LOGGER = logging.getLogger(__name__)
DT_FMT = "%Y-%m-%d %H:%M:%S.%f%z"


class AdminAPIMessageTracingSchema(OpenAPISchema):
    """
    Request/result schema including agent message tracing.

    This is to be used as a superclass for aca-py admin input/output
    messages that need to support tracing.
    """

    trace = fields.Boolean(
        required=False,
        dump_default=False,
        metadata={
            "description": "Record trace information, based on agent configuration"
        },
    )


def get_timer() -> float:
    """Return a timer."""
    return time.perf_counter()


def tracing_enabled(context, message) -> bool:
    """Determine whether to log trace messages or not."""
    # check if tracing is explicitely on
    if context.get("trace.enabled"):
        return True

    if message:
        if isinstance(message, AgentMessage):
            # if there is a trace decorator on the messages then continue to trace
            if message._trace:
                return True
        elif isinstance(message, BaseExchangeRecord):
            if message.trace:
                return True
        elif isinstance(message, dict):
            # if there is a trace decorator on the messages then continue to trace
            if message.get("~trace"):
                return True
            if message.get("trace"):
                return message.get("trace")
        elif isinstance(message, str):
            if "~trace" in message:
                return True
            if "trace" in message:
                msg = json.loads(message)
                return msg.get("trace")
        elif isinstance(message, OutboundMessage):
            if message.payload and isinstance(message.payload, AgentMessage):
                if message.payload._trace:
                    return True
            elif message.payload and isinstance(message.payload, dict):
                if message.payload.get("~trace") or message.payload.get("trace"):
                    return True
            elif message.payload and isinstance(message.payload, str):
                if "trace" in message.payload:  # includes "~trace" in message.payload
                    return True

    # default off
    return False


def decode_inbound_message(message):
    """Return bundled message if appropriate."""

    if message and isinstance(message, OutboundMessage):
        if message.payload and isinstance(message.payload, AgentMessage):
            return message.payload
        elif message.payload and isinstance(message.payload, dict):
            return message.payload
        elif message.payload and isinstance(message.payload, str):
            try:
                return json.loads(message.payload)
            except Exception:
                pass
    elif message and isinstance(message, str):
        try:
            return json.loads(message)
        except Exception:
            pass

    # default is the provided message
    return message


def trace_event(
    context,
    message,
    handler: str = None,
    outcome: str = None,
    perf_counter: float = None,
    force_trace: bool = False,
    raise_errors: bool = False,
) -> float:
    """
    Log a trace event to a configured target.

    Args:
        context: The application context, attributes of interest are:
            context["trace.enabled"]: True if we are logging events
            context["trace.target"]: Trace target ("log", "message" or an http endpoint)
            context["trace.tag"]: Tag to be included in trace output
        message: the current message, can be an AgentMessage,
            InboundMessage, OutboundMessage or Exchange record
        event: Dict that will be converted to json and posted to the target
    """

    ret = time.perf_counter()

    if force_trace or tracing_enabled(context, message):
        message = decode_inbound_message(message)

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
            if message._thread and message._thread.thid:
                thread_id = str(message._thread.thid)
            else:
                thread_id = msg_id
            msg_type = str(message._type)
        elif message and isinstance(message, InboundMessage):
            # TODO not sure if we can log an InboundMessage before it's "handled"
            msg_id = str(message.session_id) if message.session_id else "N/A"
            thread_id = str(message.session_id) if message.session_id else "N/A"
            msg_type = str(message.__class__.__name__)
        elif message and isinstance(message, OutboundMessage):
            msg_id = str(message.reply_thread_id) if message.reply_thread_id else "N/A"
            thread_id = msg_id
            msg_type = str(message.__class__.__name__)
        elif message and isinstance(message, dict):
            msg_id = str(message["@id"]) if message.get("@id") else "N/A"
            if message.get("~thread") and message["~thread"].get("thid"):
                thread_id = str(message["~thread"]["thid"])
            elif message.get("thread_id"):
                thread_id = str(message["thread_id"])
            else:
                thread_id = msg_id
            if message.get("@type"):
                msg_type = str(message["@type"])
            else:
                if message.get("~thread"):
                    msg_type = "dict:Message"
                elif message.get("thread_id"):
                    msg_type = "dict:Exchange"
                else:
                    msg_type = "dict"
        elif isinstance(message, BaseExchangeRecord):
            msg_id = "N/A"
            thread_id = str(message.thread_id)
            msg_type = str(message.__class__.__name__)
        else:
            msg_id = "N/A"
            thread_id = "N/A"
            msg_type = str(message.__class__.__name__)
        ep_time = time.time()
        str_time = datetime.datetime.utcfromtimestamp(ep_time).strftime(DT_FMT)
        event = {
            "msg_id": msg_id,
            "thread_id": thread_id if thread_id else msg_id,
            "traced_type": msg_type,
            "timestamp": ep_time,
            "str_time": str_time,
            "handler": str(handler),
            "ellapsed_milli": int(1000 * (ret - perf_counter)) if perf_counter else 0,
            "outcome": str(outcome),
        }
        event_str = json.dumps(event)

        try:
            # check our target - if we get this far we know we are logging the event
            if context["trace.target"] == TRACE_MESSAGE_TARGET and isinstance(
                message, AgentMessage
            ):
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
            elif context["trace.target"] == TRACE_LOG_TARGET:
                # write to standard log file
                LOGGER.setLevel(logging.INFO)
                LOGGER.info(" %s %s", context["trace.tag"], event_str)
            else:
                # should be an http endpoint
                _ = requests.post(
                    context["trace.target"]
                    + (context["trace.tag"] if context["trace.tag"] else ""),
                    data=event_str,
                    headers={"Content-Type": "application/json"},
                )
        except Exception as e:
            if raise_errors:
                raise
            LOGGER.error(
                "Error logging trace target: %s tag: %s event: %s",
                context.get("trace.target"),
                context.get("trace.tag"),
                event_str,
            )
            LOGGER.exception(e)

    else:
        # trace is not enabled so just return
        pass

    return ret
