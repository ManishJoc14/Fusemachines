from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.core.logging import logger
from app.db.session import AsyncSessionLocal


class SQLExecutor:
    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            if value == value.to_integral_value():
                return int(value)
            return float(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        return value

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: self._serialize_value(value) for key, value in row.items()}

    async def run_sql(self, sql: str) -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            try:
                logger.info("Executing SQL: %s", sql)
                result = await session.execute(text(sql))
                rows = result.mappings().all()
                return [self._serialize_row(dict(row)) for row in rows]
            except Exception as exc:
                logger.error("SQL execution failed: %s", exc)
                raise
