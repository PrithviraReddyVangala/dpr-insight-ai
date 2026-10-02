"""
Thin wrapper around the Google Gemini API for the RAG "generate an answer
from retrieved context" step. Single responsibility: given a prompt, call
the LLM and return text. No retrieval logic here.

Requires GEMINI_API_KEY (or GOOGLE_API_KEY) to be set in the environment.
This module could not be exercised end-to-end in the sandboxed build
session (no API key was available there, and generativelanguage.googleapis.com
isn't reachable from this sandbox's network allowlist) — the retrieval
half (chunking/embedding/FAISS search) was fully tested; this call itself
should be smoke-tested once you have a key configured.
"""

from __future__ import annotations

import os

from google import genai

DEFAULT_MODEL = "gemini-3.6-flash"


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.model = model
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "No Gemini API key found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) "
                "in the environment, or pass api_key explicitly."
            )
        self._client = genai.Client(api_key=resolved_key)

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        config = {"max_output_tokens": max_tokens}
        if system:
            config["system_instruction"] = system
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text or ""
