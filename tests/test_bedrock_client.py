import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import (ClientError, EndpointConnectionError,
                               ReadTimeoutError)

from hcl_processor.bedrock_client import BedrockProvider
from hcl_processor.llm_provider import PayloadTooLargeError


def build_config():
    return {
        "provider_config": {
            "name": "bedrock",
            "settings": {
                "aws_profile": "test-profile",
                "system_prompt": "Test system prompt",
                "payload": {
                    "anthropic_version": "v1",
                    "max_tokens": 100,
                    "temperature": 0.5,
                    "top_p": 1.0,
                    "top_k": 40,
                },
                "output_json": {"type": "object", "properties": {"monitors": {"type": "array", "items": {"type": "object"}}}},
                "model_id": "test-model",
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
        "default_bedrock": {
            "timeout_config": {
                "read_timeout": 10,
                "connect_timeout": 10,
                "retries": {"max_attempts": 3, "mode": "standard"},
            },
            "payload": {
                "anthropic_version": "v1",
                "max_tokens": 100,
                "temperature": 0.5,
                "top_p": 1.0,
                "top_k": 40,
            },
        },
        "constants": {
            "bedrock": {
                "default_model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "tool_name": "json_validator",
                "target_json_key": "monitors"
            }
        },
    }


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_invoke_single_success(mock_session):
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tooluse_test",
                            "name": "json_validator",
                            "input": {
                                "monitors": [
                                    {
                                        "monitor_name": "Test Monitor",
                                        "type": "query alert"
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single(
        "prompt", "modules_data"
    )
    mock_client.converse.assert_called_once()
    call_kwargs = mock_client.converse.call_args.kwargs
    assert "toolConfig" in call_kwargs
    # The output_json is passed directly now, not constructed within the test
    assert call_kwargs["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"] == config["provider_config"]["settings"]["output_json"]

    expected = json.dumps({"monitors": [{"monitor_name": "Test Monitor", "type": "query alert"}]}, ensure_ascii=False)
    assert result == expected


@patch("hcl_processor.bedrock_client.boto3.Session")
@pytest.mark.parametrize(
    "exception_type, exception_message, expected_exception",
    [
        (EndpointConnectionError, "test", EndpointConnectionError),
        (ReadTimeoutError, "timeout", ReadTimeoutError),
        (ClientError, {"Error": {"Code": "Test", "Message": "normal client error"}}, ClientError),
        (ClientError, {"Error": {"Code": "ValidationException", "Message": "Input token size exceeds limit"}}, PayloadTooLargeError),
        (Exception, "general", Exception),
    ],
)
def test_bedrock_provider_api_exceptions(mock_session, exception_type, exception_message, expected_exception):
    mock_client = MagicMock()

    if exception_type == ClientError:
        exception_instance = ClientError(error_response=exception_message, operation_name="test")
    elif exception_type == EndpointConnectionError:
        exception_instance = EndpointConnectionError(endpoint_url=exception_message)
    elif exception_type == ReadTimeoutError:
        exception_instance = ReadTimeoutError(endpoint_url="test", error=exception_message)
    else:
        exception_instance = exception_type(exception_message)

    mock_client.converse.side_effect = exception_instance
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    with pytest.raises(expected_exception):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_attribute_error(mock_session):
    mock_client = MagicMock()
    mock_response = {"output": None}  # will raise AttributeError when accessing message
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    with pytest.raises(AttributeError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_json_decode_error(mock_session):
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"invalid": "format"}]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    with pytest.raises(json.JSONDecodeError):
        provider.invoke_single("prompt", "modules_data")


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_modules_disabled(mock_session):
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "response text"}]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    config["modules"]["enabled"] = False
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_modules_data_none(mock_session):
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "response text"}]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single("prompt", None)
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_defaults_used(mock_session):
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "response text"}]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    config["provider_config"]["settings"]["payload"].pop("max_tokens", None)  # force default use
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_array_schema_wrapped_in_object(mock_session):
    """Test that array schemas are wrapped in object for Bedrock API compatibility."""
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tooluse_test",
                            "name": "json_validator",
                            "input": {
                                "data": [
                                    {"monitor_name": "Test Monitor 1"},
                                    {"monitor_name": "Test Monitor 2"}
                                ]
                            }
                        }
                    }
                ]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    # Set array schema
    config["provider_config"]["settings"]["output_json"] = {
        "type": "array",
        "items": {"type": "object", "properties": {"monitor_name": {"type": "string"}}}
    }
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")

    # Verify schema was wrapped in object for API call
    call_kwargs = mock_client.converse.call_args.kwargs
    sent_schema = call_kwargs["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"]
    assert sent_schema["type"] == "object"
    assert "data" in sent_schema["properties"]
    assert sent_schema["properties"]["data"]["type"] == "array"

    # Verify response was unwrapped back to array
    expected = json.dumps([{"monitor_name": "Test Monitor 1"}, {"monitor_name": "Test Monitor 2"}], ensure_ascii=False)
    assert result == expected


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_bedrock_provider_object_schema_not_wrapped(mock_session):
    """Test that object schemas are not wrapped."""
    mock_client = MagicMock()
    mock_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tooluse_test",
                            "name": "json_validator",
                            "input": {"monitors": [{"name": "test"}]}
                        }
                    }
                ]
            }
        }
    }
    mock_client.converse.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    # Object schema (default in build_config)
    system_config = build_system_config()
    provider = BedrockProvider(config, system_config)

    result = provider.invoke_single("prompt", "modules_data")

    # Verify schema was NOT wrapped
    call_kwargs = mock_client.converse.call_args.kwargs
    sent_schema = call_kwargs["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"]
    assert sent_schema == config["provider_config"]["settings"]["output_json"]
    assert "data" not in sent_schema.get("properties", {})

    # Verify response is returned as-is
    expected = json.dumps({"monitors": [{"name": "test"}]}, ensure_ascii=False)
    assert result == expected
