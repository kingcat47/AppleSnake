# env/grid.py — 격자 좌표계, 구역 정의, 셀 조회. agent/protocol을 import하지 않는다.

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import NamedTuple

import config


class Pos(NamedTuple):
    """격자 좌표. r=행(위→아래), c=열(왼→오른)."""
    r: int
    c: int


def zone_of(pos: Pos) -> int:
    """
    좌표의 구역 번호를 반환한다.
      0 — 안전 구역  : SAFE_ZONE_MIN <= r,c <= SAFE_ZONE_MAX (중앙 3×3)
      1 — 얕은 금지  : 그 바깥, 테두리 한 겹 제외
      2 — 깊은 금지  : x∈{0, GRID_SIZE-1} 또는 y∈{0, GRID_SIZE-1} (테두리)
    격자 밖 좌표는 ValueError.
    """
    r, c = pos
    n = config.GRID_SIZE
    if not (0 <= r < n and 0 <= c < n):
        raise ValueError(f"좌표 {pos}가 격자 밖입니다 (GRID_SIZE={n})")

    # 깊은 금지: 테두리 한 겹
    if r == 0 or r == n - 1 or c == 0 or c == n - 1:
        return 2

    # 안전 구역: 중앙 3×3
    mn, mx = config.SAFE_ZONE_MIN, config.SAFE_ZONE_MAX
    if mn <= r <= mx and mn <= c <= mx:
        return 0

    # 그 사이: 얕은 금지
    return 1


def all_cells() -> list[Pos]:
    """격자 내 모든 좌표 목록."""
    n = config.GRID_SIZE
    return [Pos(r, c) for r in range(n) for c in range(n)]


def cells_of_zone(z: int) -> list[Pos]:
    """특정 zone에 속하는 모든 좌표 목록."""
    return [p for p in all_cells() if zone_of(p) == z]


@dataclass
class Grid:
    """
    격자 상태: 구역 정의 + 사과 위치 관리.
    사과는 구역별 목표 수를 항상 유지한다 (먹히면 즉시 재생성).
    """

    # 구역별 사과 집합: {zone: set[Pos]}
    apples: dict[int, set[Pos]] = field(default_factory=dict)

    # RNG — smoke 테스트에서 seed 고정 가능하도록 분리
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        # 각 구역에 초기 사과 배치
        for z, count in _apple_targets().items():
            self.apples[z] = set()
            self._fill_zone(z, count, occupied=set())

    def _apple_targets(self) -> dict[int, int]:
        return _apple_targets()

    def _fill_zone(self, zone: int, count: int, occupied: set[Pos]) -> None:
        """zone에 사과가 count개 될 때까지 빈 셀에 배치한다."""
        candidates = [p for p in cells_of_zone(zone) if p not in occupied and p not in self.apples[zone]]
        needed = count - len(self.apples[zone])
        if needed <= 0:
            return
        if len(candidates) < needed:
            # 셀이 부족하면 가능한 만큼만 배치 (극단적 상황 방어)
            needed = len(candidates)
        chosen = self.rng.sample(candidates, needed)
        self.apples[zone].update(chosen)

    def apple_zone_at(self, pos: Pos) -> int | None:
        """pos에 사과가 있으면 그 zone을 반환, 없으면 None."""
        for z, s in self.apples.items():
            if pos in s:
                return z
        return None

    def eat_apple(self, pos: Pos, snake_pos: Pos) -> int | None:
        """
        pos의 사과를 제거하고 재생성한다.
        반환값: 먹은 사과의 zone (없으면 None).
        snake_pos는 재생성 시 뱀 위치를 제외하기 위해 받는다.
        """
        eaten_zone = self.apple_zone_at(pos)
        if eaten_zone is None:
            return None

        self.apples[eaten_zone].discard(pos)
        # 재생성: 뱀 위치 + 기존 사과 위치 제외
        occupied = {snake_pos} | {p for s in self.apples.values() for p in s}
        self._fill_zone(eaten_zone, _apple_targets()[eaten_zone], occupied)
        return eaten_zone

    def all_apple_positions(self) -> dict[int, list[Pos]]:
        """구역별 사과 좌표 목록 (렌더용)."""
        return {z: list(s) for z, s in self.apples.items()}

    def reset(self, seed: int | None = None) -> None:
        """격자를 초기 상태로 리셋한다."""
        if seed is not None:
            self.rng.seed(seed)
        self.apples = {}
        for z, count in _apple_targets().items():
            self.apples[z] = set()
            self._fill_zone(z, count, occupied=set())


def _apple_targets() -> dict[int, int]:
    return {
        0: config.APPLE_COUNT_ZONE0,
        1: config.APPLE_COUNT_ZONE1,
        2: config.APPLE_COUNT_ZONE2,
    }
