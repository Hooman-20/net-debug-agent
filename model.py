"""All model calls go through ask_model(). Swap the model here."""
import os

from openai import OpenAI

BASE_URL = os.environ.get("MODEL_BASE_URL", "https://api.meta.ai/v1")
MODEL = os.environ.get("MODEL_NAME", "muse-spark-1.3")

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise SystemExit("MODEL_API_KEY is not set. Run: export MODEL_API_KEY=...")
        _client = OpenAI(base_url=BASE_URL, api_key=key)
    return _client


def ask_model(messages, temperature=0.2, max_tokens=2000):
    """Send a list of chat messages, return the reply text."""
    resp = _get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
