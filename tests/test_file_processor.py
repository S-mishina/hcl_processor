import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
import os
from hcl_processor.file_processor import run_hcl_file_workflow, read_tf_file, read_local_files, get_modules_name

def test_read_tf_file_exists(tmp_path):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    content, directory = read_tf_file(str(file_path))
    assert content == "content"
    assert directory == str(tmp_path)

def test_read_tf_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_tf_file("nonexistent.tf")

@patch("hcl_processor.file_processor.hcl2.loads", return_value={"key": "value"})
def test_read_local_files_success(mock_hcl2, tmp_path):
    file_path = tmp_path / "local.tf"
    file_path.write_text("content")
    local_files = [{"env": str(file_path)}]
    result = read_local_files(local_files)
    assert "env" in result

def test_read_local_files_file_not_found():
    local_files = [{"env": "nonexistent.tf"}]
    with pytest.raises(FileNotFoundError):
        read_local_files(local_files)

@patch("hcl_processor.file_processor.hcl2.loads", side_effect=Exception("parse error"))
def test_read_local_files_parse_error(mock_hcl2, tmp_path):
    file_path = tmp_path / "local.tf"
    file_path.write_text("content")
    local_files = [{"env": str(file_path)}]
    with pytest.raises(Exception):
        read_local_files(local_files)

def test_get_modules_name_success():
    resource_dict = {"module": [{"module_name": {"monitors": "data"}}]}
    result = get_modules_name(resource_dict)
    assert result == "module_name"

def test_get_modules_name_not_found():
    resource_dict = {"module": [{"module_name": {"other": "data"}}]}
    with pytest.raises(ValueError):
        get_modules_name(resource_dict)

@patch("hcl_processor.file_processor.open", new_callable=mock_open)
@patch("hcl_processor.file_processor.os.makedirs")
@patch("hcl_processor.file_processor.aws_bedrock", return_value='{"key": "value"}')
@patch("hcl_processor.file_processor.hcl2.loads", return_value={"resource": [{}], "module": [{"module_name": {"target": [{}]}}]})
def test_run_hcl_file_workflow_success(mock_hcl2, mock_bedrock, mock_makedirs, mock_open_func, tmp_path):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    module_path = tmp_path / "module.tf"
    module_path.write_text("content")
    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": False, "path": str(module_path)},
            "failback": {"enabled": False, "type": "resource"}
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}}
    }
    system_config = {}
    with patch("hcl_processor.file_processor.validate_output_json", return_value={"validated": True}), \
         patch("hcl_processor.file_processor.output_md") as mock_output_md:
        run_hcl_file_workflow(str(file_path), config, system_config)
        mock_output_md.assert_called()

@patch("hcl_processor.file_processor.read_tf_file", return_value=(None, None))
def test_run_hcl_file_workflow_file_not_found(mock_read_tf):
    config = {"input": {"local_files": [], "modules": {"enabled": False}}, "output": {"json_path": "out.json"}, "bedrock": {"output_json": {}}}
    system_config = {}
    with pytest.raises(FileNotFoundError):
        run_hcl_file_workflow("missing.tf", config, system_config)

@patch("hcl_processor.file_processor.hcl2.loads", side_effect=Exception("parse error"))
def test_run_hcl_file_workflow_parse_error(mock_hcl2, tmp_path):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    config = {"input": {"local_files": [], "modules": {"enabled": False}}, "output": {"json_path": str(tmp_path / "out.json")}, "bedrock": {"output_json": {}}}
    system_config = {}
    with pytest.raises(Exception):
        run_hcl_file_workflow(str(file_path), config, system_config)

@patch("hcl_processor.file_processor.aws_bedrock", side_effect=json.decoder.JSONDecodeError("Expecting value", "", 0))
@patch("hcl_processor.file_processor.get_modules_name", return_value="module_name")
@patch("hcl_processor.file_processor.validate_output_json", return_value=[{"result": True}])
@patch("hcl_processor.file_processor.read_tf_file", side_effect=[("content", "dir"), ("content", "dir")])
@patch("hcl_processor.file_processor.read_local_files", return_value="locals")
@patch("hcl_processor.file_processor.hcl2.loads", return_value={"resource": [{"r1": {}}], "module": [{"module_name": {"target": [{}]}}]})
@patch("hcl_processor.file_processor.open", new_callable=mock_open)
@patch("hcl_processor.file_processor.os.makedirs")
def test_run_hcl_file_workflow_failback(mock_makedirs, mock_open_func, mock_hcl2, mock_read_local, mock_read_tf, mock_validate, mock_get_module, mock_bedrock, tmp_path):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {"enabled": True, "type": "resource", "options": {"target": "target"}}
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}}
    }
    system_config = {}
    with patch("hcl_processor.file_processor.output_md") as mock_output_md:
        run_hcl_file_workflow(str(file_path), config, system_config)
        mock_output_md.assert_called()
