# Architecture

```mermaid
flowchart LR
    User[API client] --> FastAPI[FastAPI endpoints]

    FastAPI --> Ingestion[Document ingestion service]
    Ingestion --> Loader[MD / TXT / PDF loader]
    Loader --> Chunker[Overlapping text chunker]
    Chunker --> Embeddings[Sentence-transformer embeddings]
    Embeddings --> Qdrant[(Qdrant Cloud)]

    FastAPI --> Chat[Chat service]
    Chat --> Retriever[Dense retriever]
    Retriever --> Embeddings
    Qdrant --> Retriever
    Retriever --> Context[Bounded document context]
    Context --> Agent[Assistant agent]

    Agent --> Tools{Tool required?}
    Tools -->|yes| Registry[Tool registry]
    Registry --> Calculator[Calculator]
    Registry --> Time[UTC time]
    Registry --> Weather[Open-Meteo weather]
    Calculator --> Agent
    Time --> Agent
    Weather --> Agent

    Tools -->|no / tools complete| Structured[JSON Schema response]
    Agent --> LLM{Configured backend}
    LLM --> HFPrimary[Hugging Face primary]
    HFPrimary -. failure .-> HFFallback[Hugging Face fallback]
    LLM --> VLLM[vLLM OpenAI server]
    Colab[Colab GPU] --> VLLM
    Ngrok[Protected ngrok tunnel] --> VLLM
    LLM --> Agent
    Structured --> Chat
    Chat --> Response[Answer + sources + tool metadata]
    Response --> User
```

## Request flow

1. The chat service embeds the question and retrieves relevant chunks from
   Qdrant when RAG is enabled.
2. Retrieved text is placed inside explicit context boundaries in the system
   prompt.
3. The agent asks the configured model whether a tool is required.
4. Requested tools are validated, executed, and returned to the same model.
5. Tool selection and structured generation use separate model calls because
   some OpenAI-compatible providers reject JSON mode combined with tools.
6. The final response is validated against `AssistantOutput` and invented chunk
   IDs are removed before citations reach the client.

## Deployment views

The default development and Docker path uses Hugging Face inference with
Qdrant Cloud. The GPU path runs vLLM either from the optional Compose profile on
an NVIDIA host or from Google Colab through a protected ngrok tunnel. Both
backends expose the same OpenAI-compatible interface, so the application code
switches through environment configuration rather than backend-specific routes.
