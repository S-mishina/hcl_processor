import pytest
from unittest.mock import patch, mock_open
import yaml
import json

from src.hcl_analytics.config_loader import load_system_config, load_config

def test_load_system_config_success():
    mock_yaml = yaml.dump({"system_prompt": "hello"})
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mock_yaml)):
        result = load_system_config("dummy_path.yaml")
        assert result["system_prompt"] == "hello"

def test_load_system_config_file_not_found():
    with patch("os.path.exists", return_value=False):
        with pytest.raises(ValueError, match="System config file not found"):
            load_system_config("dummy_path.yaml")

def test_load_system_config_yaml_error():
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="invalid: [:::")):
        with pytest.raises(ValueError, match="System config could not be loaded"):
            load_system_config("dummy_path.yaml")

def test_load_system_config_none():
    mock_yaml = ""
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="System config is None"):
            load_system_config("dummy_path.yaml")

def test_load_system_config_not_dict():
    mock_yaml = yaml.dump(["not", "a", "dict"])
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="System config is not a dictionary"):
            load_system_config("dummy_path.yaml")

def test_load_system_config_system_prompt_not_string():
    mock_yaml = yaml.dump({"system_prompt": 123})
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="System prompt is missing or not a string"):
            load_system_config("dummy_path.yaml")

def test_load_config_success():
    config_dict = {
        "bedrock": {
            "system_prompt": "hi",
            "payload": {
                "anthropic_version": "v1",
                "max_tokens": 100,
                "temperature": 0.5,
                "top_p": 1.0,
                "top_k": 40
            },
            "read_timeout": 10,
            "connect_timeout": 10,
            "retries": {},
            "output_json": {}
        },
        "input": {
            "resource_data": {"folder": "some_folder"},
            "modules": {"path": "some_path", "enabled": True},
            "local_files": []
        },
        "output": {
            "json_path": "output.json",
            "markdown_path": "output.md"
        }
    }
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        result = load_config("dummy_config.yaml")
        assert result["bedrock"]["system_prompt"] == "hi"

def test_load_config_output_json_string():
    config_dict = {
        "bedrock": {
            "system_prompt": "hi",
            "payload": {
                "anthropic_version": "v1",
                "max_tokens": 100,
                "temperature": 0.5,
                "top_p": 1.0,
                "top_k": 40
            },
            "read_timeout": 10,
            "connect_timeout": 10,
            "retries": {},
            "output_json": json.dumps({"key": "value"})
        },
        "input": {
            "resource_data": {"folder": "some_folder"},
            "modules": {"path": "some_path", "enabled": True},
            "local_files": []
        },
        "output": {
            "json_path": "output.json",
            "markdown_path": "output.md"
        }
    }
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        result = load_config("dummy_config.yaml")
        assert result["bedrock"]["output_json"]["key"] == "value"

def test_load_config_broken_output_json():
    config_dict = {
        "bedrock": {
            "system_prompt": "hi",
            "payload": {
                "anthropic_version": "v1",
                "max_tokens": 100,
                "temperature": 0.5,
                "top_p": 1.0,
                "top_k": 40
            },
            "read_timeout": 10,
            "connect_timeout": 10,
            "retries": {},
            "output_json": "{bad json}"
        },
        "input": {
            "resource_data": {"folder": "some_folder"},
            "modules": {"path": "some_path", "enabled": True},
            "local_files": []
        },
        "output": {
            "json_path": "output.json",
            "markdown_path": "output.md"
        }
    }
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="Invalid JSON in output_json"):
          load_config("dummy_config.yaml")

def test_load_config_schema_validation_error():
    bad_config = {"invalid": "data"}
    mock_yaml = yaml.dump(bad_config)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="Invalid configuration"):
            load_config("dummy_config.yaml")

def test_load_config_yaml_parse_error():
    with patch("builtins.open", mock_open(read_data="invalid: [:::")):
        with pytest.raises(yaml.YAMLError):
            load_config("dummy_config.yaml")
