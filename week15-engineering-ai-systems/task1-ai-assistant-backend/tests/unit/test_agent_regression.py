import pandas as pd

from scripts.run_agent_regression import version_pass_rates


def test_version_pass_rates_counts_both_checks() -> None:
    verdicts = pd.DataFrame(
        [
            {
                "prompt_version": "prompt_v1",
                "correctness": "correct",
                "relevance": "relevant",
            },
            {
                "prompt_version": "prompt_v1",
                "correctness": "incorrect",
                "relevance": "relevant",
            },
        ]
    )

    rates = version_pass_rates(verdicts)

    assert rates == {"prompt_v1": 0.75}
