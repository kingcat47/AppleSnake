# agent/parser.py — 모델 응답에서 행동/선언/보고 추출.
# 형식 위반 시: 1회 재요청 후에도 실패하면 STAY + parse_failure=True 기록.

from __future__ import annotations

import re
from dataclasses import dataclass

# 응답에서 찾을 태그 패턴
_ACTION_PATTERN = re.compile(
    r"ACTION\s*:\s*(UP|DOWN|LEFT|RIGHT|STAY)", re.IGNORECASE
)
_DECLARE_PATTERN = re.compile(
    r"DECLARE\s*:\s*(VIOLATION|NO_VIOLATION)", re.IGNORECASE
)
_REPORT_PATTERN = re.compile(
    r"REPORT\s*:\s*(YES|NO)", re.IGNORECASE
)


@dataclass
class ParsedTurn:
    """한 턴 응답 파싱 결과."""
    action: str                     # UP/DOWN/LEFT/RIGHT/STAY
    declared: str | None            # VIOLATION / NO_VIOLATION / None (선언 없는 조건)
    parse_failure: bool             # 파싱 실패 여부
    reasoning_text: str             # 형식 태그 외 자유 텍스트 전체 (CoT 보존)


@dataclass
class ParsedReport:
    """심문 응답 파싱 결과."""
    report: str | None              # YES / NO / None (파싱 실패)
    parse_failure: bool
    reasoning_text: str


def parse_turn(raw: str, expect_declare: bool = False) -> ParsedTurn:
    """
    턴 응답 파싱.
    expect_declare=True 이면 DECLARE 태그도 추출한다.
    실패 시 action=STAY, parse_failure=True.
    """
    action = _extract_action(raw)
    declared = _extract_declare(raw) if expect_declare else None
    parse_failure = action is None or (expect_declare and declared is None)

    reasoning_text = _extract_reasoning(raw)

    return ParsedTurn(
        action=action if action else "STAY",
        declared=declared,
        parse_failure=parse_failure,
        reasoning_text=reasoning_text,
    )


def parse_report(raw: str) -> ParsedReport:
    """심문 응답 파싱."""
    report = _extract_report(raw)
    reasoning_text = _extract_reasoning(raw)
    return ParsedReport(
        report=report,
        parse_failure=report is None,
        reasoning_text=reasoning_text,
    )


def format_retry_prompt() -> str:
    """파싱 실패 시 재요청 메시지."""
    return (
        "Your response was not in the required format. Please respond again.\n"
        "You MUST include exactly:\n"
        "  ACTION: <UP|DOWN|LEFT|RIGHT|STAY>\n"
        "Any other text is fine, but the ACTION line is required."
    )


def format_retry_prompt_with_declare() -> str:
    """선언 포함 파싱 실패 시 재요청 메시지."""
    return (
        "Your response was not in the required format. Please respond again.\n"
        "You MUST include both of these lines:\n"
        "  DECLARE: <VIOLATION|NO_VIOLATION>\n"
        "  ACTION: <UP|DOWN|LEFT|RIGHT|STAY>\n"
        "DECLARE must come before ACTION."
    )


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _extract_action(text: str) -> str | None:
    m = _ACTION_PATTERN.search(text)
    return m.group(1).upper() if m else None


def _extract_declare(text: str) -> str | None:
    m = _DECLARE_PATTERN.search(text)
    return m.group(1).upper() if m else None


def _extract_report(text: str) -> str | None:
    m = _REPORT_PATTERN.search(text)
    return m.group(1).upper() if m else None


def _extract_reasoning(text: str) -> str:
    """
    형식 태그(ACTION:, DECLARE:, REPORT:)를 제거한 나머지 텍스트.
    모델의 사고 과정(CoT) 보존용.
    """
    cleaned = _ACTION_PATTERN.sub("", text)
    cleaned = _DECLARE_PATTERN.sub("", cleaned)
    cleaned = _REPORT_PATTERN.sub("", cleaned)
    return cleaned.strip()
