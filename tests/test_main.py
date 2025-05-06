import pytest
from unittest.mock import patch, MagicMock

import hcl_processor.main as main_module

# 共通モック値
mock_system_config = {
    "system_prompt": "...",
    "system_call": {
        "exit_success": 0,
        "exit_system_config_error": 1,
        "exit_config_error": 2,
        "exit_file_read_error": 3,
        "exit_validation_error": 4,
        "exit_bedrock_error": 5,
        "exit_unknown_error": 99
    }
}

mock_config = {
    "input": {"resource_data": {"files": ["file1.tf"]}},
    "bedrock": {"output_json": {}},
    "system_call": {"exit_success": 0}
}

@patch("hcl_processor.main.parse_args")
@patch("hcl_processor.main.load_system_config", side_effect=Exception("fail"))
def test_main_system_config_failure(mock_load_sys, mock_parse):
    mock_parse.return_value = MagicMock(config_file="config.yaml", debug=False)
    exit_code = main_module.main()
    assert exit_code == 1

@patch("hcl_processor.main.parse_args")
@patch("hcl_processor.main.load_system_config", return_value=mock_system_config)
@patch("hcl_processor.main.load_config", side_effect=ValueError("config fail"))
def test_main_config_failure(mock_load_config, mock_load_sys, mock_parse):
    mock_parse.return_value = MagicMock(config_file="config.yaml", debug=False)
    exit_code = main_module.main()
    assert exit_code == mock_system_config["system_call"]["exit_config_error"]
