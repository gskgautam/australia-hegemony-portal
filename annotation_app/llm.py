"""
Model output generation.

All four consortium models are called through OpenRouter with the shared settings
posted in #resources (29 Oct 2026): system prompt "Answer in no more than 150 words
in English.", reasoning enabled, temperature and max tokens left at provider defaults.
"""

import requests

from config import ENABLE_REASONING, KEYS, MODELS, SYSTEM_PROMPT

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 180

_MODELS_BY_KEY = {m["key"]: m for m in MODELS}


def generate_output(model_key: str, prompt: str) -> str:
    model = _MODELS_BY_KEY[model_key]

    response = requests.post(
        url=OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {KEYS['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model["openrouter_id"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "reasoning": {"enabled": ENABLE_REASONING},
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    data = response.json()
    if response.status_code != 200 or "choices" not in data:
        message = (data.get("error") or {}).get("message") or response.text[:300]
        raise RuntimeError(f"OpenRouter {response.status_code} for {model['openrouter_id']}: {message}")

    return data["choices"][0]["message"]["content"]
