from typing import List
from pydantic import BaseModel, Field


class QuestionResult(BaseModel):
    """Result for a single graded question."""
    question_id: str = Field(description="The question ID (e.g., 'Q1')")
    student_answer: str = Field(description="The extracted student answer text")
    awarded_points: float = Field(description="Points awarded for this question")
    max_points: float = Field(description="Maximum possible points for this question")
    verdict: str = Field(description="One of: 'correct', 'partially_correct', 'incorrect'")
    confidence: float = Field(description="Confidence score (0-100) for the grading")
    feedback: str = Field(description="Specific feedback explaining the grade")


class ExamResult(BaseModel):
    """Overall exam grading result."""
    exam_id: str = Field(description="The ID of the exam/student")
    questions: List[QuestionResult] = Field(description="List of graded questions")
