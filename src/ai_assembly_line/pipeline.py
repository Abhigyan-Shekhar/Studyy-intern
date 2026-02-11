from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .agents import ExtractionAgent, GradingAgent
from .schemas import GradeOutput, ScribeOutput


class GradingPipeline:
    def __init__(self, extraction_agent: ExtractionAgent, grading_agent: GradingAgent):
        self.extraction_agent = extraction_agent
        self.grading_agent = grading_agent

    def run_one(
        self,
        *,
        exam_id: str,
        raw_text: str,
        answer_key: Dict[str, Dict[str, Any]],
        rubric_text: str,
    ) -> tuple[ScribeOutput, GradeOutput]:
        scribe_output = self.extraction_agent.run(exam_id=exam_id, raw_text=raw_text)
        grade_output = self.grading_agent.run(
            scribe_output=scribe_output,
            answer_key=answer_key,
            rubric_text=rubric_text,
        )
        return scribe_output, grade_output


def load_answer_key(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload.get("questions", {})
    if not isinstance(questions, dict):
        raise ValueError("Answer key must contain object field `questions`.")
    normalized: Dict[str, Dict[str, Any]] = {}
    for qid, qmeta in questions.items():
        normalized[str(qid)] = dict(qmeta)
    return normalized


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
        "item_breakdown",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)

