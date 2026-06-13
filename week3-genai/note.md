
---

## 1. Text-to-SQL Project Structure
- **`app/main.py`** - FastAPI entry point; creates the app instance and registers routes.
- **`app/agent/`** - LLM orchestration, prompt building, and prompt-chaining logic.
- **`app/db/`** - Schema inspection, database session handling, and SQL execution helpers.
- **`app/schema/`** - Pydantic request, response, and query-plan models.
- **`app/sql/`** - SQL safety validation and normalization rules.
- **`app/core/`** - Shared settings and logging configuration.
- **`streamlit_app.py`** - Simple UI for asking questions and viewing generated SQL/results.
- **`scripts/run_benchmark.py`** - Benchmark runner for evaluating the agent on the provided dataset.

---

## 2. Application Lifecycle and Configuration
- **FastAPI app** - Created once in `main.py` using settings from `app.core.config`.
- **CORS middleware** - Allows the Streamlit UI and local frontend origins to call the API.
- **Environment settings** - Loaded from `.env` with values like `DATABASE_URL`, `HUGGINGFACE_API_KEY`, `HF_MODEL`, and `AGENT_MAX_RETRIES`.
- **Why it matters:** Centralized settings keep the agent, API, and UI aligned across environments.

---

## 3. API Design and Endpoints
- **`GET /health`** - Lightweight health check for the service.
- **`POST /agent/sql`** - Runs the full text-to-SQL pipeline and returns a structured response.
- **`POST /agent/sql/stream`** - Streams intermediate chain updates as NDJSON.
- **`response_model`** - Ensures the final response follows the `QueryResponse` schema.
- **Why it matters:** The API exposes both a simple request/response mode and a streaming mode for debugging.

---

## 4. Prompt Chaining and LLM Flow
- **`TextToSQLAgent`** - High-level orchestrator that delegates to `PromptChain`.
- **`PromptChain`** - Runs the full decomposition -> SQL generation -> validation -> execution -> repair loop.
- **Schema introspection** - The agent reads table and foreign-key metadata before prompting the model.
- **Repair loop** - Failed executions can be retried with an LLM-generated repair prompt.
- **Why it matters:** The model is guided step by step instead of being asked to generate SQL in one shot.

---

## 5. Request Dependencies and Database Sessions
- **`QueryRequest`** - Accepts a natural language question from the client.
- **`AsyncSessionLocal`** - Used by the schema inspector and SQL executor for database access.
- **Session flow:** open session -> inspect schema or run SQL -> close session.
- **Why it matters:** Database work stays isolated and asynchronous, which fits FastAPI and the agent pipeline.

---

## 6. Schemas and Validation
- **`QueryPlan`** - Structured decomposition of the user question into intent, tables, columns, joins, filters, and aggregation.
- **`QueryResponse`** - Returns the question, generated SQL, result, summary, errors, attempts, and execution metadata.
- **`from pydantic import BaseModel`** - Provides validation and serialization for agent inputs and outputs.
- **`model_dump()`** - Used when streaming to turn Pydantic models into JSON-safe payloads.
- **Why it matters:** Typed schemas keep the chain outputs predictable and easier to debug.

---

## 7. SQL Safety and Execution
- **`SQLValidator`** - Normalizes SQL, strips fences, and checks that only safe `SELECT` statements are allowed.
- **Forbidden patterns** - Rejects semicolons, comments, and dangerous keywords.
- **`SQLExecutor`** - Runs the validated query and serializes rows for JSON responses.
- **Value conversion** - Decimal and date/time values are converted into JSON-friendly types.
- **Why it matters:** The model can propose SQL, but the app still enforces a safety boundary before execution.

---

## 8. Schema Inspection and Query Context
- **`SchemaInspector`** - Reads `information_schema` to discover tables, columns, and foreign keys at runtime.
- **Schema cache** - Reuses the formatted schema context after the first load.
- **Join hints** - Foreign-key relationships are included in the prompt context to improve SQL generation.
- **Why it matters:** The agent works from the live database structure instead of hardcoded table descriptions.

---

## 9. Logging and Error Handling
- **`app.core.logging`** - Central place for runtime logging.
- **Step logs** - Prompt chain steps are written to `logs/prompt_chain/` and aggregated in `logs/prompts.jsonl`.
- **Warnings and errors** - Capture failed decomposition, invalid SQL, and execution failures.
- **Why it matters:** Prompt-chaining systems need traceability, especially when failures come from the model rather than the database.

---

## 10. Frontend and Benchmark Integration
- **Streamlit UI** - Gives a quick interface for asking questions without using Swagger or curl.
- **Benchmark datasets** - Stored under `benchmark/` for repeatable evaluation.
- **Benchmark reports** - Results are written to `reports/` for later review.
- **Why it matters:** The project is both an interactive demo and an evaluation workflow.

---

## 11. Data Modeling Checklist
- Is the input a natural language question that fits `QueryRequest`?
- Are schema details loaded before SQL generation?
- Is the model constrained to a single safe `SELECT` statement?
- Are failed executions handled with repair attempts instead of silent crashes?
- Are results serialized into JSON-safe values?
- Are intermediate prompt-chain steps visible for debugging?
- Does the UI or API expose enough metadata to understand why a query succeeded or failed?

---

## One-line summary of all terms

| Term | Meaning |
|------|---------|
| Text-to-SQL | Converting a natural language question into SQL |
| Prompt chain | Multi-step LLM workflow with intermediate stages |
| Query plan | Structured breakdown of the question |
| Schema inspection | Reading live database metadata for context |
| SQL validation | Safety check before execution |
| Repair loop | Retry path that asks the model to fix failed SQL |
| NDJSON | Newline-delimited JSON used for streaming updates |
| `QueryRequest` | Request schema containing the user question |
| `QueryResponse` | Final structured response from the agent |
| `QueryPlan` | Pydantic model for the decomposition step |
| `SQLExecutor` | Executes validated SQL against the database |
| `SchemaInspector` | Builds schema context from `information_schema` |
| `SQLValidator` | Normalizes and filters generated SQL |
| Streamlit | Python UI framework used for the frontend |
| Benchmarking | Repeating tests to measure agent quality |

---
