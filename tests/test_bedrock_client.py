import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 ReadTimeoutError)

from hcl_processor.bedrock_client import aws_bedrock  # ← あなたの環境に合わせて修正


def build_config():
    return {
        "bedrock": {
            "aws_profile": "test-profile",
            "system_prompt": "Test system prompt",
            "payload": {
                "anthropic_version": "v1",
                "max_tokens": 100,
                "temperature": 0.5,
                "top_p": 1.0,
                "top_k": 40,
            },
            "output_json": {},
            "model_id": "test-model",
        },
        "modules": {"enabled": True},
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
    }


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_success(mock_session):
    mock_client = MagicMock()
    mock_streaming_body = MagicMock()
    mock_streaming_body.read.return_value = json.dumps(
        {"content": [{"text": "response text"}]}
    ).encode("utf-8")

    mock_response = {
        "ResponseMetadata": {},
        "contentType": "application/json",
        "body": mock_streaming_body,
    }
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    result = aws_bedrock(
        "prompt", "modules_data", build_config(), build_system_config()
    )
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
@pytest.mark.parametrize(
    "exception",
    [
        EndpointConnectionError(endpoint_url="test"),
        ReadTimeoutError(endpoint_url="test", error="timeout"),
        ClientError(error_response={}, operation_name="test"),
        Exception("general"),
    ],
)
def test_aws_bedrock_api_exceptions(mock_session, exception):
    mock_client = MagicMock()
    mock_client.invoke_model.side_effect = exception
    mock_session.return_value.client.return_value = mock_client

    with pytest.raises(type(exception)):
        aws_bedrock("prompt", "modules_data", build_config(), build_system_config())


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_attribute_error(mock_session):
    mock_client = MagicMock()
    mock_response = {"body": None}  # .read() will raise AttributeError
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    with pytest.raises(AttributeError):
        aws_bedrock("prompt", "modules_data", build_config(), build_system_config())


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_json_decode_error(mock_session):
    mock_client = MagicMock()
    mock_streaming_body = MagicMock()
    mock_streaming_body.read.return_value = b"{bad json}"

    mock_response = {"body": mock_streaming_body}
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    with pytest.raises(json.JSONDecodeError):
        aws_bedrock("prompt", "modules_data", build_config(), build_system_config())


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_modules_disabled(mock_session):
    mock_client = MagicMock()
    mock_streaming_body = MagicMock()
    mock_streaming_body.read.return_value = json.dumps(
        {"content": [{"text": "response text"}]}
    ).encode("utf-8")
    mock_response = {"body": mock_streaming_body}
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    config["modules"]["enabled"] = False

    result = aws_bedrock("prompt", "modules_data", config, build_system_config())
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_modules_data_none(mock_session):
    mock_client = MagicMock()
    mock_streaming_body = MagicMock()
    mock_streaming_body.read.return_value = json.dumps(
        {"content": [{"text": "response text"}]}
    ).encode("utf-8")
    mock_response = {"body": mock_streaming_body}
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    result = aws_bedrock("prompt", None, build_config(), build_system_config())
    assert result == "response text"


@patch("hcl_processor.bedrock_client.boto3.Session")
def test_aws_bedrock_defaults_used(mock_session):
    mock_client = MagicMock()
    mock_streaming_body = MagicMock()
    mock_streaming_body.read.return_value = json.dumps(
        {"content": [{"text": "response text"}]}
    ).encode("utf-8")
    mock_response = {"body": mock_streaming_body}
    mock_client.invoke_model.return_value = mock_response
    mock_session.return_value.client.return_value = mock_client

    config = build_config()
    config["bedrock"]["payload"].pop("max_tokens", None)  # force default use

    result = aws_bedrock("prompt", "modules_data", config, build_system_config())
    assert result == "response text"
