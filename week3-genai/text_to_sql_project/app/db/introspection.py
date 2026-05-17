from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text

from app.core.logging import logger
from app.db.session import AsyncSessionLocal


class SchemaInspector:
    def __init__(self) -> None:
        self._schema_context_cache: str | None = None

    def _format_schema(
        self, columns: list[dict[str, str]], foreign_keys: list[dict[str, str]]
    ) -> str:
        tables: dict[str, list[str]] = defaultdict(list)
        for row in columns:
            tables[row["table_name"]].append(
                f"{row['column_name']} ({row['data_type']})"
            )

        joins: dict[str, list[str]] = defaultdict(list)
        for row in foreign_keys:
            joins[row["table_name"]].append(
                f"{row['column_name']} -> {row['foreign_table_name']}.{row['foreign_column_name']}"
            )

        lines = ["Database schema:"]
        for table_name in sorted(tables):
            lines.append(f"- {table_name}: {', '.join(tables[table_name])}")
            if joins.get(table_name):
                lines.append(f"  foreign keys: {'; '.join(joins[table_name])}")

        return "\n".join(lines)

    async def get_schema_context(self) -> str:
        if self._schema_context_cache:
            return self._schema_context_cache

        async with AsyncSessionLocal() as session:
            column_result = await session.execute(
                text(
                    """
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
            )
            fk_result = await session.execute(
                text(
                    """
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema = 'public'
                    ORDER BY tc.table_name, kcu.column_name
                    """
                )
            )

            columns = [dict(row) for row in column_result.mappings().all()]
            foreign_keys = [dict(row) for row in fk_result.mappings().all()]

        if not columns:
            raise RuntimeError("Unable to load database schema context")

        self._schema_context_cache = self._format_schema(columns, foreign_keys)
        logger.info(
            "Loaded schema context for %s tables",
            len({row["table_name"] for row in columns}),
        )
        return self._schema_context_cache
