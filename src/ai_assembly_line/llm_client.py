
import json
import os
import re
import time
from typing import Type
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class LLMClient:
    """Minimal wrapper around Gemini API."""

    def __init__(self, model: str, api_key: str = None):
        self.model_name = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required.")

        if not genai:
            raise RuntimeError("Missing dependency: install `google-genai` first.")

        self._client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 2000,
        max_retries: int = 3,
    ) -> str:
        """Generate a text response from the LLM."""
        for attempt in range(max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = 60 * (2 ** attempt)
                    delay_match = re.search(r"retry\s+in\s+([\d.]+)s", error_str, re.IGNORECASE)
                    if delay_match:
                        wait_time = max(float(delay_match.group(1)) + 5, wait_time)
                    if attempt < max_retries:
                        print(f"[RATE LIMIT] Attempt {attempt + 1}/{max_retries + 1} — waiting {wait_time:.0f}s...")
                        time.sleep(wait_time)
                        continue
                raise RuntimeError(f"Gemini generation failed: {e}") from e
