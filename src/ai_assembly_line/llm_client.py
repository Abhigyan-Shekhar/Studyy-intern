
import json
import os
import re
from typing import Any, Dict, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class LLMClient:
    """Minimal wrapper around Gemini API with strict JSON parsing."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required.")

        if not genai:
            raise RuntimeError("Missing dependency: install `google-genai` first.")

        self._client = genai.Client(api_key=self.api_key)

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> Dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",
                ),
            )
            text = response.text
            return _parse_json_payload(text)
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}") from e


def _parse_json_payload(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise ValueError("Expected top-level JSON object.")
        return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Unable to parse JSON object from model response.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Expected top-level JSON object.")
    return payload

