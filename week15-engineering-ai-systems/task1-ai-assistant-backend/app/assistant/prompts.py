from pathlib import Path

PROMPT_DIRECTORY = Path(__file__).with_name("prompt_versions")
AVAILABLE_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2", "prompt_v3")
DEFAULT_PROMPT_VERSION = "prompt_v3"


def load_system_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    """Load an explicitly versioned system prompt from the package."""

    if version not in AVAILABLE_PROMPT_VERSIONS:
        available = ", ".join(AVAILABLE_PROMPT_VERSIONS)
        raise ValueError(
            f"Unknown prompt version '{version}'. Choose from: {available}"
        )

    prompt_path = PROMPT_DIRECTORY / f"{version}.txt"
    return prompt_path.read_text(encoding="utf-8").strip()


def build_system_prompt(
    context: str | None = None,
    version: str = DEFAULT_PROMPT_VERSION,
) -> str:
    prompt = load_system_prompt(version)
    if not context:
        return prompt + "\n\nNo relevant document context was retrieved."

    return prompt + "\n\n<document_context>\n" + context + "\n</document_context>"

