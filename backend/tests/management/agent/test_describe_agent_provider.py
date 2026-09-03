import pytest

from management.agent.provider import describe_agent_provider


def test_reports_fake_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "fake")

    status = describe_agent_provider()

    assert status.status == "FAKE"
    assert status.provider == "fake"
    assert status.model is None


def test_reports_configured_when_anthropic_and_api_key_are_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("GREENHOUSE_AGENT_MODEL", raising=False)

    status = describe_agent_provider()

    assert status.status == "CONFIGURED"
    assert status.provider == "anthropic"
    assert status.model == "claude-sonnet-5"


def test_reports_configured_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("GREENHOUSE_AGENT_MODEL", "claude-opus-5")

    status = describe_agent_provider()

    assert status.model == "claude-opus-5"


def test_reports_misconfigured_when_anthropic_selected_without_an_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    status = describe_agent_provider()

    assert status.status == "MISCONFIGURED"
    assert status.detail is not None
    assert "ANTHROPIC_API_KEY" in status.detail


def test_reports_misconfigured_for_an_unknown_provider_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "not-a-real-provider")

    status = describe_agent_provider()

    assert status.status == "MISCONFIGURED"
    assert status.detail is not None
