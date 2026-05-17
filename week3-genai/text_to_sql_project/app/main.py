import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agent.engine import TextToSQLAgent
from app.core.config import settings
from app.schema.request import QueryRequest
from app.schema.response import QueryResponse


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = TextToSQLAgent()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/agent/sql", response_model=QueryResponse)
async def agent_sql(req: QueryRequest):
    return await agent.run(req.question)


@app.post("/agent/sql/stream")
async def agent_sql_stream(req: QueryRequest):
    async def event_generator():
        async for update in agent.run_yield(req.question):
            # Convert any Pydantic models in the update to dicts
            clean_update = {}
            for k, v in update.items():
                if hasattr(v, "model_dump"):
                    clean_update[k] = v.model_dump()
                else:
                    clean_update[k] = v
            
            yield json.dumps(clean_update, default=str) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
