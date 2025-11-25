import json
from unittest.mock import MagicMock, patch

import pytest

from hcl_processor.gemini_client import GeminiProvider
from hcl_processor.llm_provider import PayloadTooLargeError


class MockClientError(Exception):
    """Mock ClientError for testing since real ClientError requires response_json."""
    pass


def build_config():
    return {
        "provider_config": {
            "name": "gemini",
            "settings": {
                "gcp_project": "test-project",
                "gcp_region": "us-central1",
                "system_prompt": "Test system prompt",
                "payload": {
                    "max_tokens": 100,
                    "temperature": 0.5,
                    "top_p": 1.0,
                    "top_k": 40,
                },
                "output_json": {
                    "type": "object",
                    "properties": {
                        "monitors": {
                            "type": "array",
                            "items": {"type": "object"}
                        }
                    }
                },
                "model_name": "gemini-2.0-flash",
            }
        },
        "modules": {"enabled": True},
        "output": {
            "markdown_path": "/tmp/test_output.md"
        },
    }


def build_system_config():
    return {
        "system_prompt": "System default",
        "default_gemini": {
            "gcp_region": "us-central1",
            "payload": {
                "max_tokens": 4096,
                "temperature": 0,
                "top_p": 1,
                "top_k": 0,
            },
        },
        "constants": {
            "gemini": {
                "default_model_name": "gemini-2.0-flash",
                "target_json_key": "monitors"
            }
        },
    }


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_invoke_single_success(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "monitors": [
            {
                "monitor_name": "Test Monitor",
                "type": "query alert"
            }
        ]
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")

    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert "config" in call_kwargs
    assert call_kwargs["config"].response_mime_type == "application/json"

    expected = json.dumps({"monitors": [{"monitor_name": "Test Monitor", "type": "query alert"}]})
    assert result == expected


@patch("hcl_processor.gemini_client.ClientError", MockClientError)
@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_payload_too_large_error(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockClientError(
        "Request payload size exceeds the limit"
    )
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    with pytest.raises(PayloadTooLargeError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.gemini_client.ClientError", MockClientError)
@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_token_limit_error(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockClientError(
        "Token limit exceeded"
    )
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    with pytest.raises(PayloadTooLargeError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.gemini_client.ClientError", MockClientError)
@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_client_error_non_size_related(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockClientError(
        "Authentication failed"
    )
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    with pytest.raises(MockClientError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_general_exception(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Unexpected error")
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    with pytest.raises(Exception):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_empty_response(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    with pytest.raises(json.JSONDecodeError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_modules_disabled(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"result": "success"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    config = build_config()
    config["modules"]["enabled"] = False
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")
    assert result == '{"result": "success"}'


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_modules_data_none(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"result": "success"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    result = provider.invoke_single("prompt", None)
    assert result == '{"result": "success"}'


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_output_schema_property(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    assert provider.output_schema == config["provider_config"]["settings"]["output_json"]


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_schema_conversion(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    # Test lowercase to uppercase conversion
    input_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"}
            }
        }
    }

    converted = provider._convert_schema_to_gemini_format(input_schema)

    assert converted["type"] == "ARRAY"
    assert converted["items"]["type"] == "OBJECT"
    assert converted["items"]["properties"]["name"]["type"] == "STRING"
    assert converted["items"]["properties"]["count"]["type"] == "INTEGER"


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_defaults_used(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"result": "success"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    config = build_config()
    config["provider_config"]["settings"]["payload"].pop("max_tokens", None)
    system_config = build_system_config()
    provider = GeminiProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")
    assert result == '{"result": "success"}'


@patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "env-project"})
@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_project_from_env(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    config = build_config()
    config["provider_config"]["settings"].pop("gcp_project", None)
    system_config = build_system_config()

    provider = GeminiProvider(config, system_config)

    # Should not raise an error when project is from env
    assert provider.gemini_client is not None


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_missing_project_error(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    config = build_config()
    config["provider_config"]["settings"].pop("gcp_project", None)
    system_config = build_system_config()

    with patch.dict("os.environ", {}, clear=True):
        # Remove GOOGLE_CLOUD_PROJECT from environment
        import os
        if "GOOGLE_CLOUD_PROJECT" in os.environ:
            del os.environ["GOOGLE_CLOUD_PROJECT"]

        with pytest.raises(ValueError, match="GCP project not found"):
            GeminiProvider(config, system_config)


@patch("hcl_processor.gemini_client.genai.Client")
def test_gemini_provider_with_credentials_file(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    config = build_config()
    config["provider_config"]["settings"]["gcp_credentials_file"] = "/path/to/creds.json"
    system_config = build_system_config()

    with patch.dict("os.environ", {}, clear=False):
        provider = GeminiProvider(config, system_config)
        import os
        assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == "/path/to/creds.json"
