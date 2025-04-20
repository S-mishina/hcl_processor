import pytest
from unittest.mock import patch, MagicMock
import logging
import os
from src.hcl_analytics import main as main_module

def setup_logger():
    main_module.logger = logging.getLogger("test_logger")

setup_logger()

@patch("src.hcl_analytics.main.os.walk", return_value=[("/folder", [], ["file1.tf", "file2.txt"])])
@patch("src.hcl_analytics.main.run_hcl_file_workflow")
@patch("src.hcl_analytics.main.load_config", return_value={
    "input": {"resource_data": {"folder": "/folder"}},
    "bedrock": {"output_json": {}},
    "system_call": {"exit_success": 0}
})
@patch("src.hcl_analytics.main.load_system_config", return_value={
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
})
def test_main_process_folder(mock_sys_config, mock_config, mock_run, mock_walk):
    exit_code = main_module.main("config.yaml")
    assert exit_code == 0

@patch("src.hcl_analytics.main.load_system_config", return_value={
    "system_prompt": "...",
    "system_call": {"exit_bedrock_error": 5}
})
@patch("src.hcl_analytics.main.load_config", return_value={
    "input": {"resource_data": {"files": ["file1.tf"]}},
    "bedrock": {"output_json": {}},
    "system_call": {"exit_success": 0}
})
@patch("src.hcl_analytics.main.run_hcl_file_workflow", side_effect=MagicMock(side_effect=Exception("fail")))
def test_main_api_exceptions(mock_run, mock_config, mock_sys_config):
    with patch("src.hcl_analytics.main.EndpointConnectionError", Exception):
        exit_code = main_module.main("config.yaml")
        assert exit_code == 5
