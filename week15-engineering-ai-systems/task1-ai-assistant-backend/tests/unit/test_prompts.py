import pytest

from app.assistant.prompts import build_system_prompt, load_system_prompt


def test_each_prompt_version_is_explicit_and_loadable() -> None:
    prompts = [load_system_prompt(f"prompt_v{version}") for version in range(1, 4)]

    assert len(set(prompts)) == 3
    assert "two independent sources" not in prompts[0]
    assert "two independent sources" in prompts[1]
    assert "adaptive cross-source verification" in prompts[2]


def test_prompt_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unknown prompt version"):
        load_system_prompt("prompt_v99")


def test_document_context_is_delimited() -> None:
    prompt = build_system_prompt("Verified document text", "prompt_v3")

    assert "<document_context>" in prompt
    assert "Verified document text" in prompt
    assert "</document_context>" in prompt

