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
- `output/<exam_id>_report.json`: extracted text, per-question scores, and feedback.
- `output/grades_summary.csv`: one-line summary per exam.

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

You can add any extra grading metadata (`keywords`, `common_mistakes`, etc.); the grading agent receives it.

