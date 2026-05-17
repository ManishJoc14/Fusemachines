from __future__ import annotations


from app.agent.hf_client import HFClient
from app.agent.prompts import PromptBuilder
from app.agent.pipeline import PromptChain
from app.db.executor import SQLExecutor
from app.db.introspection import SchemaInspector
from app.schema.response import QueryResponse
from app.sql.validator import SQLValidator


class TextToSQLAgent:
    def __init__(
        self,
        hf_client: HFClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        schema_inspector: SchemaInspector | None = None,
        sql_executor: SQLExecutor | None = None,
        sql_validator: SQLValidator | None = None,
    ) -> None:
        self.hf_client = hf_client or HFClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.schema_inspector = schema_inspector or SchemaInspector()
        self.sql_executor = sql_executor or SQLExecutor()
        self.sql_validator = sql_validator or SQLValidator()


    # Chat helpers removed — prompt chaining delegated to `PromptChain`.

    async def run(self, question: str, max_retries: int | None = None) -> QueryResponse:
        # Delegate to PromptChain for explicit prompt-chaining and logging
        chain = PromptChain(
            hf_client=self.hf_client,
            prompt_builder=self.prompt_builder,
            schema_inspector=self.schema_inspector,
            sql_executor=self.sql_executor,
            sql_validator=self.sql_validator,
        )

        return await chain.run(question, max_retries)

    async def run_yield(self, question: str, max_retries: int | None = None):
        chain = PromptChain(
            hf_client=self.hf_client,
            prompt_builder=self.prompt_builder,
            schema_inspector=self.schema_inspector,
            sql_executor=self.sql_executor,
            sql_validator=self.sql_validator,
        )
        async for update in chain.run_yield(question, max_retries):
            yield update
