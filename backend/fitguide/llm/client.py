"""Minimal OpenAI-compatible chat client (works with Gemini, OpenRouter, Groq and others).

- Tries each model in LLM_MODELS in order and moves on when a model is rate limited (429), missing (404) or broken (5xx).
- Asks for JSON when needed and validates it with Pydantic (see parse_json_model).
- Never logs prompts or user data."""
from __future__ import annotations
import json, re
from typing import Any, Protocol, TypeVar
import httpx
from pydantic import BaseModel, ValidationError
from ..config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    async def chat(self, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.3, max_tokens: int = 1200) -> str: ...


class OpenAICompatLLM:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()

    async def chat(self, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.3, max_tokens: int = 1200) -> str:
        if not self.s.api_key:
            raise LLMError("No LLM_API_KEY configured")
        last_err = "unknown error"
        async with httpx.AsyncClient(timeout=self.s.timeout_s) as client:
            for model in self.s.models:
                body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
                if json_mode:
                    body["response_format"] = {"type": "json_object"}
                try:
                    r = await client.post(f"{self.s.base_url}/chat/completions", json=body,
                                          headers={"Authorization": f"Bearer {self.s.api_key}"})
                except httpx.HTTPError as e:
                    last_err = f"{model}: network error {type(e).__name__}"
                    continue
                if r.status_code in (400,) and json_mode:
                    # some providers do not support response_format; retry once without it
                    body.pop("response_format", None)
                    try:
                        r = await client.post(f"{self.s.base_url}/chat/completions", json=body, headers={"Authorization": f"Bearer {self.s.api_key}"})
                    except httpx.HTTPError as e:
                        last_err = f"{model}: network error {type(e).__name__}"
                        continue
                if r.status_code in (401, 403):
                    raise LLMError("The API key was rejected. Check LLM_API_KEY.")
                if r.status_code in (404, 429) or r.status_code >= 500:
                    last_err = f"{model}: HTTP {r.status_code}"
                    continue
                if r.status_code != 200:
                    last_err = f"{model}: HTTP {r.status_code}"
                    continue
                try:
                    return r.json()["choices"][0]["message"]["content"] or ""
                except (KeyError, IndexError, ValueError):
                    last_err = f"{model}: unexpected response shape"
        raise LLMError(f"All models failed ({last_err})")


def extract_json(text: str) -> Any:
    """Models sometimes wrap JSON in ```json fences or add words around it. Pull the first JSON object out."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def parse_json_model(llm: LLM, messages: list[dict], model: type[T], *, retries: int = 1, **kw) -> T:
    """Call the LLM, validate against a Pydantic model, and ask once more with the error if it is invalid."""
    msgs = list(messages)
    last: Exception | None = None
    for _ in range(retries + 1):
        raw = await llm.chat(msgs, json_mode=True, **kw)
        try:
            return model.model_validate(extract_json(raw))
        except (ValueError, ValidationError) as e:
            last = e
            msgs = msgs + [{"role": "assistant", "content": raw[:1500]},
                           {"role": "user", "content": f"That was not valid JSON for the required schema ({str(e)[:300]}). Reply again with ONLY the corrected JSON object."}]
    raise LLMError(f"Model did not return valid JSON: {last}")
