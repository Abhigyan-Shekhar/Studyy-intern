#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from src.ai_assembly_line import ExtractionAgent, GradingAgent, GradingPipeline
from src.ai_assembly_line.llm_client import LLMClient
from src.ai_assembly_line.pipeline import (
    load_answer_key,
    save_exam_report,
    save_review_queue,
    save_summary_csv,
)
from src.ai_assembly_line.single_shot_agent import SingleShotAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run two-stage AI exam grading pipeline.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("examples/input"),
        help="Folder containing OCR text files.",
    )
    parser.add_argument(
        "--glob",
        type=str,
        default="*.txt",
        help="Glob pattern for input files.",
    )
    parser.add_argument(
        "--answer-key",
        type=Path,
        default=Path("examples/config/answer_key.json"),
        help="Answer key JSON file.",
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path("examples/config/rubric.txt"),
        help="Rubric text file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory for reports.",
    )
    parser.add_argument(
        "--extract-model",
        type=str,
        default="gemini-2.5-flash",
        help="Model used for extraction stage.",
    )
    parser.add_argument(
        "--grade-model",
        type=str,
        default="gemini-2.5-flash",
        help="Model used for grading stage.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["pipeline", "single-shot"],
        default="pipeline",
        help="Execution mode: 'pipeline' (2-stage) or 'single-shot' (1-stage).",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Optional OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=80.0,
        help="Flag questions with confidence below this threshold for review (0-100).",
    )
    return parser.parse_args()


def build_item_breakdown(grade_output) -> str:
    parts = [
        f"{item.question_id}:{item.awarded_points:g}/{item.max_points:g}"
        for item in grade_output.items
    ]
    return "; ".join(parts)


def main() -> None:
    args = parse_args()
    answer_key = load_answer_key(args.answer_key)
    rubric_text = args.rubric.read_text(encoding="utf-8")

    extraction_client = LLMClient(model=args.extract_model, base_url=args.base_url)
    grading_client = LLMClient(model=args.grade_model, base_url=args.base_url)

    if args.mode == "pipeline":
        extraction_agent = ExtractionAgent(extraction_client)
        grading_agent = GradingAgent(grading_client)
        pipeline = GradingPipeline(extraction_agent, grading_agent)
        print(f"🚀 Running in 2-stage PIPELINE mode...")
    else:
        # In single-shot, we use the grade_model for the combined task
        pipeline = SingleShotAgent(grading_client)
        print(f"🚀 Running in 1-stage SINGLE-SHOT mode...")

    inputs = sorted(args.input_dir.glob(args.glob))
    if not inputs:
        raise FileNotFoundError(
            f"No files matched {args.glob!r} in directory {str(args.input_dir)!r}."
        )

    summary_rows: List[Dict[str, object]] = []
    all_review_items: List[Dict[str, object]] = []

    for file_path in inputs:
        exam_id = file_path.stem
        raw_text = file_path.read_text(encoding="utf-8")

        scribe_output, grade_output = pipeline.run_one(
            exam_id=exam_id,
            raw_text=raw_text,
            answer_key=answer_key,
            rubric_text=rubric_text,
            confidence_threshold=args.confidence_threshold,
        )

        report_path = args.output_dir / f"{exam_id}_report.json"
        save_exam_report(report_path, scribe_output, grade_output)

        summary_rows.append(
            {
                "exam_id": exam_id,
                "total_awarded": f"{grade_output.total_awarded:.2f}",
                "total_max": f"{grade_output.total_max:.2f}",
                "percentage": f"{grade_output.percentage:.2f}",
                "flagged_count": grade_output.flagged_count,
                "item_breakdown": build_item_breakdown(grade_output),
            }
        )

        # Collect flagged items for the review queue
        for item in grade_output.flagged_items:
            all_review_items.append(
                {
                    "exam_id": exam_id,
                    "question_id": item.question_id,
                    "awarded_points": item.awarded_points,
                    "max_points": item.max_points,
                    "verdict": item.verdict,
                    "confidence": item.confidence,
                    "feedback": item.feedback,
                }
            )

        # Print result with flagged markers
        flag_info = ""
        if grade_output.flagged_count > 0:
            flag_info = f" \u26a0\ufe0f  {grade_output.flagged_count} flagged for review"
        print(
            f"[OK] {exam_id}: {grade_output.total_awarded:.2f}/{grade_output.total_max:.2f} "
            f"({grade_output.percentage:.2f}%){flag_info}"
        )

    summary_path = args.output_dir / "grades_summary.csv"
    save_summary_csv(summary_path, summary_rows)
    print(f"[DONE] Summary written to {summary_path}")

    # Save review queue
    review_path = args.output_dir / "review_queue.json"
    save_review_queue(review_path, all_review_items)
    if all_review_items:
        print(f"[REVIEW] {len(all_review_items)} item(s) need human review → {review_path}")
    else:
        print(f"[REVIEW] No items flagged for review. All grades are high-confidence.")


if __name__ == "__main__":
    main()

