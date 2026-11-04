"""All model calls go through ask_model(). Swap the model in config.py."""
import os

from openai import OpenAI

from config import MODEL_BASE_URL, MODEL_NAME as MODEL

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise SystemExit("MODEL_API_KEY is not set. Run: export MODEL_API_KEY=...")
        _client = OpenAI(base_url=MODEL_BASE_URL, api_key=key)
    return _client


def ask_model(messages, temperature=0.2, max_tokens=8000):
    """Send a list of chat messages, return the reply text.

    Muse Spark is a reasoning model: hidden reasoning tokens count against max_tokens,
    so keep it generous or replies come back empty.
    """
    resp = _get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = resp.choices[0]
    if choice.finish_reason == "length":
        print(f"[warning] model reply cut off at max_tokens={max_tokens}")
    return choice.message.content or ""
