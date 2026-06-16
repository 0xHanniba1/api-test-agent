from unittest.mock import patch, MagicMock

import pytest

from api_test_gen.llm import LlmClient, LlmError


class TestLlmClient:
    def test_default_model(self):
        client = LlmClient()
        assert client.model is not None

    def test_custom_model(self):
        client = LlmClient(model="gpt-4o")
        assert client.model == "gpt-4o"

    @patch("api_test_gen.llm.completion")
    def test_call_returns_content(self, mock_completion):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "test response"
        mock_completion.return_value = mock_resp

        client = LlmClient(model="gpt-4o")
        result = client.call(system="You are helpful.", user="Hello")
        assert result == "test response"
        mock_completion.assert_called_once()

    @patch("api_test_gen.llm.completion")
    def test_call_passes_model_and_messages(self, mock_completion):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "ok"
        mock_completion.return_value = mock_resp

        client = LlmClient(model="claude-sonnet-4-20250514")
        client.call(system="sys", user="usr")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @patch("api_test_gen.llm.completion")
    def test_call_passes_timeout_and_retries(self, mock_completion):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "ok"
        mock_completion.return_value = mock_resp

        client = LlmClient(model="gpt-4o", timeout=5, num_retries=3)
        client.call(system="sys", user="usr")

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["timeout"] == 5
        assert call_kwargs["num_retries"] == 3

    @patch("api_test_gen.llm.completion")
    def test_empty_content_raises(self, mock_completion):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "   "
        mock_completion.return_value = mock_resp

        client = LlmClient(model="gpt-4o")
        with pytest.raises(LlmError):
            client.call(system="sys", user="usr")

    @patch("api_test_gen.llm.completion")
    def test_none_content_raises(self, mock_completion):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = None
        mock_completion.return_value = mock_resp

        client = LlmClient(model="gpt-4o")
        with pytest.raises(LlmError):
            client.call(system="sys", user="usr")

    @patch("api_test_gen.llm.completion")
    def test_provider_error_is_wrapped(self, mock_completion):
        mock_completion.side_effect = RuntimeError("connection reset")

        client = LlmClient(model="gpt-4o")
        with pytest.raises(LlmError, match="connection reset"):
            client.call(system="sys", user="usr")
