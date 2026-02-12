# AI Assembly Line for Exam Grading

Two-stage grading pipeline:
1. `ExtractionAgent` (scribe): cleans OCR noise and outputs structured question/answer JSON.
2. `GradingAgent` (professor): scores extracted answers against answer key and rubric.
3. `run_pipeline.py` (manager): orchestrates both stages and saves reports.

## Why this architecture
- Prevents grading from being polluted by OCR cleanup decisions.
- Lets you tune extraction and grading independently.
- Produces audit-friendly artifacts (extracted text and grading output).

## Project layout
```
src/ai_assembly_line/
  agents.py
  llm_client.py
  pipeline.py
  schemas.py
examples/
  config/
    answer_key.json
    rubric.txt
  input/
    student_001.txt
run_pipeline.py
```

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up your environment variables:
   Create a `.env` file in the root directory and add your Gemini API key:
```bash
GEMINI_API_KEY="your_actual_key_here"
```

## Run
```bash
python run_pipeline.py \
  --input-dir examples/input \
  --answer-key examples/config/answer_key.json \
  --rubric examples/config/rubric.txt \
  --output-dir output \
  --extract-model gemini-2.5-flash \
  --grade-model gemini-2.5-flash
```

## Outputs
- `output/<exam_id>_report.json`: extracted text, per-question scores, confidence, and feedback.
- `output/grades_summary.csv`: one-line summary per exam (includes `flagged_count`).
- `output/review_queue.json`: all questions flagged for human review across all exams.

## Answer key format
`answer_key.json` must contain:
```json
{
  "questions": {
    "Q1": {
      "reference_answer": "Force is a push or pull.",
      "max_points": 5,
      "must_include": ["push", "pull"]
    }
  }
}
```
## How It Works

The pipeline processes student exams in two distinct stages to ensure accuracy and modularity.

### 1. Extraction Stage (Scribe)
- **Input**: Raw text checksums from OCR files (e.g., `examples/input/student_001.txt`).
- **Process**: The `ExtractionAgent` uses **Gemini 2.5 Flash** to clean up OCR errors (like typos or misaligned text) and structure the unstructured text into a standard JSON format.
- **Output**: A JSON object containing the student's answers, keyed by Question ID (e.g., "Q1", "Q2"), along with any transcription notes.

### 2. Grading Stage (Professor)
- **Input**: The structured JSON from the extraction stage, the `answer_key.json`, and the `rubric.txt`.
- **Process**: The `GradingAgent` uses **Gemini 2.5 Flash** to evaluate each student answer against the reference answer and rubric criteria. It checks for key concepts, partial credit rules, and specific constraints (e.g., "must include 'powerhouse'").
- **Output**: A final report containing the score, percentage, verdict (Correct/Partially Correct/Incorrect), and specific feedback for each question.

### Configuration Files
- **`answer_key.json`**: Defines the "Gold Standard" answers, maximum points, and required keywords. Keys must match the Question IDs found in the exam (e.g., "Q1").
- **`rubric.txt`**: Natural language instructions for the AI grader, defining the strictness and style of grading (e.g., "Partial credit for key concepts").

### Recent Updates (Gemini Migration)
- **Model**: Switched from OpenAI (GPT-4) to **Google Gemini 2.5 Flash** for faster and more cost-effective processing.
- **SDK**: Migrated to the `google-genai` Python SDK.
- **Security**: API keys are now managed via a `.env` file, ensuring they are never committed to version control.

## Human-in-the-Loop Review

The pipeline includes a confidence-based review system to ensure AI grades are trustworthy.

### How it works
1. The grading model outputs a **confidence score** (0–100) for each question it grades.
2. Any question with confidence **below the threshold** (default: 80%) or graded as `partially_correct` is **flagged for review**.
3. All flagged items are collected into `output/review_queue.json` for a human reviewer.

### Customizing the threshold
```bash
python run_pipeline.py --confidence-threshold 90
```
A higher threshold flags more items; a lower threshold flags fewer.

### Example output
```
[OK] student_001: 7.00/10.00 (70.00%) ⚠️  1 flagged for review
[DONE] Summary written to output/grades_summary.csv
[REVIEW] 1 item(s) need human review → output/review_queue.json
```

You can add any extra grading metadata (`keywords`, `common_mistakes`, etc.); the grading agent receives it.

## Advanced Analytics

After grading, run the analytics script to get class-level insights and question difficulty analysis:

```bash
python run_analytics.py --output-dir output
```

### What it produces
- **Class Summary**: Overall average, highest/lowest scores
- **Per-Question Breakdown**: Average score, pass rate, difficulty rating (Easy/Medium/Hard), verdict distribution
- **Actionable Insights**: Identifies which topics need reteaching based on miss rates
- **JSON Export**: `output/analytics_report.json` for programmatic use

### Example output
```
📊  CLASS ANALYTICS REPORT
============================================================
📋 Class Summary
   Students:       4
   Class Average:  55.0%
   Highest Score:  100.0%
   Lowest Score:   0.0%

📝 Per-Question Breakdown
   Q1  3.75/5.0  75.0% pass  Medium  3 correct, 1 wrong
   Q2  1.75/5.0  25.0% pass  Hard    1 correct, 1 partial, 2 wrong

💡 Insights
   1. 📊 Class average is 55.0% — acceptable but room for improvement.
   2. 🔴 Q2: 75% of students missed this question. Consider reteaching.
```
