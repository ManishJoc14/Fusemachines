# Agent Evaluation Results

Generated: 2026-09-19T12:14:28.325260+00:00

| Case | Completed | Correct tools | Iterations | Tool calls | Tokens | Failure class |
| --- | --- | --- | ---: | ---: | ---: | --- |
| confirmed_claim | yes | yes | 3 | 2 | 3626 | none |
| conflicting_sources | yes | yes | 3 | 2 | 4211 | none |
| needs_clarification | yes | yes | 1 | 0 | 1607 | none |
| injected_tool_failure | yes | yes | 4 | 3 | 5079 | none |

## Summary

- Task completion rate: 4/4 (100%)
- Tool-call correctness: 4/4 (100%)
- Average trajectory length: 2.75 iterations
- Total tokens: 14523
- Monetary cost is not estimated because Hugging Face provider routes do not expose one stable per-token price in the response.

## Notes

- **confirmed_claim:** Completed expected trajectory.
- **conflicting_sources:** Completed expected trajectory.
- **needs_clarification:** Completed expected trajectory.
- **injected_tool_failure:** Completed expected trajectory.
