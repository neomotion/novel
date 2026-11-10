"""Shared Gemini helper: pins the API version, retries busy/rate-limit errors,
and falls back to the next model when one is retired or keeps failing."""
import os
import time

from google import genai
from google.genai import errors, types

# JSON mode (response_mime_type) only works on v1beta.
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options=types.HttpOptions(api_version="v1beta"),
)

RETRY_CODES = {429, 500, 502, 503, 504}


def generate(models, contents, config=None, attempts=4):
    """Return the response text from the first model that answers."""
    last_error = None
    for model in models:
        for attempt in range(attempts):
            try:
                response = client.models.generate_content(
                    model=model, contents=contents, config=config
                )
                if response.text:
                    print(f"Generated with {model}")
                    return response.text
                last_error = RuntimeError(f"{model} returned an empty response")
            except errors.APIError as e:
                last_error = e
                if e.code == 404:  # model retired or unknown: try the next one
                    print(f"{model} unavailable: {e.message}")
                    break
                if e.code not in RETRY_CODES:
                    raise
            print(f"{model} attempt {attempt + 1} failed: {last_error}")
            if attempt < attempts - 1:
                time.sleep(15 * 2**attempt)
    raise last_error


def models_from_env(var, defaults):
    """A comma-separated env var overrides the default model list."""
    value = os.environ.get(var, "").strip()
    return [m.strip() for m in value.split(",") if m.strip()] if value else defaults
