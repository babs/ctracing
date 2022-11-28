#!/usr/bin/env python3
import copy
import json
import os

import ctracing

simple_msg = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "simple-msg.json")))
more_complete_msg = json.load(
    open(os.path.join(os.path.dirname(__file__), "fixtures", "more-complete-msg.json"))
)
more_complete_msg_w_parentid = json.load(
    open(os.path.join(os.path.dirname(__file__), "fixtures", "more-complete-msg-parent-id.json"))
)


def test_double_convertion():
    span = ctracing.convert_message_to_span(simple_msg)
    regenerated = ctracing.convert_span_to_mesage(span)
    regenerated["_id"] = simple_msg["_id"]
    assert regenerated == simple_msg


def test_double_convertion_more_complete_msg():
    span = ctracing.convert_message_to_span(more_complete_msg)
    regenerated = ctracing.convert_span_to_mesage(span)
    regenerated["_id"] = more_complete_msg["_id"]
    assert regenerated == more_complete_msg


def test_double_double_convertion():
    span = ctracing.convert_message_to_span(more_complete_msg)
    regenerated = ctracing.convert_span_to_mesage(span)
    span = ctracing.convert_message_to_span(regenerated)
    regenerated = ctracing.convert_span_to_mesage(span)
    regenerated["_id"] = more_complete_msg["_id"]
    assert regenerated == more_complete_msg


def test_double_double_convertion_w_parentid():
    span = ctracing.convert_message_to_span(more_complete_msg_w_parentid)
    regenerated = ctracing.convert_span_to_mesage(span)
    span = ctracing.convert_message_to_span(regenerated)
    regenerated = ctracing.convert_span_to_mesage(span)
    regenerated["_id"] = more_complete_msg_w_parentid["_id"]
    assert regenerated == more_complete_msg_w_parentid


def test_convertion_invalid_kind():
    msg_default_kind = copy.deepcopy(more_complete_msg_w_parentid)
    msg_invalid_kind = copy.deepcopy(more_complete_msg_w_parentid)
    msg_invalid_kind["_span"]["kind"] = "invalid"
    span = ctracing.convert_message_to_span(msg_invalid_kind)
    regenerated = ctracing.convert_span_to_mesage(span)
    span = ctracing.convert_message_to_span(regenerated)
    regenerated = ctracing.convert_span_to_mesage(span)
    regenerated["_id"] = msg_invalid_kind["_id"]
    assert regenerated == msg_default_kind
