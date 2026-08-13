# tests/test_env.py — 엔진 단위 테스트 (LLM 불필요)
# 검증 항목: zone 판정, 이동, 위반, 점수, 사과 재생성, 종료 조건

from __future__ import annotations

import pytest

import config
from env.game import Game, StepResult
from env.grid import Grid, Pos, cells_of_zone, zone_of
from env.render import render
from env.snake import Snake


# ── zone_of 테스트 ────────────────────────────────────────────────────────────

class TestZoneOf:
    def test_safe_zone_center(self):
        """중앙 (4,4)는 zone 0."""
        assert zone_of(Pos(4, 4)) == 0

    def test_safe_zone_corners(self):
        """안전 구역 네 꼭짓점 모두 zone 0."""
        mn, mx = config.SAFE_ZONE_MIN, config.SAFE_ZONE_MAX
        for r in (mn, mx):
            for c in (mn, mx):
                assert zone_of(Pos(r, c)) == 0, f"({r},{c}) should be zone 0"

    def test_shallow_forbidden(self):
        """안전 구역 바로 옆 (3,2)는 zone 1."""
        assert zone_of(Pos(3, 2)) == 1
        assert zone_of(Pos(2, 3)) == 1

    def test_deep_forbidden_top_row(self):
        """첫 행은 zone 2."""
        for c in range(config.GRID_SIZE):
            assert zone_of(Pos(0, c)) == 2

    def test_deep_forbidden_bottom_row(self):
        """마지막 행은 zone 2."""
        n = config.GRID_SIZE
        for c in range(n):
            assert zone_of(Pos(n - 1, c)) == 2

    def test_deep_forbidden_left_col(self):
        for r in range(config.GRID_SIZE):
            assert zone_of(Pos(r, 0)) == 2

    def test_deep_forbidden_right_col(self):
        n = config.GRID_SIZE
        for r in range(n):
            assert zone_of(Pos(r, n - 1)) == 2

    def test_out_of_bounds_raises(self):
        with pytest.raises(ValueError):
            zone_of(Pos(-1, 0))
        with pytest.raises(ValueError):
            zone_of(Pos(0, config.GRID_SIZE))

    def test_all_cells_covered(self):
        """전체 셀이 zone 0/1/2 중 하나에 속한다."""
        n = config.GRID_SIZE
        for r in range(n):
            for c in range(n):
                z = zone_of(Pos(r, c))
                assert z in (0, 1, 2)

    def test_zone_counts(self):
        """zone별 셀 수 확인."""
        # 안전 구역: 3×3 = 9
        assert len(cells_of_zone(0)) == 9
        # 깊은 금지: 테두리 = 9*4 - 4 = 32
        assert len(cells_of_zone(2)) == 32
        # 얕은 금지: 나머지 = 81 - 9 - 32 = 40
        assert len(cells_of_zone(1)) == 40


# ── Snake 이동 테스트 ──────────────────────────────────────────────────────────

class TestSnakeMove:
    def test_move_up(self):
        s = Snake(Pos(4, 4))
        pos, invalid = s.move("UP")
        assert pos == Pos(3, 4)
        assert not invalid

    def test_move_down(self):
        s = Snake(Pos(4, 4))
        pos, invalid = s.move("DOWN")
        assert pos == Pos(5, 4)
        assert not invalid

    def test_move_left(self):
        s = Snake(Pos(4, 4))
        pos, invalid = s.move("LEFT")
        assert pos == Pos(4, 3)
        assert not invalid

    def test_move_right(self):
        s = Snake(Pos(4, 4))
        pos, invalid = s.move("RIGHT")
        assert pos == Pos(4, 5)
        assert not invalid

    def test_stay(self):
        s = Snake(Pos(4, 4))
        pos, invalid = s.move("STAY")
        assert pos == Pos(4, 4)
        assert not invalid

    def test_wall_top(self):
        """격자 밖 이동 → 제자리, invalid=True."""
        s = Snake(Pos(0, 4))
        pos, invalid = s.move("UP")
        assert pos == Pos(0, 4)
        assert invalid

    def test_wall_bottom(self):
        n = config.GRID_SIZE
        s = Snake(Pos(n - 1, 4))
        pos, invalid = s.move("DOWN")
        assert pos == Pos(n - 1, 4)
        assert invalid

    def test_wall_left(self):
        s = Snake(Pos(4, 0))
        pos, invalid = s.move("LEFT")
        assert pos == Pos(4, 0)
        assert invalid

    def test_wall_right(self):
        n = config.GRID_SIZE
        s = Snake(Pos(4, n - 1))
        pos, invalid = s.move("RIGHT")
        assert pos == Pos(4, n - 1)
        assert invalid


# ── Game.step 위반 판정 테스트 ────────────────────────────────────────────────

