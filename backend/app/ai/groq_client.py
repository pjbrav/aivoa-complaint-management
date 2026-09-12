"""
Groq LLM wrapper.

All LangGraph nodes call the LLM through `call_groq_json`, never directly
through the SDK. This keeps one place responsible for:
  - selecting the model (gemma2-9b-it by default, llama-3.3-70b-versatile
    for the few nodes that benefit from stronger reasoning, e.g. risk
    assessment)
  - enforcing structured JSON output
  - retrying once on malformed JSON before failing loudly
  - never crashing the caller on a Groq outage (raises a typed exception
    the API layer turns into a user-facing error, per the assignment's
    error-handling requirements)
"""
import json
import re
from typing import Any

from groq import Groq, APIError, APIConnectionError

from app.config import get_settings

settings = get_settings()

_client: Groq | None = None


class GroqUnavailableError(Exception):
    """Raised when Groq cannot be reached or the API key is missing."""


class GroqMalformedResponseError(Exception):
    """Raised when the model's output could not be parsed as valid JSON
    even after one retry with a stricter instruction."""


def _get_client() -> Groq:
    global _client
    if not settings.groq_api_key:
        raise GroqUnavailableError(
            "GROQ_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    if _client is None:
        try:
            _client = Groq(api_key=settings.groq_api_key)
        except Exception as exc:  # SDK/dependency version issues, etc.
            raise GroqUnavailableError(f"Could not initialize Groq client: {exc}") from exc
    return _client


def _extract_json_block(text: str) -> dict[str, Any]:
    """Groq's gemma2-9b-it doesn't always wrap output in pure JSON even
    when asked. Strip markdown fences and grab the outermost {...} block
    before parsing, since a model might still add a one-line preamble."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise GroqMalformedResponseError(f"No JSON object found in model output: {text[:300]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GroqMalformedResponseError(
            f"Model output looked like JSON but failed to parse: {exc}"
        ) from exc


def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Call Groq and return a parsed JSON dict. Retries once with a
    stricter reminder if the first response isn't valid JSON."""
    client = _get_client()
    chosen_model = model or settings.groq_primary_model

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw = response.choices[0].message.content or ""
        return _extract_json_block(raw)
    except (GroqMalformedResponseError,):
        # Retry once with an explicit "JSON only" correction appended.
        try:
            retry_messages = messages + [
                {
                    "role": "user",
                    "content": "Your previous response was not valid JSON. "
                    "Respond again with ONLY a single valid JSON object, "
                    "no markdown, no commentary.",
                }
            ]
            response = client.chat.completions.create(
                model=chosen_model,
                messages=retry_messages,
                temperature=0.0,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or ""
            return _extract_json_block(raw)
        except Exception as exc:
            raise GroqMalformedResponseError(str(exc)) from exc
    except (APIError, APIConnectionError) as exc:
        raise GroqUnavailableError(f"Groq API error: {exc}") from exc

