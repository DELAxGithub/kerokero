"""Tests for topic loading and display."""

import json
from unittest.mock import patch

from kerokero.main import pick_topic, display_topic, TOPICS_PATH


class TestPickTopic:
    def test_returns_dict_with_required_keys(self):
        topic = pick_topic()
        assert isinstance(topic, dict)
        assert "id" in topic
        assert "topic" in topic
        assert "prompt" in topic
        assert "suggested_angles" in topic

    def test_topics_file_is_valid_json(self):
        with open(TOPICS_PATH) as f:
            topics = json.load(f)
        assert isinstance(topics, list)
        assert len(topics) > 0

    def test_all_topics_have_required_fields(self):
        with open(TOPICS_PATH) as f:
            topics = json.load(f)
        for t in topics:
            assert "id" in t, f"Missing id in topic: {t}"
            assert "topic" in t, f"Missing topic in: {t['id']}"
            assert "prompt" in t, f"Missing prompt in: {t['id']}"
            assert "suggested_angles" in t, f"Missing suggested_angles in: {t['id']}"
            assert len(t["suggested_angles"]) >= 1


class TestDisplayTopic:
    def test_display_does_not_crash(self, capsys):
        topic = {
            "id": "test-001",
            "topic": "Test Topic",
            "prompt": "Describe something.",
            "suggested_angles": ["angle 1", "angle 2"],
        }
        display_topic(topic)
