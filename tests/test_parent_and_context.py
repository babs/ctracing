#!/usr/bin/env python3
import os
from unittest import mock

import ctracing

tracer = ctracing.init_tracer("test-ctracing")


def _check_initial_state():
    (trace_id, span_id) = ctracing.get_span_hex_context()
    assert trace_id == "00000000000000000000000000000000"
    assert span_id == "0000000000000000"


def test_get_span_hex_context():
    v = ctracing.get_span_hex_context()
    assert v == ("00000000000000000000000000000000", "0000000000000000")


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


def test_init_parent_from_traceparent():
    _check_initial_state()

    expected_trace_id = "0000000000000000000000000000000c"
    expected_span_id = "000000000000000d"
    init_result = ctracing.init_parent_from_traceparent(f"00-{expected_trace_id}-{expected_span_id}-01")
    (trace_id, span_id) = ctracing.get_span_hex_context()
    assert init_result is True
    assert trace_id == expected_trace_id
    assert span_id == expected_span_id

    init_result = ctracing.init_parent_from_traceparent("")
    assert init_result is False
    assert trace_id == expected_trace_id
    assert span_id == expected_span_id

    ctracing.init_parent("00000000000000000000000000000000", "0000000000000000")
    _check_initial_state()
