# agent/llm_client.py — 프로바이더 공통 LLM 호출 인터페이스.
# 모델명 prefix로 프로바이더 자동 판별. tenacity 지수 백오프 재시도. 타임아웃 60s.
# API 키는 환경변수에서만 읽는다. 코드에 하드코딩 금지.

from __future__ import annotations

import os
import time

from tenacity import retry, stop_after_attempt, wait_exponential

import config


def complete(
    messages: list[dict],
    system_prompt: str,
    model: str,
    temperature: float = config.LLM_TEMPERATURE,
) -> str:
    """
    LLM에 messages를 보내고 텍스트 응답을 반환한다.
    프로바이더는 model명 prefix로 자동 판별:
      - "gemini-"              → Google Gemini
      - "gpt-"                 → OpenAI
      - "claude-"              → Anthropic
      - "meta/" "mistralai/"
        "nvidia/" "microsoft/"
        "google/" "qwen/"      → NVIDIA NIM (OpenAI 호환)
    """
    if model.startswith("gemini"):
        return _complete_gemini(messages, system_prompt, model, temperature)
    elif model.startswith("gpt"):
        return _complete_openai(messages, system_prompt, model, temperature)
    elif model.startswith("claude"):
        return _complete_anthropic(messages, system_prompt, model, temperature)
    elif any(model.startswith(p) for p in ("meta/", "mistralai/", "nvidia/", "microsoft/", "google/", "qwen/")):
        return _complete_nim(messages, system_prompt, model, temperature)
    else:
        raise ValueError(f"지원하지 않는 모델명: {model}")


# ── Gemini ────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(config.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _complete_gemini(
    messages: list[dict],
    system_prompt: str,
    model: str,
    temperature: float,
) -> str:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    client = genai.Client(api_key=api_key)

    # messages를 Gemini Contents 형식으로 변환
    # Gemini는 role이 "user"/"model" 두 가지만 허용
    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=1024,
        ),
    )
    return response.text


# ── OpenAI ────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(config.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _complete_openai(
    messages: list[dict],
    system_prompt: str,
    model: str,
    temperature: float,
) -> str:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key, timeout=config.LLM_TIMEOUT_SEC)

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ── Anthropic ─────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(config.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _complete_anthropic(
    messages: list[dict],
    system_prompt: str,
    model: str,
    temperature: float,
) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key, timeout=config.LLM_TIMEOUT_SEC)

    response = client.messages.create(
        model=model,
        system=system_prompt,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return response.content[0].text


# ── NVIDIA NIM ────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(config.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _complete_nim(
    messages: list[dict],
    system_prompt: str,
    model: str,
    temperature: float,
) -> str:
    from openai import OpenAI

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise EnvironmentError("NVIDIA_API_KEY 환경변수가 설정되지 않았습니다.")

    # NIM은 OpenAI 호환 API — base_url만 다름
    client = OpenAI(
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=config.LLM_TIMEOUT_SEC,
    )

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return response.choices[0].message.content
