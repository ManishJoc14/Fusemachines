# Engineering AI Assistant Backend

A FastAPI assistant that combines retrieval-augmented generation (RAG),
structured JSON output, and external tool calling. It can use hosted models
through Hugging Face or an OpenAI-compatible model served with vLLM.

## Features

- Asynchronous FastAPI endpoints and external API clients
- Hugging Face primary and fallback models
- Optional local or remote vLLM backend
- JSON Schema-constrained assistant responses
- Multi-turn tool calling with calculator, UTC time, and live weather tools
- Markdown, text, and PDF ingestion
- Local sentence-transformer embeddings and Qdrant vector search
- Verifiable document citations in chat responses
- Docker image and optional GPU vLLM Compose profile

The detailed system diagram is in [Architecture](docs/architecture.md).

## Project structure

```text
app/
├── api/          # HTTP routes and dependencies
├── assistant/    # Prompt construction and agent/tool loop
├── core/         # Typed settings and logging
├── llm/          # Hugging Face and vLLM-compatible client
├── rag/          # Loading, chunking, embeddings, retrieval, and Qdrant
├── schemas/      # Validated request, response, and domain models
├── services/     # Chat and ingestion use cases
└── tools/        # Tool registry and individual tool implementations
data/documents/   # Example knowledge-base documents
notebooks/        # Colab vLLM deployment
scripts/          # Command-line document ingestion
```

## Requirements

- Python 3.11 or 3.12
- A Hugging Face access token, or a running vLLM endpoint
- A Qdrant Cloud cluster
- An ngrok account only when exposing vLLM from Colab

vLLM itself requires a compatible GPU for this project. It is intentionally
optional and is not started by the normal Docker Compose command.

## Local setup

From this directory, create the environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Fill in `HF_TOKEN`, `QDRANT_URL`, and `QDRANT_API_KEY`. Keep `.env` private.
Then install and start the application:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

PowerShell activation uses:

```powershell
.venv\Scripts\Activate.ps1
```

Open the API documentation at <http://localhost:8000/docs> and check health at
<http://localhost:8000/api/v1/health>.

## Ingest a document

Upload through the API:

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "accept: application/json" \
  -F "file=@data/documents/nepal_flood.md;type=text/markdown"
```

Or ingest files directly:

```bash
python scripts/ingest_documents.py data/documents/nepal_flood.md
```

The pipeline validates the file, extracts text, creates overlapping chunks,
embeds them locally, and replaces that document's vectors in Qdrant.

## Ask a question

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What caused the Nepal floods? Cite the report.",
    "history": [],
    "use_rag": true
  }'
```

Set `use_rag` to `false` for a request that should not search the knowledge
base. The response reports citations, executed tools, selected model, fallback
status, and pipeline statistics.

## LLM backends

### Hugging Face

```env
LLM_BACKEND=huggingface
HF_MODEL=openai/gpt-oss-20b:groq
HF_FALLBACK_MODEL=deepseek-ai/DeepSeek-V4-Flash-0731:deepinfra
```

If the primary provider has a connection, timeout, rate-limit, or server
failure, the client retries through the configured fallback model.

### vLLM on Colab

Open [the Colab notebook](notebooks/vllm_colab.ipynb), select a GPU runtime,
and add `NGROK_AUTHTOKEN` and `VLLM_API_KEY` to Colab Secrets. The notebook
starts the quantized `Qwen/Qwen2.5-14B-Instruct-AWQ` model and prints a protected
ngrok URL.

Configure the local backend using that URL and the same API key:

```env
LLM_BACKEND=vllm
VLLM_BASE_URL=https://your-ngrok-domain.ngrok-free.app/v1
VLLM_API_KEY=your-private-key
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

Restart FastAPI after changing `.env`. Stop the Colab runtime after testing;
the ngrok URL is temporary and publicly reachable, although model routes are
protected by the vLLM API key.

## Docker

Run only the API with the configured hosted backend:

```bash
docker compose up --build api
```

On a Linux machine with an NVIDIA GPU and NVIDIA Container Toolkit, run the API
and optional vLLM service:

```bash
docker compose --profile local up --build
```

Set `LLM_BACKEND=vllm` before using the local profile. The API reaches vLLM at
`http://vllm:8000/v1` inside the Compose network.

## Quality checks

```bash
ruff format --check .
ruff check .
mypy app
pytest
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Application liveness check |
| `POST` | `/api/v1/documents` | Ingest `.md`, `.txt`, or `.pdf` content |
| `POST` | `/api/v1/chat` | Run retrieval, tools, and structured generation |

## ONNX decision

ONNX conversion is not used for the generative model. vLLM performs optimized
GPU inference using continuous batching, paged attention, and its supported
quantized model formats; converting that model to ONNX would bypass the serving
features this project is intended to demonstrate. The compact embedding model
runs locally on CPU, where ONNX could be evaluated later if profiling shows
embedding latency is a bottleneck.
