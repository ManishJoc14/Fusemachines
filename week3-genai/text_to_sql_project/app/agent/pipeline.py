from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.agent.hf_client import HFClient, HFClientError, extract_json_block
from app.agent.prompts import PromptBuilder
from app.core.logging import logger
from app.core.config import settings
from app.db.introspection import SchemaInspector
from app.db.executor import SQLExecutor
from app.schema.agent import QueryPlan
from app.schema.response import QueryResponse
from app.sql.validator import SQLValidator


ROOT_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR = ROOT_LOG_DIR / "prompt_chain"
AGG_LOG = ROOT_LOG_DIR / "prompts.jsonl"
ROOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


class PromptChain:
    """Runs an explicit prompt-chaining pipeline with step-level logging.

    Steps:
    1. Decompose -> structured plan
    2. Generate SQL from plan
    3. Validate SQL
    4. Execute SQL
    5. Repair (LLM) and retry if failed until max retries.
    """

    def __init__(
        self,
        hf_client: HFClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        schema_inspector: SchemaInspector | None = None,
        sql_executor: SQLExecutor | None = None,
        sql_validator: SQLValidator | None = None,
    ) -> None:
        self.hf = hf_client or HFClient()
        self.prompts = prompt_builder or PromptBuilder()
        self.inspector = schema_inspector or SchemaInspector()
        self.executor = sql_executor or SQLExecutor()
        self.validator = sql_validator or SQLValidator()

    def _write_log(self, name: str, payload: dict[str, Any]) -> None:
        ts = int(time.time() * 1000)
        path = LOG_DIR / f"{name}-{ts}.json"
        try:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            # also append a redacted single-line JSON to aggregated log
            try:
                redacted = self._redact_payload(payload)
                with AGG_LOG.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(redacted, ensure_ascii=False) + "\n")
            except Exception:
                logger.exception("Failed to append to aggregated prompt log")
        except Exception:
            logger.exception("Failed to write prompt chain log")

    def _redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Redact obvious secrets from payload before writing to aggregated log.

        This performs a shallow recursive redact for common keys like 'api_key',
        'authorization', 'token' and will trim overly long strings.
        """
        def redact_value(val: Any) -> Any:
            if isinstance(val, dict):
                return {k: redact_value(v) for k, v in val.items()}
            if isinstance(val, list):
                return [redact_value(x) for x in val]
            if isinstance(val, str):
                if len(val) > 500:
                    return val[:200] + "...[TRUNCATED]"
                return val
            return val

        out: dict[str, Any] = {}
        for k, v in payload.items():
            lk = k.lower()
            if lk in ("api_key", "authorization", "token", "secret"):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_value(v)
        return out

    async def run(self, question: str, max_retries: int | None = None) -> QueryResponse:
        started_at = time.perf_counter()
        retries_allowed = (
            settings.AGENT_MAX_RETRIES if max_retries is None else max_retries
        )
        max_attempts = retries_allowed + 1

        try:
            schema_context = await self.inspector.get_schema_context()
        except Exception as exc:
            logger.exception("Schema introspection failed")
            return QueryResponse(
                question=question,
                status="failed",
                sql="",
                result=None,
                error=f"Schema introspection failed: {exc}",
            )

        log_payload: dict[str, Any] = {"question": question, "steps": []}

        # Step 1: Decompose
        decomp_msgs = self.prompts.build_decomposition_messages(
            question, schema_context
        )
        log_payload["steps"].append({"step": "decompose", "messages": decomp_msgs})
        try:
            content = await self.hf.achat(decomp_msgs)
            log_payload["steps"][-1]["response"] = content
            payload = extract_json_block(content)
            decomposition_payload = json.loads(payload)
            plan = QueryPlan.model_validate(decomposition_payload)
        except (HFClientError, Exception) as exc:
            logger.exception("Decomposition failed")
            log_payload["steps"][-1]["error"] = str(exc)
            self._write_log("decompose", log_payload)
            return QueryResponse(
                question=question,
                status="failed",
                sql="",
                result=None,
                error=f"Decomposition failed: {exc}",
            )

        # Step 2: Generate SQL
        sql_msgs = self.prompts.build_sql_messages(question, plan, schema_context)
        log_payload["steps"].append({"step": "generate_sql", "messages": sql_msgs})
        try:
            sql_content = (await self.hf.achat(sql_msgs)).strip()
            log_payload["steps"][-1]["response"] = sql_content
            sql = self.validator.normalize_sql(sql_content)
        except HFClientError as exc:
            logger.exception("SQL generation failed")
            log_payload["steps"][-1]["error"] = str(exc)
            self._write_log("generate_sql", log_payload)
            return QueryResponse(
                question=question,
                status="failed",
                sql="",
                result=None,
                error=f"SQL generation failed: {exc}",
                decomposition=plan,
            )

        # Safety check
        if not self.validator.validate_sql(sql):
            logger.warning("Generated SQL failed safety validation")
            log_payload["steps"].append(
                {"step": "validate", "sql": sql, "valid": False}
            )
            self._write_log("validate", log_payload)
            return QueryResponse(
                question=question,
                status="failed",
                sql=sql,
                result=None,
                error="Unsafe SQL generated",
                decomposition=plan,
            )

        log_payload["steps"].append({"step": "validate", "sql": sql, "valid": True})

        last_error: str | None = None

        # Execute with repair loop
        for attempt in range(1, max_attempts + 1):
            try:
                rows = await self.executor.run_sql(sql)
                execution_ms = round((time.perf_counter() - started_at) * 1000, 2)
                result = (
                    rows
                    if not (len(rows) == 1 and len(rows[0]) == 1)
                    else next(iter(rows[0].values()))
                )
                # deterministic summary based on SQL and raw rows
                from app.agent.utils import summarize_result

                summary = summarize_result(rows, sql=sql)

                log_payload["steps"].append(
                    {
                        "step": "execute",
                        "attempt": attempt,
                        "sql": sql,
                        "result_count": len(rows),
                    }
                )
                self._write_log("prompt_chain", log_payload)
                return QueryResponse(
                    question=question,
                    status="success",
                    sql=sql,
                    result=result,
                    summary=summary,
                    decomposition=plan,
                    attempts=attempt,
                    execution_ms=execution_ms,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Execution failed attempt %s: %s", attempt, last_error)
                log_payload["steps"].append(
                    {"step": "execute_error", "attempt": attempt, "error": last_error}
                )

                if attempt >= max_attempts:
                    break

                # Repair step
                repair_msgs = self.prompts.build_repair_messages(
                    question, plan, schema_context, sql, last_error
                )
                log_payload["steps"].append({"step": "repair", "messages": repair_msgs})
                try:
                    repaired = (await self.hf.achat(repair_msgs)).strip()
                    log_payload["steps"][-1]["response"] = repaired
                    repaired_sql = self.validator.normalize_sql(repaired)
                except HFClientError as repair_exc:
                    last_error = f"{last_error}; repair failed: {repair_exc}"
                    log_payload["steps"][-1]["error"] = str(repair_exc)
                    break

                if not repaired_sql or not self.validator.validate_sql(repaired_sql):
                    last_error = f"{last_error}; repaired SQL invalid"
                    log_payload["steps"][-1]["repaired_sql"] = repaired_sql
                    break

                sql = repaired_sql

        execution_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_payload["final_error"] = last_error
        self._write_log("prompt_chain_failed", log_payload)
        return QueryResponse(
            question=question,
            status="failed",
            sql=sql,
            result=None,
            error=last_error or "Execution failed",
            decomposition=plan,
            attempts=max_attempts,
            execution_ms=execution_ms,
        )
