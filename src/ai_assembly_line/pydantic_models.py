from typing import List
from pydantic import BaseModel, Field


# ── LLM Output Schema (passed to Gemini's response_schema) ──────────────

class QuestionResult(BaseModel):
    """Result for a single graded question — used as the LLM output schema."""
    question_id: str = Field(description="The question ID (e.g., 'Q1')")
    student_answer: str = Field(description="The extracted student answer text")
    awarded_points: float = Field(description="Points awarded for this question")
    max_points: float = Field(description="Maximum possible points for this question")
    verdict: str = Field(description="One of: 'correct', 'partially_correct', 'incorrect'")
    confidence: float = Field(description="Confidence score (0-100) for the grading")
    feedback: str = Field(description="Specific feedback explaining the grade")


class ExamResult(BaseModel):
    """Overall exam grading result — used as the LLM output schema."""
    exam_id: str = Field(description="The ID of the exam/student")
    questions: List[QuestionResult] = Field(description="List of graded questions")


# ── Internal Pipeline Models ────────────────────────────────────────────

DEFAULT_CONFIDENCE_THRESHOLD = 80.0


class ScribeItem(BaseModel):
    """A single extracted question/answer pair."""
    question_id: str
    question_text: str = ""
    student_answer: str
    transcription_notes: List[str] = []


class ScribeOutput(BaseModel):
    """All extracted items for one exam."""
    exam_id: str
    items: List[ScribeItem]


class GradeItem(BaseModel):
    """A single graded question."""
    question_id: str
    awarded_points: float
    max_points: float
    verdict: str
    feedback: str
    confidence: float = 100.0
    flagged_for_review: bool = False


class GradeOutput(BaseModel):
    """All graded items for one exam."""
    exam_id: str
    items: List[GradeItem]

    @property
    def flagged_items(self) -> List[GradeItem]:
        return [item for item in self.items if item.flagged_for_review]

    @property
    def flagged_count(self) -> int:
        return len(self.flagged_items)

    @property
    def total_awarded(self) -> float:
        return sum(item.awarded_points for item in self.items)

    @property
    def total_max(self) -> float:
        return sum(item.max_points for item in self.items)

    @property
    def percentage(self) -> float:
        if self.total_max <= 0:
            return 0.0
        return (self.total_awarded / self.total_max) * 100.0
