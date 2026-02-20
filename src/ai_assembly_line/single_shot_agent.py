import logging
from typing import Dict, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .pydantic_models import (
    ExamResult,
    GradeOutput,
    GradeItem,
    ScribeOutput,
    ScribeItem,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


# Pydantic output parser
parser = PydanticOutputParser(pydantic_object=ExamResult)


# LangChain prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are an expert exam grader.
Your task is to read the raw text from a student's answer sheet, extract the answers, and grade them using only the Rubric below.

## Rubric
{rubric}

## Hard Rules
1) Denoise the text: The input is raw OCR. Correct typos and formatting issues when extracting the answer.
2) Grade strictly using only the Rubric above. Do not infer or assume any additional grading criteria.
3) Confidence: Assign a confidence score (0-100) based on how certain you are.
4) Output: Return a structured JSON matching the format instructions below.

## Format Instructions
{format_instructions}"""),
    ("human",
     "Exam ID: {exam_id}\n\nRaw OCR Text:\n{raw_text}"),
])


class SingleShotAgent:
    def __init__(self, llm):
        """
        Args:
            llm: A LangChain chat model (e.g., ChatGoogleGenerativeAI).
        """
        # LCEL chain: prompt → LLM → parser
        self.chain = prompt | llm | parser

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
        # Invoke the chain with all template variables
        result: ExamResult = self.chain.invoke({
            "rubric": rubric_text.strip(),
            "format_instructions": parser.get_format_instructions(),
            "exam_id": exam_id,
            "raw_text": raw_text,
        })

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
