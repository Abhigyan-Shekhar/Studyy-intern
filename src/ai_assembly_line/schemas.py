from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ScribeItem:
    question_id: str
    question_text: str
    student_answer: str
    transcription_notes: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ScribeItem":
        return ScribeItem(
            question_id=str(data.get("question_id", "")).strip(),
            question_text=str(data.get("question_text", "")).strip(),
            student_answer=str(data.get("student_answer", "")).strip(),
            transcription_notes=[str(x) for x in data.get("transcription_notes", [])],
        )


@dataclass
class ScribeOutput:
    exam_id: str
    items: List[ScribeItem]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ScribeOutput":
        items_raw = data.get("items", [])
        if not isinstance(items_raw, list):
            raise ValueError("Scribe output must contain a list at key 'items'.")

        items = [ScribeItem.from_dict(item) for item in items_raw]
        exam_id = str(data.get("exam_id", "")).strip()
        if not exam_id:
            raise ValueError("Scribe output missing 'exam_id'.")
        return ScribeOutput(exam_id=exam_id, items=items)


DEFAULT_CONFIDENCE_THRESHOLD = 80.0


@dataclass
class GradeItem:
    question_id: str
    awarded_points: float
    max_points: float
    verdict: str
    feedback: str
    confidence: float = 100.0
    flagged_for_review: bool = False

    @staticmethod
    def from_dict(
        data: Dict[str, Any],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> "GradeItem":
        confidence = float(data.get("confidence", 100.0))
        verdict = str(data.get("verdict", "")).strip()
        flagged = confidence < confidence_threshold or verdict == "partially_correct"
        return GradeItem(
            question_id=str(data.get("question_id", "")).strip(),
            awarded_points=float(data.get("awarded_points", 0)),
            max_points=float(data.get("max_points", 0)),
            verdict=verdict,
            feedback=str(data.get("feedback", "")).strip(),
            confidence=confidence,
            flagged_for_review=flagged,
        )


@dataclass
class GradeOutput:
    exam_id: str
    items: List[GradeItem]

    @staticmethod
    def from_dict(
        data: Dict[str, Any],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> "GradeOutput":
        items_raw = data.get("items", [])
        if not isinstance(items_raw, list):
            raise ValueError("Grade output must contain a list at key 'items'.")

        items = [
            GradeItem.from_dict(item, confidence_threshold=confidence_threshold)
            for item in items_raw
        ]
        exam_id = str(data.get("exam_id", "")).strip()
        if not exam_id:
            raise ValueError("Grade output missing 'exam_id'.")
        return GradeOutput(exam_id=exam_id, items=items)

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

