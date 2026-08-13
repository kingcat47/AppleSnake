# protocol/conditions.py — 실험 조건 데이터클래스 + 조건 매트릭스 생성.
# Spec §5 기반.

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Literal


@dataclass(frozen=True)
class Condition:
    """실험 조건 1개. Spec §5 필드 정의."""

    boundary_info: Literal["none", "hint", "explicit"]
    penalty: Literal["none", "score", "terminate"]
    question_style: Literal["open", "direct"] | None
    framing: Literal["explicit", "narrative"]
    protocol_mode: Literal["interrogation", "declaration", "both"] | None
    model: str


def pilot_set(model: str) -> list[Condition]:
    """
    Phase 3 파일럿용 조건 목록.
    심문/선언 없이 boundary_info(3) x framing(2) = 6개 조건.
    penalty=none, question_style=None, protocol_mode=None 고정.
    """
    conditions = []
    for bi, fr in product(
        ("none", "hint", "explicit"),
        ("explicit", "narrative"),
    ):
        conditions.append(Condition(
            boundary_info=bi,
            penalty="none",
            question_style=None,
            framing=fr,
            protocol_mode=None,
            model=model,
        ))
    return conditions


def main_set(models: list[str]) -> list[Condition]:
    """
    Phase 4 본 실험용 조건 목록 (부분요인설계).
    Spec §5: 전체 매트릭스 3x3x2x2x3 = 108 조건 x 모델 수.

    부분요인설계:
      - boundary_info(3) x penalty(3) x protocol_mode(3) = 27 조건/모델
      - framing은 explicit 고정 (pilot에서 비교 완료)
      - question_style은 protocol_mode에 따라 자동 결정:
        - declaration -> None (심문 없음)
        - interrogation/both -> direct
    """
    conditions = []
    for model in models:
        for bi, pen, pm in product(
            ("none", "hint", "explicit"),
            ("none", "score", "terminate"),
            ("interrogation", "declaration", "both"),
        ):
            # question_style 자동 결정
            if pm == "declaration":
                qs = None
            else:
                qs = "direct"

            conditions.append(Condition(
                boundary_info=bi,
                penalty=pen,
                question_style=qs,
                framing="explicit",
                protocol_mode=pm,
                model=model,
            ))
    return conditions
