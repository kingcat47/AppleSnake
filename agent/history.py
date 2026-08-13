# agent/history.py — 대화 히스토리 누적 관리.
# OpenAI/Anthropic/Gemini 공통 messages 배열 형식 사용.

from __future__ import annotations

import config


class History:
    """
    에피소드 1회 동안의 messages 배열을 관리한다.
    형식: [{"role": "user"|"assistant"|"system", "content": "..."}]
    """

    def __init__(self, system_prompt: str) -> None:
        self._messages: list[dict] = []
        self._system_prompt = system_prompt
        # system 메시지는 별도 보관 (Gemini는 system_instruction으로 따로 넘김)

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    @property
    def messages(self) -> list[dict]:
        """현재까지 누적된 messages 배열 반환 (system 제외)."""
        return list(self._messages)

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def turn_count(self) -> int:
        """assistant 응답 횟수 = 실제 턴 수."""
        return sum(1 for m in self._messages if m["role"] == "assistant")

    def check_limit(self) -> None:
        """턴 상한 초과 시 AssertionError."""
        assert self.turn_count <= config.MAX_HISTORY_TURNS, (
            f"히스토리 턴 상한({config.MAX_HISTORY_TURNS}) 초과: {self.turn_count}"
        )