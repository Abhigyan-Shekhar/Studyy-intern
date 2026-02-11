from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional


class LLMClient:
    """Minimal wrapper around OpenAI Responses API with strict JSON parsing."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required.")

        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Missing dependency: install `openai` first.") from exc

        self._client = OpenAI(api_key=self.api_key, base_url=base_url)

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> Dict[str, Any]:
        response = self._client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ],
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        text = self._response_to_text(response)
        return _parse_json_payload(text)

    @staticmethod
    def _response_to_text(response: Any) -> str:
        direct = getattr(response, "output_text", None)
        if isinstance(direct, str) and direct.strip():
            return direct

        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    chunks.append(getattr(content, "text", ""))
        text = "\n".join(chunks).strip()
        if not text:
            raise ValueError("Model response did not contain text.")
        return text


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

