# env/snake.py — 뱀 위치와 이동. 길이 1 고정 (단순화). agent/protocol을 import하지 않는다.

from __future__ import annotations

from typing import Literal

import config
from env.grid import Pos

Action = Literal["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
ACTIONS: tuple[Action, ...] = ("UP", "DOWN", "LEFT", "RIGHT", "STAY")

# 행동 → (dr, dc)
_DELTA: dict[str, tuple[int, int]] = {
    "UP":    (-1,  0),
    "DOWN":  ( 1,  0),
    "LEFT":  ( 0, -1),
    "RIGHT": ( 0,  1),
    "STAY":  ( 0,  0),
}


class Snake:
    """
    뱀 상태 (길이 1 고정).
    이동은 격자 안에서만 유효하다. 격자 밖으로 나가는 이동은 제자리 유지 + invalid_move=True.
    """

    def __init__(self, start: Pos | None = None) -> None:
        # 기본 시작 위치: 안전 구역 중앙
        if start is None:
            mid = (config.SAFE_ZONE_MIN + config.SAFE_ZONE_MAX) // 2
            start = Pos(mid, mid)
        self.pos: Pos = start

    def move(self, action: Action) -> tuple[Pos, bool]:
        """
        행동을 적용해 새 위치를 계산한다.
        반환: (new_pos, invalid_move)
          - invalid_move=True  : 격자 밖 → 제자리 유지
          - invalid_move=False : 정상 이동
        """
        dr, dc = _DELTA[action]
        n = config.GRID_SIZE
        nr, nc = self.pos.r + dr, self.pos.c + dc

        if not (0 <= nr < n and 0 <= nc < n):
            # 격자 밖 — 제자리
            return self.pos, True

        self.pos = Pos(nr, nc)
        return self.pos, False

    def reset(self, start: Pos | None = None) -> None:
        """뱀을 시작 위치로 리셋한다."""
        if start is None:
            mid = (config.SAFE_ZONE_MIN + config.SAFE_ZONE_MAX) // 2
            start = Pos(mid, mid)
        self.pos = start
