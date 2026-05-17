# Text-to-SQL Agent

This project replaces the earlier rule-based SQL generator with a Hugging Face Inference API-backed text-to-SQL agent.

## Pipeline

1. Inspect the PostgreSQL schema at runtime.
2. Ask the model to decompose the question into a structured query plan.
3. Ask the model to generate a single PostgreSQL `SELECT` statement.
4. Validate the SQL for safety.
5. Execute the query.
6. Retry with a repair prompt if execution fails.
7. Return the SQL, result, summary, and execution metadata.

## Environment

Copy `.env.example` to `.env` and set:

- `DATABASE_URL`
- `HUGGINGFACE_API_KEY`
- `HF_MODEL`
- `AGENT_MAX_RETRIES`

## Run the API

```bash
uvicorn app.main:app --reload
```

`POST /agent/sql`

```json
{
  "question": "How many shipped orders are from USA customers?"
}
```

## Benchmark

Run the benchmark evaluation against the provided dataset:

```bash
python scripts/run_benchmark.py
```

Results are written to `evaluation/benchmark_results.json` and `evaluation/benchmark_results.csv`.

## Notes

- Only `SELECT` statements are allowed.
- Logs are written to `logs/text2sql.log`.
- The retry loop is bounded and uses LLM-based repair instead of hardcoded rules.