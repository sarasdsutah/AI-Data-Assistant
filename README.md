# AI Product Insights Assistant

This repo now contains a starter assistant for product analytics workflows:

- ingest a user-behavior dataset
- retrieve relevant context from product and experiment docs
- generate churn and retention insights
- run a small evaluation harness
- analyze uploaded datasets through a local web UI

## What It Includes

- `data/users.csv`: sample SaaS usage and churn data
- `knowledge/*.md`: internal docs used as retrieval context
- `src/product_insights_assistant/`: retrieval, analysis, evaluation, and CLI code
- `src/product_insights_assistant/webapp.py`: browser-based UI for uploads and analysis

The assistant works in two modes:

1. Fallback mode: deterministic, offline, no external dependencies
2. OpenAI mode: uses an LLM if you set `OPENAI_API_KEY` and pass `--model`

## Quick Start

Run a single analysis:

```bash
PYTHONPATH=src python -m product_insights_assistant.cli \
  --question "Based on current behavior and prior experiments, what should we do next?"
```

Run the lightweight evaluation suite:

```bash
PYTHONPATH=src python -m product_insights_assistant.cli --eval
```

Pass business context through the CLI:

```bash
PYTHONPATH=src python -m product_insights_assistant.cli \
  --data data/users.csv \
  --business-context "This is a SaaS activation dataset. We care about first-30-day churn." \
  --question "What patterns and experiments should the product team focus on?"
```

Run the local web UI:

```bash
PYTHONPATH=src python -m product_insights_assistant.webapp
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000), upload a CSV, describe the dataset or business context, and submit a question.

Use an OpenAI model:

```bash
pip install -e ".[llm]"
export OPENAI_API_KEY=your_key_here
PYTHONPATH=src python -m product_insights_assistant.cli \
  --model gpt-4.1 \
  --question "Which users are most likely to churn and what experiment should we run?"
```

## How The Architecture Maps To Your Idea

### 1. Dataset

The assistant reads a CSV with fields like:

- `user_id`
- `week1_usage`
- `week2_usage`
- `churned`

You can replace `data/users.csv` with a Kaggle export or your own warehouse extract.
The UI also accepts arbitrary CSVs and will fall back to a generic dataset summary when the schema is not churn-specific.

### 2. LLM Reasoning

`analysis.py` builds a prompt that combines:

- a preview of the uploaded dataset
- dataset-level summary statistics
- churn metrics when the uploaded CSV matches the starter schema
- retrieved product context
- business-context text entered by the user
- the user question

### 3. RAG

`rag.py` loads markdown docs and performs lightweight keyword retrieval.

This is intentionally simple for a starter version. The next upgrade would be:

- embeddings
- vector storage
- chunking
- metadata filters by doc type or date

### 4. Evaluation

`evaluate.py` runs a few checks against expected substrings so you can catch obvious regressions.

## Recommended Next Upgrade Paths

### A. Natural Language to SQL

Add:

- a schema description
- a query generation step
- a SQL execution sandbox
- result explanation

### B. Churn Explainer

Add:

- model scores per user
- per-user risk reasons
- recommended intervention playbooks

### C. Experiment Copilot

Add:

- experiment results ingestion
- decision rubrics
- ship / iterate / kill recommendations

## Suggested Project Structure For V2

If you keep building this out, the next step is usually:

- replace CSV with warehouse queries
- replace keyword retrieval with embeddings
- add a web UI or notebook interface
- add proper eval datasets and rubric scoring
