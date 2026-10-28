"""One thin REST adapter per provider (no vendor SDKs needed, just httpx).
Whichever API key is present gets used; AI_PROVIDER=auto picks the first configured."""
from typing import Optional

import httpx

from ..config import get_settings

PROVIDERS = ("anthropic", "openai", "gemini")


class AIError(Exception):
    """Provider call failed (bad key, wrong model name, quota, network...)."""


class AINotConfigured(AIError):
    """No usable API key."""


def configured_providers() -> dict:
    s = get_settings()
    return {
        "anthropic": {"configured": bool(s.anthropic_api_key), "model": s.anthropic_model},
        "openai": {"configured": bool(s.openai_api_key), "model": s.openai_model},
        "gemini": {"configured": bool(s.gemini_api_key), "model": s.gemini_model},
    }


def resolve_provider(requested: Optional[str] = None) -> str:
    s = get_settings()
    choice = (requested or s.ai_provider or "auto").lower()
    info = configured_providers()
    if choice == "auto":
        for name in PROVIDERS:
            if info[name]["configured"]:
                return name
        raise AINotConfigured(
            "No AI API key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY in .env "
            "(any one is enough).")
    if choice not in PROVIDERS:
        raise AIError(f"Unknown provider '{choice}'. Use one of: auto, {', '.join(PROVIDERS)}.")
    if not info[choice]["configured"]:
        raise AINotConfigured(f"Provider '{choice}' selected but its API key is not set.")
    return choice


async def complete(provider: str, system: str, user: str,
                   client: Optional[httpx.AsyncClient] = None) -> str:
    s = get_settings()
    fn = {"anthropic": _anthropic, "openai": _openai, "gemini": _gemini}[provider]
    own = client is None
    client = client or httpx.AsyncClient(timeout=s.ai_timeout)
    try:
        return await fn(client, system, user)
    except httpx.TimeoutException:
        raise AIError(f"{provider}: request timed out after {s.ai_timeout}s")
    except httpx.HTTPError as e:
        raise AIError(f"{provider}: network error {type(e).__name__}")
    finally:
        if own:
            await client.aclose()


def _raise_for_error(provider: str, r: httpx.Response) -> None:
    if r.status_code >= 400:
        detail = r.text[:300].replace("\n", " ")
        hint = ""
        if r.status_code in (401, 403):
            hint = " (check the API key)"
        elif r.status_code == 404:
            hint = " (model name may be wrong/retired - set the *_MODEL variable in .env)"
        elif r.status_code == 429:
            hint = " (rate limit or quota exceeded)"
        raise AIError(f"{provider} API returned HTTP {r.status_code}{hint}: {detail}")


async def _anthropic(client: httpx.AsyncClient, system: str, user: str) -> str:
    s = get_settings()
    r = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": s.anthropic_model, "max_tokens": 2000, "system": system,
              "messages": [{"role": "user", "content": user}]},
    )
    _raise_for_error("anthropic", r)
    blocks = r.json().get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    if not text:
        raise AIError("anthropic returned an empty response")
    return text


async def _openai(client: httpx.AsyncClient, system: str, user: str) -> str:
    s = get_settings()
    r = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {s.openai_api_key}"},
        json={"model": s.openai_model,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
    )
    _raise_for_error("openai", r)
    try:
        text = r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        text = None
    if not text:
        raise AIError("openai returned an empty response")
    return text


async def _gemini(client: httpx.AsyncClient, system: str, user: str) -> str:
    s = get_settings()
    r = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent",
        headers={"x-goog-api-key": s.gemini_api_key, "content-type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}]},
    )
    _raise_for_error("gemini", r)
    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        text = ""
    if not text:
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidates returned")
        raise AIError(f"gemini returned no text ({reason})")
    return text
