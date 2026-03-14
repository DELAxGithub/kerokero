"""Tests for evaluation functions (Claude calls mocked)."""

import json
from unittest.mock import patch

from kerokero.main import evaluate_test, evaluate_structure, display_evaluation, display_structure_result


MOCK_TEST_EVAL = {
    "overall_band": 6.5,
    "scores": {
        "fluency_coherence": 6.0,
        "lexical_resource": 7.0,
        "grammatical_range": 6.5,
        "pronunciation_estimate": 6.5,
    },
    "strengths": ["Good vocabulary", "Clear structure"],
    "weaknesses": ["Some hesitation"],
    "corrected_version_en": "A better version.",
    "corrected_version": "より良いバージョン。",
    "specific_improvements": [
        {"original": "very good", "improved": "exceptionally good", "reason": "より具体的"}
    ],
    "examiner_comment": "まずまずの回答です。",
}

MOCK_STRUCTURE_EVAL = {
    "content_score": 7.0,
    "scores": {"topic_coverage": 7, "idea_development": 7, "logical_flow": 7, "completeness": 7},
    "feedback": "良い構成です。",
    "suggested_outline_en": "Start with...",
    "key_phrases_en": ["in terms of", "what struck me", "looking back"],
    "gate_pass": True,
}


class TestEvaluateTest:
    def test_calls_claude_and_parses(self):
        with patch("kerokero.main.call_claude", return_value=json.dumps(MOCK_TEST_EVAL)):
            result = evaluate_test("Describe something", "My answer here", "ja")

        assert result["overall_band"] == 6.5
        assert len(result["strengths"]) == 2

    def test_includes_duration_info(self):
        with patch("kerokero.main.call_claude", return_value=json.dumps(MOCK_TEST_EVAL)) as mock:
            evaluate_test("Topic", "Transcript", "ja", duration=95.0)

        call_args = mock.call_args[0]
        assert "95 seconds" in call_args[1]

    def test_includes_key_phrases(self):
        with patch("kerokero.main.call_claude", return_value=json.dumps(MOCK_TEST_EVAL)) as mock:
            evaluate_test("Topic", "Transcript", "ja", key_phrases=["phrase A", "phrase B"])

        call_args = mock.call_args[0]
        assert "phrase A" in call_args[1]
        assert "phrase B" in call_args[1]


class TestEvaluateStructure:
    def test_calls_claude_and_parses(self):
        with patch("kerokero.main.call_claude", return_value=json.dumps(MOCK_STRUCTURE_EVAL)):
            result = evaluate_structure("Describe something", "日本語プラン", "ja")

        assert result["content_score"] == 7.0
        assert result["gate_pass"] is True


class TestDisplayEvaluation:
    def test_display_full_evaluation(self):
        display_evaluation(MOCK_TEST_EVAL)

    def test_display_minimal_evaluation(self):
        minimal = {
            "overall_band": 5.0,
            "scores": {
                "fluency_coherence": 5.0,
                "lexical_resource": 5.0,
                "grammatical_range": 5.0,
                "pronunciation_estimate": 5.0,
            },
            "strengths": [],
            "weaknesses": [],
        }
        display_evaluation(minimal)


class TestDisplayStructureResult:
    def test_display_pass(self):
        display_structure_result(MOCK_STRUCTURE_EVAL)

    def test_display_fail(self):
        fail_eval = {**MOCK_STRUCTURE_EVAL, "content_score": 4.0, "gate_pass": False}
        display_structure_result(fail_eval)
