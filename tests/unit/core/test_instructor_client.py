from unittest.mock import patch

from core.infrastructure.services.instructor_client import InstructorLlmClient


@patch("core.infrastructure.services.instructor_client.OpenAI")
@patch("core.infrastructure.services.instructor_client.instructor.from_openai")
def test_instructor_llm_client_default_config(mock_from_openai, mock_openai, monkeypatch):
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT", raising=False)

    client = InstructorLlmClient(base_url="http://localhost:11434/v1")
    assert client.base_url == "http://localhost:11434/v1"
    mock_openai.assert_called_once()
    kwargs = mock_openai.call_args[1]
    assert kwargs["max_retries"] == 3
    assert kwargs["timeout"] == 120.0


@patch("core.infrastructure.services.instructor_client.OpenAI")
@patch("core.infrastructure.services.instructor_client.instructor.from_openai")
def test_instructor_llm_client_custom_env_config(mock_from_openai, mock_openai, monkeypatch):
    monkeypatch.setenv("LLM_MAX_RETRIES", "5")
    monkeypatch.setenv("LLM_TIMEOUT", "60.0")

    client = InstructorLlmClient(base_url="https://omniroute.example.com/v1")
    assert client.base_url == "https://omniroute.example.com/v1"
    mock_openai.assert_called_once()
    kwargs = mock_openai.call_args[1]
    assert kwargs["max_retries"] == 5
    assert kwargs["timeout"] == 60.0
