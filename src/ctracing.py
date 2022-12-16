#!/usr/bin/env python3
# Created By  : Damien Degois <damien@degois.info>
# Created Date: 2022-11-18
import os
import uuid
from typing import Any
from typing import Callable
from typing import Optional
from typing import Sequence

import requests
from opentelemetry import context
from opentelemetry import trace
from opentelemetry.attributes import BoundedAttributes  # type: ignore[attr-defined]
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.util import BoundedList
from opentelemetry.trace import Link
from opentelemetry.trace import NonRecordingSpan
from opentelemetry.trace import SpanContext
from opentelemetry.trace import SpanKind
from opentelemetry.trace import TraceFlags
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation import get_current_span
from opentelemetry.trace.status import Status
from opentelemetry.trace.status import StatusCode


class CallbackSpanExporter(SpanExporter):
    def __init__(self, callback: Callable[[ReadableSpan], bool]) -> None:
        self._callback = callback

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        had_failures = False
        for span in spans:
            try:
                if not self._callback(span):
                    had_failures = True
            except Exception:
                had_failures = True

        return SpanExportResult.FAILURE if had_failures else SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        ...

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class BasicHttpSpanExporter(SpanExporter):
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._sess = requests.Session()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        had_failures = False
        for span in spans:
            message = convert_span_to_mesage(span)
            resp = self._sess.post(
                self._endpoint,
                headers={"Content-Type": "application/json"},
                json=message,
            )
            try:
                resp.raise_for_status()
            except Exception:
                had_failures = True

        return SpanExportResult.FAILURE if had_failures else SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        ...

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def convert_span_to_mesage(span: ReadableSpan) -> dict[str, Any]:
    message: dict[str, Any] = {
        "_message_type": "spanreport",
        "_message_version": 1,
        "_id": uuid.uuid4().hex,
        "_span": {
            "version": 2,
            "trace_id": "%0.32x" % span.context.trace_id,
            "span_id": "%0.16x" % span.context.span_id,
            "start_time_unix_nano": span.start_time,
            "end_time_unix_nano": span.end_time,
            "name": span.name,
            "kind": span.kind.name,
        },
    }
    spansect = message.get("_span", {})
    if span.parent is not None:
        spansect["parent_id"] = "%0.16x" % span.parent.span_id

    attrs = {}
    if span.attributes:
        for k, v in span.attributes.items():
            attrs[k] = v
    attrs["service.name"] = span.resource.attributes.get("service.name", "unknown-servicename")
    spansect["attributes"] = attrs

    if span.events:
        evts = []
        for evt in span.events:
            evtdict = {
                "name": evt.name,
                "time_unix_nano": evt.timestamp,
            }
            if evt.attributes:
                evtattrs = {}
                for k, v in evt.attributes.items():
                    evtattrs[k] = v
                evtdict["attributes"] = evtattrs
            evts.append(evtdict)
        spansect["events"] = evts
    if span.links:
        links = []
        for link in span.links:
            linkdict: dict[str, Any] = {
                "context": {
                    "trace_id": "%0.32x" % link.context.trace_id,
                    "span_id": "%0.16x" % link.context.span_id,
                }
            }
            if link.attributes:
                linkattrs = {}
                for k, v in link.attributes.items():
                    linkattrs[k] = v
                linkdict["attributes"] = linkattrs
            links.append(linkdict)
        spansect["links"] = links
    return message


