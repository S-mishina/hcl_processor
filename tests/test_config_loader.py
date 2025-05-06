import pytest
from unittest.mock import patch, mock_open
import yaml
import json

from hcl_processor.config_loader import load_system_config, load_config

# -------- load_config tests -------- #

def create_valid_config():
    return {
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

def test_load_config_success():
    config_dict = create_valid_config()
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        result = load_config("dummy_config.yaml")
        assert result["bedrock"]["system_prompt"] == "hi"

def test_load_config_output_json_string():
    config_dict = create_valid_config()
    config_dict["bedrock"]["output_json"] = json.dumps({"key": "value"})
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        result = load_config("dummy_config.yaml")
        assert result["bedrock"]["output_json"]["key"] == "value"

def test_load_config_invalid_output_json():
    config_dict = create_valid_config()
    config_dict["bedrock"]["output_json"] = "{bad json}"
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="Invalid JSON in output_json"):
            load_config("dummy_config.yaml")

def test_load_config_schema_validation_error():
    config_dict = create_valid_config()
    del config_dict["input"]  # Remove required section
    mock_yaml = yaml.dump(config_dict)
    with patch("builtins.open", mock_open(read_data=mock_yaml)):
        with pytest.raises(ValueError, match="Invalid configuration"):
            load_config("dummy_config.yaml")

def test_load_config_yaml_parse_error():
    broken_yaml = "invalid: [:::"
    with patch("builtins.open", mock_open(read_data=broken_yaml)):
        with pytest.raises(yaml.YAMLError):  # More precise exception
            load_config("dummy_config.yaml")
