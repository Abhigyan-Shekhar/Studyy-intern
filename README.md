# AI Assembly Line for Exam Grading

AI-powered exam grading pipeline that reads **raw, unstructured OCR text**, segments question–answer pairs, and grades them using **Google Gemini** — all in a **single LLM call**.

Built with **LangChain**, **Pydantic**, and **LCEL** (LangChain Expression Language).

## Key Features

- **Q&A Segmentation** — Analyzes textual structure and semantic intent to segment question–answer pairs, even when formatting is inconsistent or informal (numbered, lettered, dashed, or completely unlabeled).
- **Rubric-Only Grading** — No answer key required. Grades are based purely on the rubric.
- **Pydantic Structured Output** — Uses `PydanticOutputParser` to inject format instructions into the prompt and parse the LLM response into typed Python objects.
- **LCEL Chain** — Composable `prompt | llm | parser` pipeline using LangChain Expression Language.
- **Human-in-the-Loop Review** — Confidence-based flagging system routes uncertain grades to a human reviewer.
- **Progress Bar** — `tqdm` progress bar for batch grading.
- **Proper Logging** — Uses Python's `logging` module instead of `print()`.

## Project Layout

```
src/ai_assembly_line/
  single_shot_agent.py   # SingleShotAgent — Q&A segmentation + grading
  pydantic_models.py     # Pydantic schemas for LLM output + internal models
  pipeline.py            # Report saving utilities (JSON, CSV, review queue)
  __init__.py
examples/
  config/
    rubric.txt           # Grading rubric (sole grading criteria)
  input/
    student_001.txt      # Messy OCR with numbered format + metadata
    student_002.txt      # Plain text questions, no numbering
    student_003.txt      # Completely unlabeled, no structure
    student_004.txt      # Lettered (a)/(b) format with OCR noise
run_pipeline.py          # Main CLI entry point
requirements.txt
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Gemini API key:
```bash
GEMINI_API_KEY="your_actual_key_here"
```

## Usage

```bash
python run_pipeline.py \
  --input-dir examples/input \
  --rubric examples/config/rubric.txt \
  --output-dir output \
  --model gemini-2.5-flash
```

### CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--input-dir` | `examples/input` | Folder containing OCR text files |
| `--glob` | `*.txt` | Glob pattern for input files |
| `--rubric` | `examples/config/rubric.txt` | Rubric text file |
| `--output-dir` | `output` | Output directory for reports |
| `--model` | `gemini-2.5-flash` | Gemini model to use |
| `--confidence-threshold` | `80.0` | Flag grades below this confidence (0–100) |

## How It Works

### Architecture

```
Raw OCR Text → [ChatPromptTemplate] → [ChatGoogleGenerativeAI] → [PydanticOutputParser] → Reports
                    ↑                                                     ↑
               rubric.txt                                        ExamResult (Pydantic)
               format_instructions
```

This is implemented as an **LCEL chain**:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

parser = PydanticOutputParser(pydantic_object=ExamResult)

chain = prompt | llm | parser
result = chain.invoke({...})
```

### Step-by-Step

1. **Input**: Raw, unstructured OCR text and a `rubric.txt`.
2. **Q&A Segmentation**: The LLM analyzes textual structure and semantic intent to identify question–answer pairs — ignoring metadata (student name, roll number, class, date) and handling any formatting style.
3. **OCR Denoising**: Corrects typos and OCR artifacts (e.g., `"pul"` → `"pull"`, `"ceII"` → `"cell"`, `"powerh0use"` → `"powerhouse"`).
4. **Rubric-Based Grading**: Each answer is graded strictly against the rubric with a confidence score (0–100).
5. **Structured Output**: `PydanticOutputParser` injects format instructions into the prompt and parses the response into a validated `ExamResult` object.
6. **Reports**: Per-student JSON reports, summary CSV, and a review queue for flagged items.

### Rubric Format

`rubric.txt` contains natural language grading instructions. This is the **sole grading criteria** — no answer key is used.

```
Grade each question independently.
- Award points only for content present in student_answer.
- Determine max_points based on the complexity and scope of each question.
- Verdict must be one of: correct, partially_correct, incorrect.
- Award partial credit when a student demonstrates understanding of key concepts.
```

## Outputs

| File | Description |
|---|---|
| `output/<exam_id>_report.json` | Extracted answers, scores, verdicts, confidence, feedback |
| `output/grades_summary.csv` | One-line summary per exam with flagged count |
| `output/review_queue.json` | All questions flagged for human review |

## Human-in-the-Loop Review

The pipeline includes a confidence-based review system:

1. The LLM assigns a **confidence score** (0–100) for each graded question.
2. Questions with confidence **below the threshold** (default: 80%) or graded as `partially_correct` are **flagged for review**.
3. Flagged items are collected into `output/review_queue.json`.

```bash
# Flag more items (stricter threshold)
python run_pipeline.py --confidence-threshold 90
```

### Example Output

```
Evaluating Exams: 100%|██████████| 4/4
INFO:__main__:student_001: 4.00/4.00 (100.00%)
INFO:__main__:student_002: 5.00/5.00 (100.00%)
INFO:__main__:student_003: 0.00/4.00 (0.00%)
INFO:__main__:student_004: 1.00/2.00 (50.00%)
INFO:__main__:Summary written to output/grades_summary.csv
INFO:__main__:No items flagged for review. All grades are high-confidence.
```

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Google Gemini 2.5 Flash via `langchain-google-genai` |
| Orchestration | LangChain LCEL (`prompt \| llm \| parser`) |
| Prompt Templating | `ChatPromptTemplate` |
| Output Parsing | `PydanticOutputParser` (format instructions injected into prompt) |
| Data Models | Pydantic `BaseModel` |
| Progress Bar | `tqdm` |
| Logging | Python `logging` module |
| API Key Management | `python-dotenv` (`.env` file) |
