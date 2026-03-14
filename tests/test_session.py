"""Tests for session saving."""

import json
from pathlib import Path
from unittest.mock import patch

from kerokero.main import save_test_session, save_practice_session


class TestSaveTestSession:
    def test_saves_valid_json(self, tmp_path):
        sessions_dir = tmp_path / "sessions"

        topic = {"id": "t-001", "topic": "Test", "prompt": "Describe test."}
        transcript = "This is my answer about testing."
        evaluation = {"overall_band": 6.5, "scores": {}}
        audio_path = tmp_path / "audio.wav"

        with patch("kerokero.main.SESSIONS_DIR", sessions_dir):
            save_test_session(topic, transcript, evaluation, 45.2, audio_path)

        files = list(sessions_dir.glob("*.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["mode"] == "test"
        assert data["topic_id"] == "t-001"
        assert data["transcript"] == transcript
        assert data["duration_seconds"] == 45.2
        assert data["evaluation"]["overall_band"] == 6.5


class TestSavePracticeSession:
    def test_saves_both_stages(self, tmp_path):
        sessions_dir = tmp_path / "sessions"

        topic = {"id": "t-002", "topic": "Practice", "prompt": "Describe practice."}
        s_eval = {"content_score": 7.0, "scores": {}, "key_phrases_en": ["phrase"], "gate_pass": True}
        p_eval = {"overall_band": 6.0, "scores": {}}

        with patch("kerokero.main.SESSIONS_DIR", sessions_dir):
            save_practice_session(
                topic, s_eval, "日本語のプラン", 30.0,
                p_eval, "English production", 90.0,
                tmp_path / "s1.wav", tmp_path / "s3.wav",
            )

        files = list(sessions_dir.glob("*_practice.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["mode"] == "practice"
        assert data["stages"]["structure"]["transcript_l1"] == "日本語のプラン"
        assert data["stages"]["production"]["transcript_en"] == "English production"
        assert data["stages"]["structure"]["key_phrases_en"] == ["phrase"]