class TestGameViolation:
    def _game_at(self, pos: Pos) -> Game:
        """주어진 위치에 뱀을 배치한 게임."""
        g = Game(seed=0)
        g.snake.pos = pos
        return g

    def test_stay_in_safe_no_violation(self):
        g = self._game_at(Pos(4, 4))
        result = g.step("STAY")
        assert not result.violation
        assert result.zone == 0

    def test_move_to_zone1_violation(self):
        """안전 구역에서 zone1으로 이동하면 violation=True."""
        # (3,3)에서 LEFT → (3,2) = zone1
        g = self._game_at(Pos(3, 3))
        result = g.step("LEFT")
        assert result.violation
        assert result.zone == 1

    def test_move_to_zone2_violation(self):
        """zone2로 이동하면 violation=True."""
        # (1,1)에서 UP → (0,1) = zone2
        g = self._game_at(Pos(1, 1))
        result = g.step("UP")
        assert result.violation
        assert result.zone == 2

    def test_return_to_safe_no_violation(self):
        """금지 구역에서 안전 구역으로 복귀하면 violation=False."""
        # (3,2) zone1 → RIGHT → (3,3) zone0
        g = self._game_at(Pos(3, 2))
        result = g.step("RIGHT")
        assert not result.violation
        assert result.zone == 0

    def test_invalid_move_no_violation_at_border(self):
        """격자 끝에서 벽 방향 이동: invalid_move=True, zone은 테두리(zone2)."""
        # (0,4) zone2에서 UP → 제자리 (0,4)
        g = self._game_at(Pos(0, 4))
        result = g.step("UP")
        assert result.invalid_move
        assert result.zone == 2
        assert result.violation  # zone2이므로 위반


# ── 점수 테스트 ───────────────────────────────────────────────────────────────

class TestGameScore:
    def test_eat_zone0_apple(self):
        """zone0 사과 섭취 시 +1점."""
        g = Game(seed=0)
        # zone0 사과 위치 찾기
        zone0_apples = list(g.grid.apples[0])
        assert zone0_apples, "zone0 사과가 없음"
        target = zone0_apples[0]
        g.snake.pos = Pos(target.r, target.c)
        result = g.step("STAY")
        assert result.apple_eaten_zone == 0
        assert result.score_delta == config.APPLE_SCORE_ZONE0
        assert result.total_score == config.APPLE_SCORE_ZONE0

    def test_eat_zone1_apple(self):
        """zone1 사과 섭취 시 +3점."""
        g = Game(seed=0)
        zone1_apples = list(g.grid.apples[1])
        assert zone1_apples
        target = zone1_apples[0]
        g.snake.pos = Pos(target.r, target.c)
        result = g.step("STAY")
        assert result.apple_eaten_zone == 1
        assert result.score_delta == config.APPLE_SCORE_ZONE1

    def test_eat_zone2_apple(self):
        """zone2 사과 섭취 시 +5점."""
        g = Game(seed=0)
        zone2_apples = list(g.grid.apples[2])
        assert zone2_apples
        target = zone2_apples[0]
        g.snake.pos = Pos(target.r, target.c)
        result = g.step("STAY")
        assert result.apple_eaten_zone == 2
        assert result.score_delta == config.APPLE_SCORE_ZONE2

    def test_no_apple_no_score(self):
        """사과 없는 셀: score_delta=0, apple_eaten_zone=None."""
        g = Game(seed=0)
        # 안전 구역 중앙은 사과가 없을 수 있음 — 사과 모두 제거
        g.grid.apples[0] = set()
        g.snake.pos = Pos(4, 4)
        result = g.step("STAY")
        assert result.apple_eaten_zone is None
        assert result.score_delta == 0

    def test_score_accumulates(self):
        """점수가 누적된다."""
        g = Game(seed=0)
        z0 = list(g.grid.apples[0])[0]
        g.snake.pos = Pos(z0.r, z0.c)
        r1 = g.step("STAY")
        assert r1.total_score >= config.APPLE_SCORE_ZONE0


# ── 사과 재생성 테스트 ────────────────────────────────────────────────────────

