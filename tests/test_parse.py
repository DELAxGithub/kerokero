"""Tests for JSON parsing utilities."""

import pytest

from kerokero.main import parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        raw = '{"overall_band": 6.5, "scores": {"fluency_coherence": 6.0}}'
        result = parse_json_response(raw)
        assert result["overall_band"] == 6.5
        assert result["scores"]["fluency_coherence"] == 6.0

    def test_json_with_markdown_fence(self):
        raw = 'Here is my evaluation:\n```json\n{"overall_band": 7.0}\n```\nDone.'
        result = parse_json_response(raw)
        assert result["overall_band"] == 7.0

    def test_json_with_plain_fence(self):
        raw = '```\n{"overall_band": 5.5}\n```'
        result = parse_json_response(raw)
        assert result["overall_band"] == 5.5

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_json_response("not json at all")

    def test_nested_json(self):
        raw = '```json\n{"scores": {"a": 1, "b": 2}, "list": [1, 2, 3]}\n```'
        result = parse_json_response(raw)
        assert result["list"] == [1, 2, 3]

    def test_empty_json_object(self):
        result = parse_json_response("{}")
        assert result == {}
