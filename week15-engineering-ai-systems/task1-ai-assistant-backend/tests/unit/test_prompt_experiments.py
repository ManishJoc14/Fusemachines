from scripts.evaluate_agent import EvaluationResult
from scripts.run_prompt_experiments import aggregate_metrics


def result(*, completed: bool, tokens: int) -> EvaluationResult:
    return EvaluationResult(
        case_id="case",
        question="question",
        answer="answer",
        model="model",
        used_fallback=False,
        completed=completed,
        tool_calls_correct=completed,
        iterations=2,
        tool_calls=1,
        prompt_tokens=tokens - 2,
        completion_tokens=2,
        total_tokens=tokens,
        failure_class="none" if completed else "soft failure",
        notes="note",
        trajectory=[],
    )


def test_aggregate_metrics_compares_quality_and_cost() -> None:
    metrics = aggregate_metrics(
        [result(completed=True, tokens=100), result(completed=False, tokens=200)]
    )

    assert metrics["task_completion_rate"] == 0.5
    assert metrics["tool_correctness_rate"] == 0.5
    assert metrics["average_iterations"] == 2
    assert metrics["average_tokens"] == 150
    assert metrics["soft_failures"] == 1