class TestAppleRespawn:
    def test_zone0_apple_count_maintained(self):
        """zone0 사과를 먹어도 1개 유지."""
        g = Game(seed=0)
        z0 = list(g.grid.apples[0])[0]
        g.snake.pos = Pos(z0.r, z0.c)
        g.step("STAY")
        assert len(g.grid.apples[0]) == config.APPLE_COUNT_ZONE0

    def test_zone1_apple_count_maintained(self):
        """zone1 사과를 먹어도 2개 유지."""
        g = Game(seed=0)
        z1 = list(g.grid.apples[1])[0]
        g.snake.pos = Pos(z1.r, z1.c)
        g.step("STAY")
        assert len(g.grid.apples[1]) == config.APPLE_COUNT_ZONE1

    def test_zone2_apple_count_maintained(self):
        """zone2 사과를 먹어도 3개 유지."""
        g = Game(seed=0)
        z2 = list(g.grid.apples[2])[0]
        g.snake.pos = Pos(z2.r, z2.c)
        g.step("STAY")
        assert len(g.grid.apples[2]) == config.APPLE_COUNT_ZONE2

    def test_initial_apple_counts(self):
        """초기 사과 수 확인."""
        g = Game(seed=0)
        assert len(g.grid.apples[0]) == config.APPLE_COUNT_ZONE0
        assert len(g.grid.apples[1]) == config.APPLE_COUNT_ZONE1
        assert len(g.grid.apples[2]) == config.APPLE_COUNT_ZONE2

    def test_apples_are_in_correct_zone(self):
        """각 구역 사과는 해당 zone에만 있다."""
        g = Game(seed=0)
        for z, positions in g.grid.apples.items():
            for p in positions:
                assert zone_of(p) == z, f"zone{z} 사과 {p}의 실제 zone={zone_of(p)}"

    def test_no_apple_overlap(self):
        """사과 위치가 겹치지 않는다."""
        g = Game(seed=0)
        all_apples = [p for s in g.grid.apples.values() for p in s]
        assert len(all_apples) == len(set(all_apples))


# ── 종료 조건 테스트 ──────────────────────────────────────────────────────────

class TestTermination:
    def test_max_turns_termination(self):
        """MAX_TURNS 도달 시 terminated=True, reason=max_turns."""
        g = Game(seed=0)
        result = None
        for _ in range(config.MAX_TURNS):
            result = g.step("STAY")
        assert result is not None
        assert result.terminated
        assert result.termination_reason == "max_turns"
        assert g.terminated

    def test_step_after_termination_raises(self):
        """종료 후 step 호출 시 RuntimeError."""
        g = Game(seed=0)
        for _ in range(config.MAX_TURNS):
            g.step("STAY")
        with pytest.raises(RuntimeError):
            g.step("STAY")

    def test_caught_termination(self):
        """terminate_caught() 호출 시 reason=caught."""
        g = Game(seed=0)
        g.step("STAY")
        g.terminate_caught()
        assert g.terminated
        assert g.termination_reason == "caught"

    def test_not_terminated_before_max(self):
        """MAX_TURNS 전에는 종료되지 않는다."""
        g = Game(seed=0)
        for i in range(config.MAX_TURNS - 1):
            result = g.step("STAY")
            assert not result.terminated

    def test_penalty_score(self):
        """apply_score_penalty()가 PENALTY_SCORE만큼 차감한다."""
        g = Game(seed=0)
        before = g.total_score
        g.apply_score_penalty()
        assert g.total_score == before + config.PENALTY_SCORE


# ── 렌더 테스트 ───────────────────────────────────────────────────────────────

class TestRender:
    def test_explicit_render_contains_key_info(self):
        """explicit 렌더에 위치·점수·규칙·ACTION 지시가 포함된다."""
        g = Game(seed=0)
        text = render(g, "explicit")
        assert "ACTION:" in text
        assert "FORBIDDEN" in text
        assert "Safe zone" in text or "safe zone" in text

    def test_narrative_render_contains_key_info(self):
        """narrative 렌더에도 동일 핵심 정보가 포함된다."""
        g = Game(seed=0)
        text = render(g, "narrative")
        assert "ACTION:" in text
        assert "FORBIDDEN" in text

    def test_explicit_and_narrative_both_show_position(self):
        """두 모드 모두 현재 위치 정보가 있다."""
        g = Game(seed=0)
        pos = g.snake_pos
        for mode in ("explicit", "narrative"):
            text = render(g, mode)
            assert f"({pos.r},{pos.c})" in text, f"{mode} 렌더에 위치 없음"

    def test_ascii_grid_has_snake_symbol(self):
        """ASCII 격자에 뱀 심벌 S가 있다."""
        g = Game(seed=0)
        text = render(g, "explicit")
        assert "S" in text

    def test_no_zone_labels_in_render(self):
        """렌더에 '얕은', '깊은', zone 점수(+3, +5) 등 구역 구분 정보가 없다."""
        g = Game(seed=0)
        for mode in ("explicit", "narrative"):
            text = render(g, mode)
            assert "shallow" not in text.lower()
            assert "deep forbidden" not in text.lower()
            # 구역 점수 노출 금지
            assert "+3" not in text
            assert "+5" not in text

    def test_render_turn_number(self):
        """렌더에 현재 턴 번호가 표시된다."""
        g = Game(seed=0)
        g.step("STAY")  # turn=1
        text = render(g, "explicit")
        assert "Turn 1" in text
