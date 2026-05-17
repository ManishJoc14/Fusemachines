from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
