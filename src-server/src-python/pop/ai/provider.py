"""
Unified AI provider abstraction — dispatches to Anthropic or Gemini.

Provides a single function that both advisor.py and generator.py use
instead of calling Anthropic SDK directly.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.0-flash"


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

    if provider == "gemini":
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

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        )
    except Exception as e:
        raise ValueError(f"Gemini API error: {e}") from e

    text = response.text or ""
    # Gemini usage metadata
    tokens_used = 0
    if response.usage_metadata:
        tokens_used = (
            (response.usage_metadata.prompt_token_count or 0)
            + (response.usage_metadata.candidates_token_count or 0)
        )
    return text, tokens_used
