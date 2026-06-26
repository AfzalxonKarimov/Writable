"""
OpenRouter API client with automatic fallback across config.VISION_MODELS /
config.TEXT_MODELS. If a model 429s, errors, or returns unparseable output,
we move to the next one in the list automatically -- this is the resilience
layer we designed specifically because free models get pulled/rate-limited
without notice.
"""
import json
import logging

import aiohttp

import config

logger = logging.getLogger(__name__)


class AIRequestError(Exception):
    """Raised when every model in the fallback list has failed."""
    pass


async def _call_openrouter(model: str, messages: list[dict]) -> str:
    """Single call to one model. Raises on any failure; caller handles fallback."""
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/",  # OpenRouter recommends setting these
        "X-Title": "IELTS Writing Bot",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,  # low temperature: we want consistent, rubric-following scoring, not creativity
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            config.OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=90
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise AIRequestError(f"Model {model} returned HTTP {resp.status}: {body[:300]}")
            data = await resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise AIRequestError(f"Model {model} returned unexpected shape: {data}") from e


def _extract_json(raw_text: str) -> dict:
    """
    Models sometimes wrap JSON in markdown fences or add stray text despite
    instructions. Strip common wrappers before parsing, rather than failing
    outright on the first model that's slightly chatty.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # If there's still leading/trailing junk, try to isolate the outermost {...}
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)


async def run_with_fallback(
    prompt: str,
    model_list: list[str],
    image_file_url: str | None = None,
) -> tuple[dict, str]:
    """
    Try each model in model_list in order until one succeeds and returns
    parseable JSON. Returns (parsed_json, model_name_used).
    Raises AIRequestError if every model in the list fails.
    """
    content: list[dict] = [{"type": "text", "text": prompt}]
    if image_file_url:
        content.append({"type": "image_url", "image_url": {"url": image_file_url}})

    messages = [{"role": "user", "content": content}]

    last_error: Exception | None = None
    for model in model_list:
        try:
            raw = await _call_openrouter(model, messages)
            parsed = _extract_json(raw)
            return parsed, model
        except (AIRequestError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Model {model} failed, trying next in fallback list: {e}")
            last_error = e
            continue

    raise AIRequestError(
        f"All models in fallback list failed. Last error: {last_error}"
    )


async def assess_writing(prompt: str, image_file_url: str | None = None) -> tuple[dict, str]:
    """Assessment uses VISION_MODELS list (Task 1 needs vision; Task 2 doesn't
    strictly need it, but using the same list keeps behavior consistent)."""
    return await run_with_fallback(prompt, config.VISION_MODELS, image_file_url)


async def generate_sample(prompt: str, image_file_url: str | None = None) -> tuple[dict, str]:
    """Sample generation: vision list only needed for Task 1 (image present)."""
    model_list = config.VISION_MODELS if image_file_url else config.TEXT_MODELS
    return await run_with_fallback(prompt, model_list, image_file_url)
