from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.assistant.agent import AgentLimitError, AssistantAgent
from app.core.config import PROJECT_ROOT, get_settings
from app.llm.client import LLMClient
from app.tools.registry import RegisteredTool, ToolRegistry

CASES_PATH = PROJECT_ROOT / "evals" / "cases.json"
REPORT_PATH = PROJECT_ROOT / "evals" / "results.md"


class EvidenceSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=500)
    source: Literal["source_a", "source_b", "unavailable_source"]


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    minimum_tool_calls: int = 0
    maximum_tool_calls: int | None = None
    minimum_iterations: int = 1
    expected_tools: list[str]
    expected_sources: list[str]
    answer_terms: list[str]
    expects_injected_failure: bool


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    case_id: str
    question: str
    answer: str
    model: str
    used_fallback: bool
    completed: bool
    tool_calls_correct: bool
    iterations: int
    tool_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    failure_class: str
    notes: str
    trajectory: list[dict[str, object]]


EVIDENCE: dict[str, dict[str, str]] = {
    "bridges": {
        "source_a": "Regional report: the flood destroyed 19 motorable bridges.",
        "source_b": "Engineering survey: inspectors recorded 19 destroyed bridges.",
    },
    "shelters": {
        "source_a": "Municipal bulletin: 17 emergency shelters remained open.",
        "source_b": "Relief agency update: 19 shelters remained open.",
    },
    "schools": {
        "source_a": "Education office: most schools reopened on September 12.",
        "source_b": "Local bulletin: classes resumed gradually from September 12.",
    },
}


def search_evidence(input_data: BaseModel) -> str:
    # Step 1: Validate the same arguments the model sends through the registry.
    request = EvidenceSearchInput.model_validate(input_data.model_dump())

    # Step 2: Inject a predictable outage for the recovery test.
    if request.source == "unavailable_source":
        raise ValueError("Injected failure: evidence source timed out")

    # Step 3: Find the controlled topic requested by the agent.
    topic = next(
        (name for name in EVIDENCE if name in request.query.lower()),
        "",
    )
    if not topic:
        return json.dumps(
            {
                "source": request.source,
                "status": "not_found",
                "evidence": "No matching evidence was found.",
            }
        )

    # Step 4: Return deterministic evidence from the selected source.
    return json.dumps(
        {
            "source": request.source,
            "status": "found",
            "evidence": EVIDENCE[topic][request.source],
        }
    )


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            RegisteredTool(
                name="evidence_search",
                description=(
                    "Search one controlled independent evidence source while "
                    "verifying a claim. Assess each result before deciding whether "
                    "another source is necessary."
                ),
                input_model=EvidenceSearchInput,
                handler=search_evidence,
            )
        ]
    )


def load_cases(path: Path) -> list[EvaluationCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase.model_validate(item) for item in payload]


