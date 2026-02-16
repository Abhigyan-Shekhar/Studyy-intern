# AI Assembly Line for Exam Grading

AI-powered exam grading pipeline using **Google Gemini 2.5 Flash**.

Performs OCR text extraction and grading in a **single LLM call** using **Pydantic** structured output and **Gemini's native schema enforcement**.

## Project layout
```
src/ai_assembly_line/
  single_shot_agent.py   # SingleShotAgent — extraction + grading in one pass
  pydantic_models.py     # Pydantic schemas for structured output
  llm_client.py          # Gemini API wrapper with retry logic
  pipeline.py            # Report saving utilities
  schemas.py             # Dataclass schemas for internal data
examples/
  config/
    answer_key.json
    rubric.txt
  input/
    student_001.txt
    student_002.txt
    student_003.txt
    student_004.txt
run_pipeline.py            # Main CLI entry point
```

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Set up your environment variables:
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
  --model gemini-2.5-flash
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

The pipeline processes student exams in a single pass using the **SingleShotAgent**:

1. **Input**: Raw OCR text (e.g., `examples/input/student_001.txt`), the `answer_key.json`, and the `rubric.txt`.
2. **Process**: The `SingleShotAgent` sends everything to **Gemini 2.5 Flash** in one call. The model simultaneously:
   - Denoises the OCR text (e.g., "Defne" → "Define", "pul" → "pull")
   - Extracts the student's answers
   - Grades each answer against the answer key and rubric
3. **Structured Output**: The response is enforced via a **Pydantic** schema (`ExamResult`), so the JSON is always valid.
4. **Output**: A report with scores, verdicts, confidence scores, and feedback per question.

### Configuration Files
- **`answer_key.json`**: Defines the reference answers, maximum points, and required keywords.
- **`rubric.txt`**: Natural language instructions for the AI grader (e.g., "Partial credit for key concepts").

### Key Features
- **Pydantic Integration**: Output schemas are enforced via `pydantic.BaseModel` and Gemini's native `response_schema` parameter.
- **Rate Limit Handling**: Automatic retry with exponential backoff for API rate limits.
- **Security**: API keys managed via `.env` file (never committed to version control).

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
[OK] student_001: 7.50/10.00 (75.00%) ⚠️  1 flagged for review
[DONE] Summary written to output/grades_summary.csv
[REVIEW] 1 item(s) need human review → output/review_queue.json
```
