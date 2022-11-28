#!/usr/bin/env python3
import json
import os

import requests_mock
from opentelemetry.sdk.trace.export import SpanExportResult

import ctracing

URL = "mock://localhost/log"
msg = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "simple-msg.json")))


def test_basichttpspanexporter_basic():
    rebuilt_span = ctracing.convert_message_to_span(msg)
    with requests_mock.mock() as m:
        m.post(URL)
        bhse = ctracing.BasicHttpSpanExporter(endpoint=URL)
        bhse.export([rebuilt_span])

    assert m.called is True
    assert m.last_request.url is URL
    value_received = m.last_request.json()
    value_received["_id"] = msg["_id"]
    assert value_received == msg


def test_basichttpspanexporter_http_error():
    rebuilt_span = ctracing.convert_message_to_span(msg)
    with requests_mock.mock() as m:
        m.post(URL, status_code=500)
        bhse = ctracing.BasicHttpSpanExporter(endpoint=URL)
        call_result = bhse.export([rebuilt_span])

    assert m.called is True
    assert call_result is SpanExportResult.FAILURE


def test_callbackspanexporter_shutdown_returns_none():
    bhse = ctracing.BasicHttpSpanExporter(endpoint=URL)
    assert bhse.shutdown() is None


def test_callbackspanexporter_force_flush():
    bhse = ctracing.BasicHttpSpanExporter(endpoint=URL)
    assert bhse.force_flush() is True
