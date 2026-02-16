#!/usr/bin/env python3
"""Advanced Analytics: Class Insights and Difficulty Analysis.

Reads graded report JSONs from the output directory and produces:
- Per-question statistics (avg score, pass rate, difficulty rating)
- Class-level insights (overall avg, common missed questions)
- Actionable teacher recommendations

Usage:
    python run_analytics.py --output-dir output
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate class analytics from graded reports.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory containing *_report.json files.",
    )
    return parser.parse_args()


def load_reports(output_dir: Path) -> List[Dict[str, Any]]:
    """Load all *_report.json files from the output directory."""
    reports = []
    for path in sorted(output_dir.glob("*_report.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        reports.append(data)
    return reports


def compute_question_stats(reports: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Compute per-question statistics across all students."""
    question_data: Dict[str, Dict[str, list]] = defaultdict(
        lambda: {
            "scores": [],
            "max_points": 0.0,
            "verdicts": [],
            "confidences": [],
            "feedbacks": [],
        }
    )

    for report in reports:
        for item in report.get("graded_items", []):
            qid = item["question_id"]
            question_data[qid]["scores"].append(item["awarded_points"])
            question_data[qid]["max_points"] = item["max_points"]
            question_data[qid]["verdicts"].append(item["verdict"])
            question_data[qid]["confidences"].append(item.get("confidence", 100.0))
            question_data[qid]["feedbacks"].append(item.get("feedback", ""))

    stats: Dict[str, Dict[str, Any]] = {}
    for qid in sorted(question_data.keys()):
        data = question_data[qid]
        scores = data["scores"]
        max_pts = data["max_points"]
        total_students = len(scores)
        avg_score = sum(scores) / total_students if total_students > 0 else 0.0
        score_pct = (avg_score / max_pts * 100) if max_pts > 0 else 0.0
        full_marks_count = sum(1 for s in scores if s >= max_pts)
        zero_count = sum(1 for s in scores if s <= 0)
        pass_count = sum(1 for s in scores if s >= max_pts * 0.5)
        pass_rate = (pass_count / total_students * 100) if total_students > 0 else 0.0
        avg_confidence = (
            sum(data["confidences"]) / total_students if total_students > 0 else 0.0
        )

        # Difficulty rating based on score percentage
        if score_pct >= 80:
            difficulty = "Easy"
        elif score_pct >= 50:
            difficulty = "Medium"
        else:
            difficulty = "Hard"

        stats[qid] = {
            "total_students": total_students,
            "max_points": max_pts,
            "avg_score": round(avg_score, 2),
            "avg_score_pct": round(score_pct, 1),
            "full_marks_count": full_marks_count,
            "zero_count": zero_count,
            "pass_rate": round(pass_rate, 1),
            "avg_confidence": round(avg_confidence, 1),
            "difficulty": difficulty,
            "verdict_breakdown": {
                "correct": sum(1 for v in data["verdicts"] if v == "correct"),
                "partially_correct": sum(
                    1 for v in data["verdicts"] if v == "partially_correct"
                ),
                "incorrect": sum(1 for v in data["verdicts"] if v == "incorrect"),
            },
        }

    return stats


