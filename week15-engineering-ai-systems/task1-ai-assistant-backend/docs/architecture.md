# Architecture

The AI assistant has two applications: a Next.js frontend and a FastAPI
backend. The frontend handles the user experience and local chat sessions. The
backend owns RAG, tool execution, model access, and document ingestion.

## Overall system

```mermaid
flowchart LR
    User["User"] --> Frontend["Next.js frontend"]
    Frontend <-->|"HTTP and SSE"| Backend["FastAPI backend"]

    Backend --> RAG["RAG pipeline"]
    Backend --> Agent["Assistant agent"]

    RAG <--> Qdrant["Qdrant Cloud"]
    Agent --> Tools["External tools"]
    Agent --> Models["LLM providers"]
```

## Frontend and API

```mermaid
flowchart LR
    UI["Chat interface"] --> Sessions["Session state"]
    Sessions --> Storage["Browser localStorage"]

    UI -->|"Upload files"| Documents["Documents API"]
    UI -->|"Send message"| Chat["Streaming chat API"]
    Chat -->|"Status events"| UI
    Chat -->|"Tool events"| UI
    Chat -->|"Answer deltas"| UI
    Chat -->|"Final metadata"| UI
```

The frontend aborts the active streaming request when the user presses the stop
button. Any answer text already received remains in the session.

## Document ingestion and retrieval

```mermaid
flowchart LR
    Upload["MD, TXT, or PDF"] --> Validate["Validate and load"]
    Validate --> Chunk["Overlapping chunks"]
    Chunk --> Cloud["Qdrant Cloud Inference"]

    Cloud --> Dense["Dense vectors"]
    Cloud --> Sparse["BM25 sparse vectors"]
    Cloud --> ColBERT["ColBERT vectors"]
    Dense --> Collection["Qdrant collection"]
    Sparse --> Collection
    ColBERT --> Collection

    Cloud -. "unavailable" .-> Local["Local MiniLM embeddings"]
    Local --> Collection

    Question["User question"] --> Hybrid["Dense and sparse retrieval"]
    Collection --> Hybrid
    Hybrid --> Rerank["ColBERT reranking"]
    Rerank --> Context["Top document chunks"]

    Question -. "cloud inference unavailable" .-> QueryVector["Local MiniLM query embedding"]
    QueryVector --> DenseFallback["Dense cosine search"]
    Collection --> DenseFallback
    DenseFallback --> Context
```

Single-file and batch upload endpoints use the same ingestion pipeline. Batch
uploads have bounded concurrency, and every file receives its own result.

## Assistant agent

```mermaid
flowchart TD
    Request["Question, history, and RAG context"] --> Selection["LLM tool-selection call"]

    Selection -->|"Tool requested"| Registry["Tool registry"]
    Registry --> Calculator["Calculator"]
    Registry --> Time["Current UTC time"]
    Registry --> Weather["Open-Meteo weather"]
    Registry --> Monid["Monid external APIs"]
    Registry -->|"Validated tool result"| Selection

    Selection -->|"No more tools"| Answer["Stream answer text"]
    Answer --> Metadata["Generate structured metadata"]
    Metadata --> Validate["Validate citations and schema"]
    Validate --> Response["Answer, sources, tools, and model details"]
```

Tool selection and structured output use separate model calls because some
OpenAI-compatible providers do not allow tool calling and JSON mode together.
The loop is bounded by `LLM_MAX_TOOL_ITERATIONS`.

## Model routing

```mermaid
flowchart LR
    Client["OpenAI-compatible LLM client"] --> Choice{"LLM_BACKEND"}

    Choice -->|"huggingface"| Primary["Hugging Face primary model"]
    Primary -. "request failure" .-> Fallback["Hugging Face fallback model"]

    Choice -->|"vllm"| VLLM["vLLM endpoint"]
    VLLM --> LocalGPU["Local NVIDIA host"]
    VLLM --> Tunnel["Colab GPU through ngrok"]
```

The backend may use the fallback model only before streamed output begins. It
does not combine a partial response from one model with output from another.

## Deployment

```mermaid
flowchart LR
    Browser["Browser"] --> Web["Next.js application"]
    Web --> API["FastAPI container"]
    API --> Qdrant["Qdrant Cloud"]
    API --> Hosted["Hosted LLM and tools"]
    API -. "optional Docker profile" .-> GPU["vLLM GPU container"]
```

The default Docker Compose command starts only FastAPI. vLLM is in the optional
`local` profile so it cannot start accidentally on a development laptop.