def convert_message_to_span(content) -> ReadableSpan:
    spandetails = content.get("_span", {})
    parentcontext = None
    if "parent_id" in spandetails:
        parentcontext = SpanContext(
            trace_id=int(spandetails.get("trace_id"), 16),
            span_id=int(spandetails.get("parent_id"), 16),
            is_remote=True,
        )

    eventlist = []
    if spandetails.get("events", []):
        for spanevent in spandetails.get("events"):
            eventlist.append(
                Event(
                    name=spanevent.get("name"),
                    timestamp=spanevent.get("time_unix_nano"),
                    attributes=BoundedAttributes(128, spanevent.get("attributes", {})),
                )
            )
    events = BoundedList.from_seq(128, eventlist)

    attributes = spandetails.get("attributes", {})

    try:
        kind = SpanKind[spandetails.get("kind", "INTERNAL")]
    except KeyError:
        kind = SpanKind.INTERNAL

    try:
        statuscode = StatusCode[spandetails.get("status")]
    except KeyError:
        statuscode = StatusCode.UNSET

    linkseq = []
    for link in spandetails.get("links", []):
        linkseq.append(
            Link(
                SpanContext(
                    trace_id=int(link.get("context", {}).get("trace_id"), 16),
                    span_id=int(link.get("context", {}).get("span_id"), 16),
                    is_remote=True,
                    trace_flags=TraceFlags(0x01),
                ),
                attributes=BoundedAttributes(128, link.get("attributes", {})),
            )
        )

    links = BoundedList.from_seq(128, linkseq)

    return ReadableSpan(
        context=SpanContext(
            trace_id=int(spandetails.get("trace_id"), 16),
            span_id=int(spandetails.get("span_id"), 16),
            is_remote=True,
        ),
        parent=parentcontext,
        name=spandetails.get("name"),
        attributes=BoundedAttributes(128, attributes=attributes),
        events=events,
        kind=kind,
        links=links,
        status=Status(statuscode),
        start_time=int(spandetails.get("start_time_unix_nano")),
        end_time=int(spandetails.get("end_time_unix_nano")),
        resource=Resource(
            attributes={
                SERVICE_NAME: spandetails.get("attributes", {}).get("service.name", "unknown-servicename")
            }
        ),
    )


def add_batchspan_processor(exporter: SpanExporter):
    tp: TracerProvider = trace.get_tracer_provider()  # type: ignore
    tp.add_span_processor(BatchSpanProcessor(exporter))


def add_simplespan_processor(exporter: SpanExporter):
    tp: TracerProvider = trace.get_tracer_provider()  # type: ignore
    tp.add_span_processor(SimpleSpanProcessor(exporter))


def init_tracer(
    service_name: str,
) -> Tracer:
    trace.set_tracer_provider(TracerProvider(resource=Resource(attributes={SERVICE_NAME: service_name})))

    tp: TracerProvider = trace.get_tracer_provider()  # type: ignore

    basichttp_endpoint = os.environ.get("OTEL_EXPORTER_BASICHTTP_ENDPOINT", None)
    if basichttp_endpoint is not None:  # pragma: no cover
        tp.add_span_processor(
            BatchSpanProcessor(
                BasicHttpSpanExporter(
                    endpoint=basichttp_endpoint,
                )
            )
        )

    otlp_entpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    if otlp_entpoint is not None:  # pragma: no cover
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            tp.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=otlp_entpoint,
                    )
                )
            )
        except ModuleNotFoundError:
            import warnings

            warnings.warn(
                "Unable to import OTLPSpanExporter, is opentelemetry-exporter-otlp installed ?",
                stacklevel=2,
            )

    if os.environ.get("OTEL_EXPORTER_CONSOLE", "false").lower() == "true":
        tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    return trace.get_tracer(service_name)


def init_parent(
    trace_id: Optional[str] = None,
    parent_id: Optional[str] = None,
):
    if trace_id is not None and parent_id is not None:
        span_context = SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(parent_id, 16),
            is_remote=True,
            trace_flags=TraceFlags(0x01),
        )
        context.attach(trace.set_span_in_context(NonRecordingSpan(span_context)))


def init_parent_from_traceparent(traceparent: str) -> bool:
    traceparent_splited = traceparent.split("-")
    if len(traceparent_splited) != 4:
        return False
    trace_id = traceparent_splited[1]
    parent_span_id = traceparent_splited[2]
    init_parent(trace_id, parent_span_id)
    return True


def init_parent_from_env():
    traceparent = os.environ.get("TRACEPARENT")
    if traceparent is not None:
        traceparent_splited = traceparent.split("-")
        trace_id = traceparent_splited[1]
        parent_span_id = traceparent_splited[2]

        init_parent(trace_id, parent_span_id)


def get_span_hex_context() -> tuple[str, str]:
    cur_span_context = get_current_span().get_span_context()
    return "%0.32x" % cur_span_context.trace_id, "%0.16x" % cur_span_context.span_id
