import json
from typing import Dict, Any
from .llm_client import LLMClient
from .pydantic_models import (
    ExamResult,
    GradeOutput,
    GradeItem,
    ScribeOutput,
    ScribeItem,
    DEFAULT_CONFIDENCE_THRESHOLD,
)


SINGLE_SHOT_SYSTEM_PROMPT = """You are an expert exam grader.
Your task is to read the raw text from a student's answer sheet, extract the answers, and grade them using only the Rubric below.

## Rubric
{rubric}

## Hard Rules
1) Denoise the text: The input is raw OCR. Correct typos and formatting issues when extracting the answer.
2) Grade strictly using only the Rubric above. Do not infer or assume any additional grading criteria.
3) Confidence: Assign a confidence score (0-100) based on how certain you are.
4) Output: Return a structured JSON matching the schema.
"""

class SingleShotAgent:
    def __init__(self, client: LLMClient):
        self.client = client

    def run_one(
        self,
        *,
        exam_id: str,
        raw_text: str,
        rubric_text: str,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> tuple[ScribeOutput, GradeOutput]:
        """
        Run extraction and grading in a single pass.
        Returns ScribeOutput and GradeOutput for report generation.
        """
        system_prompt = SINGLE_SHOT_SYSTEM_PROMPT.format(rubric=rubric_text.strip())

        user_prompt = (
            f"Exam ID: {exam_id}\n\n"
            "Raw OCR Text:\n"
            f"{raw_text}\n"
        )

        result: ExamResult = self.client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=ExamResult,
            temperature=0.0,
        )

        # Convert LLM output -> pipeline models
        scribe_items = []
        grade_items = []

        for q in result.questions:
            scribe_items.append(ScribeItem(
                question_id=q.question_id,
                student_answer=q.student_answer,
                transcription_notes=["Extracted via single-shot mode"],
            ))

            flagged = (q.confidence < confidence_threshold) or (q.verdict == "partially_correct")
            grade_items.append(GradeItem(
                question_id=q.question_id,
                awarded_points=q.awarded_points,
                max_points=q.max_points,
                verdict=q.verdict,
                feedback=q.feedback,
                confidence=q.confidence,
                flagged_for_review=flagged,
            ))

        return (
            ScribeOutput(exam_id=exam_id, items=scribe_items),
            GradeOutput(exam_id=exam_id, items=grade_items),
        )
