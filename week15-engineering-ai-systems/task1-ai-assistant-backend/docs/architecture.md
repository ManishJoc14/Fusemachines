# System Architecture

## Overall system

```mermaid
flowchart LR
  User["User"] --> Web["Next.js chat UI"]
  Web --> API["FastAPI backend"]
  API --> Auth["Google authentication"]
  API --> Chat["Chat and session services"]
  API --> Ingest["Document ingestion"]
  Chat --> Agent["Bounded assistant agent"]
  Chat --> RAG["RAG retrieval"]
  Agent --> LLM["Hugging Face or vLLM"]
  Agent --> Tools["Calculator, time, weather, Monid"]
  RAG --> Qdrant["Qdrant hybrid vectors"]
  Auth --> Postgres["PostgreSQL"]
  Chat --> Postgres
  Ingest --> Postgres
  Ingest --> Qdrant
  API --> Redis["Redis rate limits"]
```

PostgreSQL stores users, sessions, messages, document metadata, and attachment
relationships. Qdrant stores user-scoped document chunks. The backend validates
ownership before retrieval, and the browser communicates through authenticated
HTTP and Server-Sent Events.

## Agentic verification loop

```mermaid
flowchart TD
  Q["Question plus bounded RAG context"] --> Decide["Model assesses current evidence"]
  Decide -->|"Ambiguous"| Clarify["Ask one clarification question"]
  Decide -->|"Evidence needed"| Call["Choose one tool and valid arguments"]
  Call --> Execute["Execute bounded tool"]
  Execute --> Note["Structured capped observation"]
  Note --> Decide
  Decide -->|"Sufficient or limit reached"| Answer["Structured final answer"]
  Limit["Maximum tool iterations"] -.-> Decide
```

The model controls which tool to use and whether another iteration is useful.
The application controls safety: registered schemas validate arguments, external
writes are not exposed, observations are capped, and the maximum iteration count
prevents an infinite loop. Full tool results remain available in the API response
even though the model receives the bounded note.

## Retrieval and ingestion

```mermaid
flowchart LR
  Upload["Owned Markdown, text, or PDF"] --> Load["Extract text"]
  Load --> Chunk["Overlapping chunks"]
  Chunk --> Index["Dense plus BM25 vectors"]
  Index --> Qdrant["User-scoped Qdrant collection"]
  Question["Question"] --> Search["Hybrid candidate search"]
  Search --> Rerank["ColBERT reranking"]
  Rerank --> Context["Top-k cited context"]
  Qdrant --> Search
  Context --> Agent["Assistant agent"]
```

When Qdrant Cloud inference is unavailable, retrieval falls back to local dense
embeddings and cosine search. Expired documents are deleted from PostgreSQL and
Qdrant by the cleanup service.

## MLOps evaluation and promotion

```mermaid
flowchart TD
  Versions["Prompt v1, v2, v3"] --> Harness["Fixed agent evaluation cases"]
  Harness --> Loop["Real bounded agent loop"]
  Loop --> Evidence["Deterministic evidence tool"]
  Evidence --> Loop
  Loop --> Traces["Full trajectory JSON"]
  Traces --> MLflow["MLflow params, metrics, tokens, artifacts"]
  Traces --> Current["Current candidate responses"]
  Golden["Approved golden responses"] --> Judge["Evidently LLM judge"]
  Current --> Judge
  Judge --> Checks["Correctness and relevance checks"]
  Checks --> Gate{"At least 75% passed?"}
  Gate -->|"Yes"| Review["Eligible for human promotion review"]
  Gate -->|"No"| Block["Block and inspect failed traces"]
  Checks --> MLflow
```

The deterministic evidence tool keeps source behavior repeatable while the real
model still chooses tools, iterations, recovery, and termination. MLflow compares
performance and token cost across prompt versions. Evidently evaluates the saved
answers against one fixed golden set, and the promotion gate blocks versions
below the declared pass threshold. Human review remains required because the
evaluator is also an LLM.
