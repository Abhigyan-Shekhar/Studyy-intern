from __future__ import annotations

import json
from typing import Any, Dict

from .llm_client import LLMClient
from .schemas import GradeOutput, ScribeOutput


SCRIBE_SYSTEM_PROMPT = """You are the Extraction Agent in an exam-grading pipeline.
Your only job: transcribe and clean OCR noise into structured question/answer records.

Hard rules:
1) Never grade or evaluate quality of answers.
2) Preserve student intent and wording. Correct only obvious OCR artifacts.
3) If text is unreadable, keep best-effort text and note uncertainty in transcription_notes.
4) Return valid JSON object only (no markdown).

Output schema:
{
  "exam_id": "string",
  "items": [
    {
      "question_id": "string",
      "question_text": "string",
      "student_answer": "string",
      "transcription_notes": ["string"]
    }
  ]
}
"""


GRADER_SYSTEM_PROMPT = """You are the Grading Agent in a two-stage pipeline.
Input already came from an Extraction Agent.

Hard rules:
1) Grade only against provided answer key and rubric.
2) Do not improve, reinterpret, or infer missing student content.
3) No pity points. Reward only what is present in student_answer.
4) Keep feedback specific and short.
5) Return valid JSON object only (no markdown).

Output schema:
{
  "exam_id": "string",
  "items": [
    {
      "question_id": "string",
      "awarded_points": 0,
      "max_points": 0,
      "verdict": "string",
      "feedback": "string"
    }
  ]
}
"""


class ExtractionAgent:
    def __init__(self, client: LLMClient):
        self.client = client

    def run(self, *, exam_id: str, raw_text: str) -> ScribeOutput:
        user_prompt = (
            "Clean and structure the OCR text below.\n"
            f"exam_id: {exam_id}\n\n"
            "Raw OCR text:\n"
            f"{raw_text.strip()}\n"
        )
        payload = self.client.generate_json(
            system_prompt=SCRIBE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_output_tokens=1800,
        )
        return ScribeOutput.from_dict(payload)


class GradingAgent:
    def __init__(self, client: LLMClient):
        self.client = client

    def run(
        self,
        *,
        scribe_output: ScribeOutput,
        answer_key: Dict[str, Dict[str, Any]],
        rubric_text: str,
    ) -> GradeOutput:
        items_payload = [
            {
                "question_id": item.question_id,
                "question_text": item.question_text,
                "student_answer": item.student_answer,
                "transcription_notes": item.transcription_notes,
                "answer_key": answer_key.get(item.question_id, {}),
            }
            for item in scribe_output.items
        ]

        user_prompt = (
            f"exam_id: {scribe_output.exam_id}\n\n"
            "Rubric:\n"
            f"{rubric_text.strip()}\n\n"
            "Items to grade (JSON):\n"
            f"{json.dumps(items_payload, ensure_ascii=True, indent=2)}\n"
        )

        payload = self.client.generate_json(
            system_prompt=GRADER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_output_tokens=2200,
        )
        return GradeOutput.from_dict(payload)

