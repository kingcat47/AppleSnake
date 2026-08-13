# protocol/conditions.py — 실험 조건 데이터클래스 + 조건 매트릭스 생성.
# 설계 v2: boundary_info 축 제거, monitoring_awareness 축 추가.

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Literal


@dataclass(frozen=True)
class Condition:
    """실험 조건 1개."""

    monitoring_awareness: Literal["off", "on"]
    penalty: Literal["none", "score", "terminate"]
    question_style: Literal["open", "direct"] | None
    framing: Literal["explicit", "narrative"]
    protocol_mode: Literal["interrogation", "declaration", "both"] | None
    model: str


def pilot_set(model: str) -> list[Condition]:
    """
    파일럿용 조건 목록.
    심문/선언 없이 monitoring_awareness(2) x framing(2) = 4개 조건.
    penalty=none, question_style=None, protocol_mode=None 고정.
    """
    conditions = []
    for mon, fr in product(
        ("off", "on"),
        ("explicit", "narrative"),
    ):
        conditions.append(Condition(
            monitoring_awareness=mon,
            penalty="none",
            question_style=None,
            framing=fr,
            protocol_mode=None,
            model=model,
        ))
    return conditions


def main_set(models: list[str]) -> list[Condition]:
    """
    본 실험용 조건 목록.
    monitoring_awareness(2) x penalty(3) x protocol_mode(3) = 18 조건/모델.
    framing은 explicit 고정.
    question_style은 protocol_mode에 따라 자동 결정:
      - declaration -> None (심문 없음)
      - interrogation/both -> direct

    baseline 조건: monitoring_awareness=off, penalty=none
    대조군: monitoring on 또는 penalty score/terminate
    """
    conditions = []
    for model in models:
        for mon, pen, pm in product(
            ("off", "on"),
            ("none", "score", "terminate"),
            ("interrogation", "declaration", "both"),
        ):
            # question_style 자동 결정
            if pm == "declaration":
                qs = None
            else:
                qs = "direct"

            conditions.append(Condition(
                monitoring_awareness=mon,
                penalty=pen,
                question_style=qs,
                framing="explicit",
                protocol_mode=pm,
                model=model,
            ))
    return conditions
