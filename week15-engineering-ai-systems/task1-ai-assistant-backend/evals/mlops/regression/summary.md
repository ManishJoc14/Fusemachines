# Agent Regression Results

The Evidently LLM judge checks reference-based correctness and answer relevance.

| Prompt version | Checks passed | Promotion decision |
| --- | ---: | --- |
| prompt_v1 | 62% | block |
| prompt_v2 | 88% | pass |
| prompt_v3 | 88% | pass |

## Failed cases

- **prompt_v1 / confirmed_claim**: correctness=incorrect, relevance=relevant. Judge notes: The response states that source A alone supports the claim, but the reference explicitly says both independent sources (source_a and source_b) report the same information. The response fails to acknowledge that source_b has already confirmed the claim, and instead treats source_b as not yet retrieved, contradicting the reference that both sources support the claim. Therefore, it does not preserve the key reference information.
- **prompt_v1 / injected_tool_failure**: correctness=incorrect, relevance=irrelevant. Judge notes: The candidate response is empty, providing no information at all. It fails to preserve any of the key reference information (that schools reopened or resumed gradually from September 12, and that the failed source is a limitation). Therefore, it contradicts the requirement to verify and state the evidence, making it incorrect.
- **prompt_v2 / injected_tool_failure**: correctness=incorrect, relevance=relevant. Judge notes: The response claims schools reopened on September 12, but the reference states schools 'reopened or resumed gradually from September 12', meaning reopening was gradual and not necessarily a single event on that exact date. The response omits the gradual nature and also fails to acknowledge the unavailable source limitation, thus it does not preserve key reference information and slightly contradicts it.
- **prompt_v3 / injected_tool_failure**: correctness=incorrect, relevance=relevant. Judge notes: The reference states that evidence from available sources says schools reopened or resumed gradually from September 12, but also explicitly notes that the unavailable source failed and is a limitation. The response asserts a specific date 'September 12, 2024' and states they 'reopened on September 12' without acknowledging the limitation or that the evidence only supports gradual resumption from that date, not necessarily a full reopening on that exact date. This goes beyond the reference by adding specificity ('2024') and omitting the noted uncertainty, thereby contradicting the reference's cautious tone and limitation.

## Judge sanity check

The verdicts must still be reviewed with the saved candidate, reference, and reasoning columns. The judge is a model and can be wrong; its result is a regression signal, not an unquestionable ground truth.