def compute_class_stats(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute class-level statistics."""
    if not reports:
        return {"total_students": 0}

    percentages = [r.get("percentage", 0.0) for r in reports]
    totals_awarded = [r.get("total_awarded", 0.0) for r in reports]
    totals_max = [r.get("total_max", 0.0) for r in reports]
    n = len(reports)

    return {
        "total_students": n,
        "class_average_pct": round(sum(percentages) / n, 1),
        "highest_score": round(max(percentages), 1),
        "lowest_score": round(min(percentages), 1),
        "total_possible": totals_max[0] if totals_max else 0.0,
        "avg_total_awarded": round(sum(totals_awarded) / n, 2),
    }


def generate_insights(
    class_stats: Dict[str, Any],
    question_stats: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Generate actionable teacher insights."""
    insights: List[str] = []

    # Class-level insights
    avg = class_stats.get("class_average_pct", 0.0)
    if avg < 50:
        insights.append(
            f"⚠️ Class average is {avg}% — below passing. Consider reviewing core material."
        )
    elif avg < 70:
        insights.append(
            f"📊 Class average is {avg}% — acceptable but room for improvement."
        )
    else:
        insights.append(f"✅ Class average is {avg}% — solid performance overall.")

    # Per-question insights
    for qid, qs in question_stats.items():
        n = qs["total_students"]
        incorrect = qs["verdict_breakdown"]["incorrect"]
        partial = qs["verdict_breakdown"]["partially_correct"]
        miss_rate = ((incorrect + partial) / n * 100) if n > 0 else 0.0

        if miss_rate >= 50:
            insights.append(
                f"🔴 {qid}: {miss_rate:.0f}% of students missed this question "
                f"(avg {qs['avg_score']}/{qs['max_points']}). "
                f"Difficulty: {qs['difficulty']}. Consider reteaching this topic."
            )
        elif qs["difficulty"] == "Easy" and qs["full_marks_count"] == n:
            insights.append(
                f"🟢 {qid}: All students got full marks. "
                f"Consider increasing difficulty."
            )

    # Difficulty distribution
    difficulties = [qs["difficulty"] for qs in question_stats.values()]
    hard_count = difficulties.count("Hard")
    if hard_count > len(difficulties) / 2:
        insights.append(
            f"⚠️ {hard_count}/{len(difficulties)} questions rated Hard. "
            f"The exam may be too difficult overall."
        )

    return insights


def print_analytics(
    class_stats: Dict[str, Any],
    question_stats: Dict[str, Dict[str, Any]],
    insights: List[str],
) -> None:
    """Print a formatted analytics report to the terminal."""
    print("\n" + "=" * 60)
    print("📊  CLASS ANALYTICS REPORT")
    print("=" * 60)

    # Class summary
    print(f"\n📋 Class Summary")
    print(f"   Students:       {class_stats['total_students']}")
    print(f"   Class Average:  {class_stats['class_average_pct']}%")
    print(f"   Highest Score:  {class_stats['highest_score']}%")
    print(f"   Lowest Score:   {class_stats['lowest_score']}%")

    # Per-question table
    print(f"\n📝 Per-Question Breakdown")
    print(f"   {'Question':<10} {'Avg Score':<12} {'Pass Rate':<12} {'Difficulty':<12} {'Correct':<10} {'Partial':<10} {'Wrong':<10}")
    print(f"   {'─' * 10} {'─' * 12} {'─' * 12} {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10}")
    for qid, qs in question_stats.items():
        vb = qs["verdict_breakdown"]
        print(
            f"   {qid:<10} "
            f"{qs['avg_score']:>4}/{qs['max_points']:>4}     "
            f"{qs['pass_rate']:>5}%      "
            f"{qs['difficulty']:<12} "
            f"{vb['correct']:<10} "
            f"{vb['partially_correct']:<10} "
            f"{vb['incorrect']:<10}"
        )

    # Insights
    print(f"\n💡 Insights")
    for i, insight in enumerate(insights, 1):
        print(f"   {i}. {insight}")

    print("\n" + "=" * 60)


def save_analytics_json(
    path: Path,
    class_stats: Dict[str, Any],
    question_stats: Dict[str, Dict[str, Any]],
    insights: List[str],
) -> None:
    """Save analytics to a JSON file."""
    payload = {
        "class_summary": class_stats,
        "question_stats": question_stats,
        "insights": insights,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    reports = load_reports(args.output_dir)

    if not reports:
        print(f"[ERROR] No *_report.json files found in {args.output_dir}")
        return

    class_stats = compute_class_stats(reports)
    question_stats = compute_question_stats(reports)
    insights = generate_insights(class_stats, question_stats)

    print_analytics(class_stats, question_stats, insights)

    analytics_path = args.output_dir / "analytics_report.json"
    save_analytics_json(analytics_path, class_stats, question_stats, insights)
    print(f"[DONE] Analytics saved to {analytics_path}")


if __name__ == "__main__":
    main()
