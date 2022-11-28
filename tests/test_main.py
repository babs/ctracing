#!/usr/bin/env python3
import os
from unittest import mock

import pytest

import ctracing

tracer = ctracing.init_tracer("test-ctracing")


@pytest.fixture
def traceparent_env(request):
    traceparent = "00-0000000000000000000000000000000a-000000000000000b-01"
    with mock.patch.dict(os.environ, {"TRACEPARENT": traceparent}):
        yield


def _check_initial_state():
    (trace_id, span_id) = ctracing.get_span_hex_context()
    assert trace_id == "00000000000000000000000000000000"
    assert span_id == "0000000000000000"


def test_main_simplespan():
    def inner(span: ctracing.ReadableSpan) -> bool:
        ...

    ctracing.add_simplespan_processor(ctracing.CallbackSpanExporter(inner))


def test_main_batchspan():
    def inner(span: ctracing.ReadableSpan) -> bool:
        ...

    ctracing.add_batchspan_processor(ctracing.CallbackSpanExporter(inner))


def test_get_span_hex_context():
    context = ctracing.get_span_hex_context()
    assert context == ("00000000000000000000000000000000", "0000000000000000")


def test_init_parent():
    _check_initial_state()
    expected_trace_id = "0000000000000000000000000000000c"
    expected_span_id = "000000000000000d"
    ctracing.init_parent(expected_trace_id, expected_span_id)
    (trace_id, span_id) = ctracing.get_span_hex_context()
    assert trace_id == expected_trace_id
    assert span_id == expected_span_id

    ctracing.init_parent("00000000000000000000000000000000", "0000000000000000")
    _check_initial_state()


def test_init_parent_from_env():

    _check_initial_state()

    expected_trace_id = "0000000000000000000000000000000a"
    expected_span_id = "000000000000000b"
    with mock.patch.dict(os.environ, {"TRACEPARENT": f"00-{expected_trace_id}-{expected_span_id}-01"}):
        ctracing.init_parent_from_env()
    (trace_id, span_id) = ctracing.get_span_hex_context()
    assert trace_id == expected_trace_id
    assert span_id == expected_span_id

    ctracing.init_parent("00000000000000000000000000000000", "0000000000000000")
    _check_initial_state()
