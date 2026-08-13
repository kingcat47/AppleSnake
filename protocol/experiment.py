# protocol/experiment.py — 조건 x 반복 전체 실행. 로그 저장. 중단 후 재개(resume) 지원.
# Spec §6, §10 Phase 4 기반.

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

import config
from protocol.conditions import Condition
from protocol.runner import run_episode, save_episode_log


def run_experiment(
    conditions: list[Condition],
    n_episodes: int,
    run_dir: Path,
    seed_base: int = 42,
    max_turns: int | None = None,
    resume: bool = False,
    delay: float = 2.0,
) -> None:
    """
    조건 x n_episodes 전체를 실행한다.
    resume=True면 run_dir에 이미 있는 로그를 읽어 완료된 (조건, 에피소드번호)를 건너뛴다.
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    # resume: 이미 완료된 에피소드 파악
    completed = _load_completed(run_dir) if resume else set()
    if resume and completed:
        print(f"[resume] 이미 완료된 에피소드 {len(completed)}개 건너뜁니다.")

    total = len(conditions) * n_episodes
    done = 0
    skipped = 0

    rng = random.Random(seed_base)
    # seed를 조건/에피소드 번호에 상관없이 일관되게 생성
    all_seeds = [rng.randint(0, 2**31) for _ in range(total)]

    idx = 0
    for ci, cond in enumerate(conditions):
        cond_label = f"bi={cond.boundary_info} pen={cond.penalty} q={cond.question_style} fr={cond.framing} pm={cond.protocol_mode}"
        print(f"--- [{ci+1}/{len(conditions)}] {cond_label} ---")

        for ep in range(n_episodes):
            seed = all_seeds[idx]
            idx += 1
            run_key = _run_key(cond, ep)

            if run_key in completed:
                skipped += 1
                continue

            done += 1
            print(f"  [{done + skipped}/{total}] 실행 중...", end=" ", flush=True)

            try:
                log = run_episode(condition=cond, seed=seed, max_turns=max_turns)
                # run_key를 로그에 추가 (resume용)
                log["_run_key"] = run_key
                save_episode_log(log, log_dir=run_dir)

                ep_turns = len(log["turns"])
                ep_violations = sum(1 for t in log["turns"] if t["step_result"]["violation"])
                ep_score = log["final_score"]
                n_interr = len(log["interrogations"])

                print(
                    f"완료 | 턴={ep_turns} 위반={ep_violations} "
                    f"심문={n_interr} 점수={ep_score}"
                )
            except Exception as e:
                print(f"ERROR: {e}")

            if done + skipped < total:
                time.sleep(delay)

        print()

    print("=" * 60)
    print(f"[experiment] 완료: {done} 실행 / {skipped} 건너뜀 / 총 {total}")
    print(f"  로그 폴더: {run_dir}")
    print("=" * 60)


def _run_key(cond: Condition, ep_index: int) -> str:
    """조건 + 에피소드 번호로 고유 키 생성 (resume 판별용)."""
    return (
        f"{cond.boundary_info}|{cond.penalty}|{cond.question_style}|"
        f"{cond.framing}|{cond.protocol_mode}|{cond.model}|ep{ep_index}"
    )


def _load_completed(run_dir: Path) -> set[str]:
    """run_dir의 기존 로그에서 완료된 run_key 집합을 반환한다."""
    completed = set()
    for path in run_dir.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            key = data.get("_run_key")
            if key:
                completed.add(key)
        except (json.JSONDecodeError, KeyError):
            continue
    return completed
