"""
Thin wrapper around the Google Gemini API for the RAG
"generate an answer from retrieved context" step.

Handles:
- Gemini API authentication
- Environment configuration
- Bounded retries for temporary 503/429 errors
- User-friendly error messages
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load backend/.env regardless of the current working directory
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)


DEFAULT_MODEL = "gemini-3.6-flash"

MAX_RETRIES = 2
RETRY_DELAYS = [2, 5]


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self.model = model

        resolved_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        if not resolved_key:
            raise RuntimeError(
                "No Gemini API key found. Set GEMINI_API_KEY "
                "(or GOOGLE_API_KEY) in the environment, "
                "or pass api_key explicitly."
            )

        self._client = genai.Client(
            api_key=resolved_key,
            http_options=types.HttpOptions(
                timeout=30_000,
                retry_options=types.HttpRetryOptions(
                    attempts=2,
                    initial_delay=1,
                    max_delay=5,
                    exp_base=2,
                    jitter=1,
                    http_status_codes=[429, 500, 502, 503, 504],
                ),
            ),
        )

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:

        config = {
            "max_output_tokens": max_tokens,
        }

        if system:
            config["system_instruction"] = system

        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                return response.text or ""

            except Exception as exc:
                last_error = exc
                error_text = str(exc)

                # Retry only temporary service/rate-limit failures.
                retryable = any(
                    code in error_text
                    for code in ("429", "500", "502", "503", "504")
                )

                if not retryable or attempt >= MAX_RETRIES:
                    break

                time.sleep(RETRY_DELAYS[attempt])

        raise RuntimeError(
            "AI service is temporarily unavailable. "
            "Please try again in a moment."
        ) from last_error