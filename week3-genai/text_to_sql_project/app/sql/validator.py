from __future__ import annotations

import re

from app.core.constants import ALLOWED_SQL_START, FORBIDDEN_SQL_KEYWORDS, MAX_SQL_LENGTH


class SQLValidator:
    CODE_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE)

    def normalize_sql(self, sql: str) -> str:
        cleaned = self.CODE_FENCE_RE.sub("", sql.strip()).strip()
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()
        return cleaned

    def validate_sql(self, sql: str) -> bool:
        normalized = self.normalize_sql(sql).lower()

        if not normalized.startswith(ALLOWED_SQL_START):
            return False

        if ";" in normalized:
            return False

        if "--" in normalized or "/*" in normalized or "*/" in normalized:
            return False

        if len(normalized) > MAX_SQL_LENGTH:
            return False

        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if keyword in normalized:
                return False

        return True
