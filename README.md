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
2. Set API key:
```bash
export OPENAI_API_KEY="your_key_here"
```

## Run
```bash
python run_pipeline.py \
  --input-dir examples/input \
  --answer-key examples/config/answer_key.json \
  --rubric examples/config/rubric.txt \
  --output-dir output
```

## Outputs
- `output/<exam_id>_report.json`: extracted text, per-question scores, and feedback.
- `output/grades_summary.csv`: one-line summary per exam.

## Answer key format
`answer_key.json` must contain:
```json
{
  "questions": {
    "1": {
      "reference_answer": "Force is a push or pull.",
      "max_points": 5,
      "must_include": ["push", "pull"]
    }
  }
}
```

You can add any extra grading metadata (`keywords`, `common_mistakes`, etc.); the grading agent receives it.

