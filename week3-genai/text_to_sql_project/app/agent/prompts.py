from __future__ import annotations

from app.schema.agent import QueryPlan


class PromptBuilder:
    DECOMPOSITION_SYSTEM_PROMPT = """You are a PostgreSQL text-to-SQL planner.
Return JSON only. Do not wrap the response in markdown.

The JSON object must match this shape:
{
  "intent": "string",
  "tables": ["string"],
  "columns": ["string"],
  "filters": ["string"],
  "joins": ["string"],
  "aggregation": ["string"],
  "group_by": ["string"],
  "order_by": ["string"],
  "limit": 0,
  "notes": ["string"]
}

Rules:
- Use only tables and columns that exist in the provided schema.
- Prefer the smallest valid set of tables and columns.
- If the question asks for a count, total, average, minimum, maximum, or grouped summary, reflect that in aggregation and group_by.
- If the question is ambiguous, make the safest reasonable choice and explain the assumption in notes.
"""

    SQL_SYSTEM_PROMPT = """You are a PostgreSQL SQL generator.
Return a single executable SELECT query only.
Do not include markdown, explanation, or code fences.
Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, or CTEs.
Use only tables and columns present in the schema and the plan.
Prefer explicit JOINs with table aliases when multiple tables are needed.
"""

    REPAIR_SYSTEM_PROMPT = """You are a PostgreSQL SQL repair assistant.
Return only a corrected SELECT query.
Do not include markdown, explanation, or code fences.
Keep the query aligned with the question, the plan, and the schema.
Fix the exact database error while preserving the original intent.
"""

    def build_decomposition_messages(
        self, question: str, schema_context: str
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.DECOMPOSITION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Schema:\n"
                    f"{schema_context}\n\n"
                    f"Question: {question}\n\n"
                    "Return only the JSON object described above."
                ),
            },
        ]

    def build_sql_messages(
        self, question: str, plan: QueryPlan, schema_context: str
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.SQL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Schema:\n"
                    f"{schema_context}\n\n"
                    f"Question: {question}\n\n"
                    f"Plan:\n{plan.model_dump_json(indent=2)}\n\n"
                    "Return one SELECT statement only."
                ),
            },
        ]

    def build_repair_messages(
        self, question: str, plan: QueryPlan, schema_context: str, sql: str, error: str
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.REPAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Schema:\n"
                    f"{schema_context}\n\n"
                    f"Question: {question}\n\n"
                    f"Plan:\n{plan.model_dump_json(indent=2)}\n\n"
                    f"Previous SQL:\n{sql}\n\n"
                    f"Database error:\n{error}\n\n"
                    "Return the corrected SELECT statement only."
                ),
            },
        ]
