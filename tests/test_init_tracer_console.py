#!/usr/bin/env python3
import os
from unittest import mock

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import ctracing


def test_init_tracer_console():
    with mock.patch.dict(os.environ, {"OTEL_EXPORTER_CONSOLE": "true"}):
        ctracing.init_tracer("test-ctracing")

    tp: TracerProvider = trace.get_tracer_provider()  # type: ignore
    tp._active_span_processor._span_processors
    assert len(tp._active_span_processor._span_processors) == 1
    spanproc = tp._active_span_processor._span_processors[0]
    assert type(spanproc) is SimpleSpanProcessor
    assert type(spanproc.span_exporter) is ConsoleSpanExporter
