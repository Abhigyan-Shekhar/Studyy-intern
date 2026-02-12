import json
from typing import Dict, Any
from .llm_client import LLMClient
from .pydantic_models import ExamResult
from .schemas import GradeOutput, GradeItem, ScribeOutput, ScribeItem


SINGLE_SHOT_SYSTEM_PROMPT = """You are an expert exam grader.
Your task is to read the raw text from a student's answer sheet, identify the answers corresponding to the provided Answer Key, and grade them against the Rubric.

Hard Rules:
1) Denoise the text: The input is raw OCR. Correct typos and formatting issues when extracting the answer.
2) Grade strictly: Use the provided Answer Key and Rubric.
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
        answer_key: Dict[str, Dict[str, Any]],
        rubric_text: str,
        confidence_threshold: float = 80.0,
    ) -> tuple[ScribeOutput, GradeOutput]:
        """
        Run extraction and grading in a single pass.
        Returns ScribeOutput and GradeOutput to maintain compatibility with the pipeline.
        """
        user_prompt = (
            f"Exam ID: {exam_id}\n\n"
            "Rubric:\n"
            f"{rubric_text.strip()}\n\n"
            "Answer Key:\n"
            f"{json.dumps(answer_key, indent=2)}\n\n"
            "Raw OCR Text:\n"
            f"{raw_text}\n"
        )

        # 1. Inspect raw OCR text
        # 2. Identify answers for each question in Answer Key
        # 3. Grade each answer
        # 4. Return structured output

        result: ExamResult = self.client.generate_structured(
            system_prompt=SINGLE_SHOT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ExamResult,
            temperature=0.0,
        )

        # Convert Pydantic Result -> ScribeOutput + GradeOutput
        # This ensures the rest of the pipeline (reports, analytics) continues to work.

        scribe_items = []
        grade_items = []

        for q in result.questions:
            # Scribe Output (Simulated)
            scribe_items.append(
                ScribeItem(
                    question_id=q.question_id,
                    question_text="",  # Schema doesn't ask for question text, keeping empty
                    student_answer=q.student_answer,
                    transcription_notes=["Extracted via single-shot mode"],
                )
            )

            # Grade Output
            flagged = (q.confidence < confidence_threshold) or (q.verdict == "partially_correct")
            grade_items.append(
                GradeItem(
                    question_id=q.question_id,
                    awarded_points=q.awarded_points,
                    max_points=q.max_points,
                    verdict=q.verdict,
                    feedback=q.feedback,
                    confidence=q.confidence,
                    flagged_for_review=flagged,
                )
            )

        scribe_output = ScribeOutput(exam_id=exam_id, items=scribe_items)
        grade_output = GradeOutput(exam_id=exam_id, items=grade_items)

        return scribe_output, grade_output
