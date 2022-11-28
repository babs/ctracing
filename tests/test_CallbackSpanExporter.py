#!/usr/bin/env python3
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

import ctracing


def _callback_true(span: ReadableSpan) -> bool:
    return True


def _callback_false(span: ReadableSpan) -> bool:
    return False


def _callback_raise(span: ReadableSpan) -> bool:
    raise Exception()


def test_callbackspanexporter_handle_true():
    cbse = ctracing.CallbackSpanExporter(_callback_true)
    export_result = cbse.export([ReadableSpan()])
    assert export_result is SpanExportResult.SUCCESS


def test_callbackspanexporter_handle_false():
    cbse = ctracing.CallbackSpanExporter(_callback_false)
    export_result = cbse.export([ReadableSpan()])
    assert export_result is SpanExportResult.FAILURE


def test_callbackspanexporter_handle_exception():
    cbse = ctracing.CallbackSpanExporter(_callback_raise)
    export_result = cbse.export([ReadableSpan()])
    assert export_result is SpanExportResult.FAILURE


def test_callbackspanexporter_shutdown_returns_none():
    cbse = ctracing.CallbackSpanExporter(_callback_false)
    assert cbse.shutdown() is None


def test_callbackspanexporter_force_flush():
    cbse = ctracing.CallbackSpanExporter(_callback_false)
    assert cbse.force_flush() is True
