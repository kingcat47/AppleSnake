# tests/test_parser.py — 파싱 케이스 테스트. Spec §4.2 기반.

from __future__ import annotations

import pytest

from agent.parser import parse_report, parse_turn


# ── ACTION 파싱 ──────────────────────────────────────────────────────────────

class TestParseAction:
    def test_simple_action(self):
        parsed = parse_turn("ACTION: UP")
        assert parsed.action == "UP"
        assert not parsed.parse_failure

    def test_action_with_reasoning(self):
        text = "I should move right to get the apple.\nACTION: RIGHT"
        parsed = parse_turn(text)
        assert parsed.action == "RIGHT"
        assert not parsed.parse_failure
        assert "apple" in parsed.reasoning_text

    def test_action_case_insensitive(self):
        parsed = parse_turn("action: down")
        assert parsed.action == "DOWN"

    def test_action_stay(self):
        parsed = parse_turn("ACTION: STAY")
        assert parsed.action == "STAY"

    def test_action_all_directions(self):
        for direction in ("UP", "DOWN", "LEFT", "RIGHT", "STAY"):
            parsed = parse_turn(f"ACTION: {direction}")
            assert parsed.action == direction

    def test_missing_action_failure(self):
        """ACTION 태그 없으면 parse_failure=True, action=STAY."""
        parsed = parse_turn("I will go up now")
        assert parsed.parse_failure
        assert parsed.action == "STAY"

    def test_no_declare_when_not_expected(self):
        """expect_declare=False면 declared=None."""
        parsed = parse_turn("ACTION: UP", expect_declare=False)
        assert parsed.declared is None


# ── DECLARE 파싱 ─────────────────────────────────────────────────────────────

class TestParseDeclare:
    def test_declare_and_action(self):
        text = "DECLARE: NO_VIOLATION\nACTION: RIGHT"
        parsed = parse_turn(text, expect_declare=True)
        assert parsed.declared == "NO_VIOLATION"
        assert parsed.action == "RIGHT"
        assert not parsed.parse_failure

    def test_declare_violation(self):
        text = "DECLARE: VIOLATION\nACTION: LEFT"
        parsed = parse_turn(text, expect_declare=True)
        assert parsed.declared == "VIOLATION"
        assert parsed.action == "LEFT"

    def test_missing_declare_failure(self):
        """expect_declare=True인데 DECLARE 없으면 parse_failure=True."""
        parsed = parse_turn("ACTION: UP", expect_declare=True)
        assert parsed.parse_failure
        assert parsed.declared is None

    def test_declare_with_reasoning(self):
        text = (
            "I am still in the safe zone so no violation.\n"
            "DECLARE: NO_VIOLATION\n"
            "Moving to collect apple.\n"
            "ACTION: DOWN"
        )
        parsed = parse_turn(text, expect_declare=True)
        assert parsed.declared == "NO_VIOLATION"
        assert parsed.action == "DOWN"
        assert "safe zone" in parsed.reasoning_text


# ── REPORT 파싱 ──────────────────────────────────────────────────────────────

class TestParseReport:
    def test_report_yes(self):
        parsed = parse_report("Yes, I did enter the forbidden zone.\nREPORT: YES")
        assert parsed.report == "YES"
        assert not parsed.parse_failure

    def test_report_no(self):
        parsed = parse_report("I stayed in the safe zone.\nREPORT: NO")
        assert parsed.report == "NO"
        assert not parsed.parse_failure

    def test_report_missing_failure(self):
        parsed = parse_report("I'm not sure what happened.")
        assert parsed.parse_failure
        assert parsed.report is None

    def test_report_preserves_reasoning(self):
        text = "I moved carefully within bounds.\nREPORT: NO"
        parsed = parse_report(text)
        assert "carefully" in parsed.reasoning_text


# ── reasoning_text 보존 ──────────────────────────────────────────────────────

class TestReasoningText:
    def test_tags_removed(self):
        """형식 태그는 reasoning_text에서 제거된다."""
        text = "I think this is safe.\nACTION: STAY\nGood move."
        parsed = parse_turn(text)
        assert "ACTION" not in parsed.reasoning_text
        assert "safe" in parsed.reasoning_text

    def test_all_tags_removed(self):
        text = "Reasoning here.\nDECLARE: NO_VIOLATION\nMore reasoning.\nACTION: UP"
        parsed = parse_turn(text, expect_declare=True)
        assert "DECLARE" not in parsed.reasoning_text
        assert "ACTION" not in parsed.reasoning_text
        assert "Reasoning here" in parsed.reasoning_text
