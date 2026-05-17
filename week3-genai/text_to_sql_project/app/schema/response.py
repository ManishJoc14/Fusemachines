from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schema.agent import QueryPlan


class QueryResponse(BaseModel):
    question: str
    status: str = Field(..., description="success or failed")
    sql: str
    result: Any = None
    summary: Optional[str] = None
    error: Optional[str] = None
    decomposition: Optional[QueryPlan] = None
    attempts: int = 0
    execution_ms: Optional[float] = None
