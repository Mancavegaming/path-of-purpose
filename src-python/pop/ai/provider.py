"""
Unified AI provider abstraction — dispatches to Anthropic, Gemini, or OpenAI.

Provides a single function that both advisor.py and generator.py use
instead of calling provider SDKs directly.
"""

from __future__ import annotations

import logging
import re
import time

logger = logging.getLogger(__name__)

GEMINI_MAX_RETRIES = 3

ANTHROPIC_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"
OPENAI_MODEL = "gpt-4.1-mini"


def _sanitize_text(text: str) -> str:
    """Remove surrogate characters that break UTF-8 encoding on Windows."""
    return text.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")


def chat_completion(
    provider: str,
    api_key: str,
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> tuple[str, int]:
    """Send a chat completion request to the configured AI provider.

    Args:
        provider: "anthropic" or "gemini"
        api_key: API key for the provider
        system: System prompt
        messages: List of {"role": "user"/"assistant", "content": "..."}
        max_tokens: Maximum tokens in the response

    Returns:
        Tuple of (response_text, tokens_used)
    """
    # Sanitize all message content
    sanitized = [
        {"role": m["role"], "content": _sanitize_text(m["content"])}
        for m in messages
    ]

    if provider == "openai":
        return _openai_completion(api_key, system, sanitized, max_tokens)
    elif provider == "gemini":
        return _gemini_completion(api_key, system, sanitized, max_tokens)
    else:
        return _anthropic_completion(api_key, system, sanitized, max_tokens)


def _anthropic_completion(
    api_key: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
) -> tuple[str, int]:
    """Call the Anthropic Claude API."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
    except anthropic.APIError as e:
        raise ValueError(f"Anthropic API error: {e.message}") from e

    text = response.content[0].text
    tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
    return text, tokens_used


def _openai_completion(
    api_key: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
) -> tuple[str, int]:
    """Call the OpenAI API."""
    from openai import OpenAI, APIError

    client = OpenAI(api_key=api_key)

    oai_messages = [{"role": "system", "content": system}] + messages

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=oai_messages,
            max_tokens=max_tokens,
        )
    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}") from e

    text = response.choices[0].message.content or ""
    tokens_used = 0
    if response.usage:
        tokens_used = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)
    return text, tokens_used


def _gemini_completion(
    api_key: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
) -> tuple[str, int]:
    """Call the Google Gemini API via the google-genai SDK."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Build Gemini contents from messages
    contents: list[types.Content] = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    last_error = None
    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                ),
            )
            break
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Extract retry delay from error message if available
                delay = 30.0  # default wait
                match = re.search(r"retry in ([\d.]+)s", err_str, re.IGNORECASE)
                if match:
                    delay = float(match.group(1)) + 1.0
                logger.warning(
                    "Gemini 429 rate limit (attempt %d/%d), waiting %.1fs",
                    attempt + 1, GEMINI_MAX_RETRIES, delay,
                )
                time.sleep(delay)
                continue
            raise ValueError(f"Gemini API error: {e}") from e
    else:
        raise ValueError(
            f"Gemini API rate limit exceeded after {GEMINI_MAX_RETRIES} retries: {last_error}"
        ) from last_error

    text = response.text or ""
    # Gemini usage metadata
    tokens_used = 0
    if response.usage_metadata:
        tokens_used = (
            (response.usage_metadata.prompt_token_count or 0)
            + (response.usage_metadata.candidates_token_count or 0)
        )
    return text, tokens_used
