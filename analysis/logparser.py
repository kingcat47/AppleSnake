# analysis/logparser.py — logs/ 의 JSON 읽기/검증.
# Spec §8 분석의 기반. 하위 폴더를 재귀 탐색하여 에피소드 로그를 로드한다.

from __future__ import annotations

import json
from pathlib import Path

import config


def load_all_episodes(logs_dir: str | Path | None = None) -> list[dict]:
    """
    logs 디렉터리(하위 폴더 포함)에서 모든 에피소드 JSON을 로드한다.
    반환: 에피소드 로그 딕셔너리 리스트.
    """
    if logs_dir is None:
        logs_dir = Path(config.LOGS_DIR)
    else:
        logs_dir = Path(logs_dir)

    if not logs_dir.exists():
        return []

    episodes = []
    for path in sorted(logs_dir.rglob("*.json")):
        try:
            ep = _load_and_validate(path)
            if ep is not None:
                episodes.append(ep)
        except Exception as e:
            print(f"[logparser] 로드 실패: {path} - {e}")

    return episodes


def load_run(run_dir: str | Path) -> list[dict]:
    """특정 run 폴더의 에피소드만 로드한다."""
    run_dir = Path(run_dir)
    if not run_dir.exists():
        return []

    episodes = []
    for path in sorted(run_dir.glob("*.json")):
        try:
            ep = _load_and_validate(path)
            if ep is not None:
                episodes.append(ep)
        except Exception as e:
            print(f"[logparser] 로드 실패: {path} - {e}")

    return episodes


def _load_and_validate(path: Path) -> dict | None:
    """
    JSON 파일을 로드하고 최소 스키마 검증.
    Spec §7 필수 필드: episode_id, condition, turns, final_score.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # 최소 필수 필드 확인
    required = ("episode_id", "condition", "turns", "final_score")
    for field in required:
        if field not in data:
            print(f"[logparser] 필수 필드 누락({field}): {path}")
            return None

    # 소스 경로 보존 (디버깅용)
    data["_source_path"] = str(path)

    return data