async def evaluate_case(
    agent: AssistantAgent,
    case: EvaluationCase,
) -> EvaluationResult:
    # Step 1: Run the real agent loop and classify runtime errors as hard failures.
    try:
        result = await agent.run(case.question)
    except AgentLimitError as exc:
        return EvaluationResult(
            case_id=case.id,
            question=case.question,
            answer="",
            model="unknown",
            used_fallback=False,
            completed=False,
            tool_calls_correct=False,
            iterations=len(exc.trajectory),
            tool_calls=len(exc.tools_used),
            prompt_tokens=exc.token_usage.prompt_tokens,
            completion_tokens=exc.token_usage.completion_tokens,
            total_tokens=exc.token_usage.total_tokens,
            failure_class="hard failure",
            notes=str(exc),
            trajectory=[asdict(step) for step in exc.trajectory],
        )
    except Exception as exc:
        return EvaluationResult(
            case_id=case.id,
            question=case.question,
            answer="",
            model="unknown",
            used_fallback=False,
            completed=False,
            tool_calls_correct=False,
            iterations=0,
            tool_calls=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            failure_class="hard failure",
            notes=f"{type(exc).__name__}: {exc}",
            trajectory=[],
        )

    # Step 2: Inspect tool names, arguments, failures, and trajectory length.
    tools = result.tools_used
    tool_names = {tool.name for tool in tools}
    requested_sources = [
        str(tool.arguments.get("source"))
        for tool in tools
        if tool.name == "evidence_search"
    ]
    failed_tools = [tool for tool in tools if not tool.success]
    expected_failure_observed = (
        any(
            tool.arguments.get("source") == "unavailable_source" and not tool.success
            for tool in tools
        )
        == case.expects_injected_failure
    )
    maximum_ok = (
        case.maximum_tool_calls is None or len(tools) <= case.maximum_tool_calls
    )
    tool_calls_correct = (
        set(case.expected_tools).issubset(tool_names)
        and all(source in requested_sources for source in case.expected_sources)
        and len(tools) >= case.minimum_tool_calls
        and maximum_ok
        and result.iterations >= case.minimum_iterations
        and expected_failure_observed
    )

    # Step 3: Check whether the final answer contains the expected evidence.
    answer = result.output.answer.lower()
    answer_matches = not case.answer_terms or any(
        term.lower() in answer for term in case.answer_terms
    )
    completed = bool(answer.strip()) and tool_calls_correct and answer_matches

    # Step 4: Apply the assignment's failure taxonomy to incomplete runs.
    if completed:
        failure_class = "none"
        notes = "Completed expected trajectory."
    elif failed_tools and result.output.confidence == "high":
        failure_class = "cascading soft failure"
        notes = "A failed observation propagated into a high-confidence answer."
    else:
        failure_class = "soft failure"
        notes = "The run completed but missed an expected behavior."

    # Step 5: Return behavior and token metrics for this query.
    return EvaluationResult(
        case_id=case.id,
        question=case.question,
        answer=result.output.answer,
        model=result.model,
        used_fallback=result.used_fallback,
        completed=completed,
        tool_calls_correct=tool_calls_correct,
        iterations=result.iterations,
        tool_calls=len(tools),
        prompt_tokens=result.token_usage.prompt_tokens,
        completion_tokens=result.token_usage.completion_tokens,
        total_tokens=result.token_usage.total_tokens,
        failure_class=failure_class,
        notes=notes,
        trajectory=[asdict(step) for step in result.trajectory],
    )


def build_report(results: list[EvaluationResult]) -> str:
    # Step 1: Aggregate the metrics used in the report summary.
    completed = sum(result.completed for result in results)
    correct_tools = sum(result.tool_calls_correct for result in results)
    total_tokens = sum(result.total_tokens for result in results)
    average_iterations = (
        sum(result.iterations for result in results) / len(results) if results else 0
    )

    # Step 2: Build one result row for every evaluation query.
    lines = [
        "# Agent Evaluation Results",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "| Case | Completed | Correct tools | Iterations | Tool calls | "
        "Tokens | Failure class |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            f"{result.case_id} | "
            f"{'yes' if result.completed else 'no'} | "
            f"{'yes' if result.tool_calls_correct else 'no'} | "
            f"{result.iterations} | {result.tool_calls} | "
            f"{result.total_tokens} | {result.failure_class} |"
        )

    # Step 3: Append aggregate rates, token usage, and failure notes.
    case_count = len(results)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Task completion rate: {completed}/{case_count} "
            f"({completed / case_count:.0%})"
            if case_count
            else "- No cases ran.",
            f"- Tool-call correctness: {correct_tools}/{case_count} "
            f"({correct_tools / case_count:.0%})"
            if case_count
            else "- No cases ran.",
            f"- Average trajectory length: {average_iterations:.2f} iterations",
            f"- Total tokens: {total_tokens}",
            "- Monetary cost is not estimated because Hugging Face provider routes "
            "do not expose one stable per-token price in the response.",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- **{result.case_id}:** {result.notes}" for result in results)
    return "\n".join(lines) + "\n"


async def run(cases_path: Path, report_path: Path) -> int:
    # Step 1: Build the production agent with a controlled evaluation tool.
    settings = get_settings()
    client = LLMClient(settings)
    agent = AssistantAgent(client, build_registry(), settings)

    # Step 2: Execute every case while ensuring the HTTP client is closed.
    try:
        results = [await evaluate_case(agent, case) for case in load_cases(cases_path)]
    finally:
        await client.close()

    # Step 3: Save a human-readable report and return a CI-friendly exit code.
    report = build_report(results)
    await asyncio.to_thread(report_path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(report_path.write_text, report, encoding="utf-8")
    print(report)
    return 0 if all(result.completed for result in results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the agentic workflow")
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.cases, args.report))


if __name__ == "__main__":
    raise SystemExit(main())
