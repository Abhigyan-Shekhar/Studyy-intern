import json
import logging
from typing import Dict, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage

from .pydantic_models import (
    ExamResult,
    GradeOutput,
    GradeItem,
    ScribeOutput,
    ScribeItem,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


SINGLE_SHOT_SYSTEM_PROMPT = """You are an expert exam grader.
Your task is to read the raw text from a student's answer sheet, extract the answers, and grade them using only the Rubric below.

## Rubric
{rubric}

## Hard Rules
1) Denoise the text: The input is raw OCR. Correct typos and formatting issues when extracting the answer.
2) Grade strictly using only the Rubric above. Do not infer or assume any additional grading criteria.
3) Confidence: Assign a confidence score (0-100) based on how certain you are.
4) Output: Return a structured JSON matching the format instructions below.

## Format Instructions
{format_instructions}
"""


# Create the parser from the Pydantic model
parser = PydanticOutputParser(pydantic_object=ExamResult)


class SingleShotAgent:
    def __init__(self, llm):
        """
        Args:
            llm: A LangChain chat model (e.g., ChatGoogleGenerativeAI).
        """
        self.llm = llm

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
        # Get format instructions from the Pydantic parser
        format_instructions = parser.get_format_instructions()

        # Build system prompt with rubric + format instructions
        system_prompt = SINGLE_SHOT_SYSTEM_PROMPT.format(
            rubric=rubric_text.strip(),
            format_instructions=format_instructions,
        )

        user_prompt = (
            f"Exam ID: {exam_id}\n\n"
            "Raw OCR Text:\n"
            f"{raw_text}\n"
        )

        # Invoke LangChain LLM with system + human messages
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        # Parse the response using PydanticOutputParser
        result: ExamResult = parser.parse(response.content)

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
