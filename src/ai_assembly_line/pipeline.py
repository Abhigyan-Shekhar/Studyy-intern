
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .pydantic_models import GradeOutput, ScribeOutput


def save_exam_report(path: Path, scribe_output: ScribeOutput, grade_output: GradeOutput) -> None:
    payload: Dict[str, Any] = {
        "exam_id": grade_output.exam_id,
        "total_awarded": grade_output.total_awarded,
        "total_max": grade_output.total_max,
        "percentage": grade_output.percentage,
        "extracted_items": [
            {
                "question_id": item.question_id,
                "question_text": item.question_text,
                "student_answer": item.student_answer,
                "transcription_notes": item.transcription_notes,
            }
            for item in scribe_output.items
        ],
        "graded_items": [
            {
                "question_id": item.question_id,
                "awarded_points": item.awarded_points,
                "max_points": item.max_points,
                "verdict": item.verdict,
                "feedback": item.feedback,
                "confidence": item.confidence,
                "flagged_for_review": item.flagged_for_review,
            }
            for item in grade_output.items
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def save_summary_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows_list: List[Dict[str, Any]] = list(rows)
    if not rows_list:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "exam_id",
        "total_awarded",
        "total_max",
        "percentage",
        "flagged_count",
        "item_breakdown",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)


def save_review_queue(path: Path, review_items: List[Dict[str, Any]]) -> None:
    """Write flagged items across all exams to a single review queue JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_flagged": len(review_items),
        "items": review_items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
