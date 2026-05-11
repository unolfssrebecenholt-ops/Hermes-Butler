"""Tests that switch_model preserves config_context_length."""

from unittest.mock import MagicMock, patch

from run_agent import AIAgent
from agent.context_compressor import ContextCompressor


def _make_agent_with_compressor(config_context_length=None) -> AIAgent:
    """Build a minimal AIAgent with a context_compressor, skipping __init__."""
    agent = AIAgent.__new__(AIAgent)

    # Primary model settings
    agent.model = "primary-model"
    agent.provider = "openrouter"
    agent.base_url = "https://openrouter.ai/api/v1"
    agent.api_key = "sk-primary"
    agent.api_mode = "chat_completions"
    agent.client = MagicMock()
    agent.quiet_mode = True

    # Store config_context_length for later use in switch_model
    agent._config_context_length = config_context_length

    # Context compressor with primary model values
    compressor = ContextCompressor(
        model="primary-model",
        threshold_percent=0.50,
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-primary",
        provider="openrouter",
        quiet_mode=True,
        config_context_length=config_context_length,
    )
    agent.context_compressor = compressor

    # For switch_model
    agent._primary_runtime = {}

    return agent


@patch("agent.model_metadata.get_model_context_length", return_value=131_072)
def test_switch_model_preserves_config_context_length(mock_ctx_len):
    """When switching models, config_context_length should be passed to get_model_context_length."""
    agent = _make_agent_with_compressor(config_context_length=32_768)

    assert agent.context_compressor.model == "primary-model"
    assert agent.context_compressor.context_length == 32_768  # From config override

    # Switch model
    agent.switch_model("new-model", "openrouter", api_key="sk-new", base_url="https://openrouter.ai/api/v1")

    # Verify get_model_context_length was called with config_context_length
    mock_ctx_len.assert_called_once()
    call_kwargs = mock_ctx_len.call_args.kwargs
    assert call_kwargs.get("config_context_length") == 32_768

    # Verify compressor was updated
    assert agent.context_compressor.model == "new-model"


def test_switch_model_without_config_context_length():
    """When switching models without config override, config_context_length should be None."""
    agent = _make_agent_with_compressor(config_context_length=None)

    with patch("agent.model_metadata.get_model_context_length", return_value=128_000) as mock_ctx_len:
        # Switch model
        agent.switch_model("new-model", "openrouter", api_key="sk-new", base_url="https://openrouter.ai/api/v1")

        # Verify get_model_context_length was called with None
        mock_ctx_len.assert_called_once()
        call_kwargs = mock_ctx_len.call_args.kwargs
        assert call_kwargs.get("config_context_length") is None


def test_switch_model_adds_generic_user_agent_for_custom_openai_compat_base():
    """Custom OpenAI-compatible relays should not use the OpenAI SDK UA."""
    agent = _make_agent_with_compressor(config_context_length=None)
    captured = {}

    def _fake_create_client(client_kwargs, *, reason, shared):
        captured["kwargs"] = dict(client_kwargs)
        captured["reason"] = reason
        captured["shared"] = shared
        return MagicMock()

    agent._create_openai_client = _fake_create_client

    with patch("agent.model_metadata.get_model_context_length", return_value=128_000):
        agent.switch_model(
            "gpt-5.5",
            "relay",
            api_key="sk-relay",
            base_url="https://sub.aielove.eu.cc/v1",
            api_mode="chat_completions",
        )

    assert captured["reason"] == "switch_model"
    assert captured["shared"] is True
    assert captured["kwargs"]["default_headers"]["User-Agent"] == "HermesAgent/1.0"
    assert agent._primary_runtime["client_kwargs"]["default_headers"]["User-Agent"] == "HermesAgent/1.0"
