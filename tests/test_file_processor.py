from unittest.mock import MagicMock, mock_open, patch

import pytest

from hcl_processor.file_processor import (get_modules_name, read_local_files,
                                          read_tf_file, run_hcl_file_workflow)
from hcl_processor.llm_provider import PayloadTooLargeError


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
    result = get_modules_name(resource_dict, "monitors")
    assert result == "module_name"


def test_get_modules_name_not_found():
    resource_dict = {"module": [{"module_name": {"other": "data"}}]}
    with pytest.raises(ValueError):
        get_modules_name(resource_dict)


@patch("hcl_processor.file_processor.open", new_callable=mock_open)
@patch("hcl_processor.file_processor.os.makedirs")
@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function, not its import
def test_run_hcl_file_workflow_success(
    mock_create_llm_provider, mock_makedirs, mock_open_func, tmp_path
):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    module_path = tmp_path / "module.tf"
    module_path.write_text("content")
    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": False, "path": str(module_path)},
            "failback": {"enabled": False, "type": "resource"},
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf"
            }
        }
    }

    mock_provider_instance = MagicMock()
    mock_provider_instance.invoke_single.return_value = '{"key": "value"}'
    mock_create_llm_provider.return_value = mock_provider_instance

    with patch(
        "hcl_processor.file_processor.validate_output_json",
        return_value={"validated": True},
    ), patch("hcl_processor.file_processor.output_md") as mock_output_md:
        run_hcl_file_workflow(str(file_path), config, system_config)
        mock_output_md.assert_called()
        mock_provider_instance.invoke_single.assert_called_once()


@patch("hcl_processor.file_processor.read_tf_file", return_value=(None, None))
def test_run_hcl_file_workflow_file_not_found(mock_read_tf):
    config = {
        "input": {"local_files": [], "modules": {"enabled": False}},
        "output": {"json_path": "out.json"},
        "bedrock": {"output_json": {}},
    }
    system_config = {}
    with pytest.raises(FileNotFoundError):
        run_hcl_file_workflow("missing.tf", config, system_config)


@patch("hcl_processor.file_processor.hcl2.loads", side_effect=Exception("parse error"))
def test_run_hcl_file_workflow_parse_error(mock_hcl2, tmp_path):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    config = {
        "input": {"local_files": [], "modules": {"enabled": False}},
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {}
    with pytest.raises(Exception):
        run_hcl_file_workflow(str(file_path), config, system_config)


@patch("hcl_processor.file_processor.create_llm_provider")
@patch(
    "hcl_processor.file_processor.validate_output_json", return_value=[{"result": True}]
)
@patch(
    "hcl_processor.file_processor.read_tf_file",
    side_effect=[("content", "dir"), ("content", "dir")],
)
@patch("hcl_processor.file_processor.read_local_files", return_value="locals")
@patch(
    "hcl_processor.file_processor.hcl2.loads",
    return_value={
        "resource": [{"r1": {}}],
        "module": [{"module_name": {"target": [{}]}}],
    },
)
@patch("hcl_processor.file_processor.open", new_callable=mock_open)
@patch("hcl_processor.file_processor.os.makedirs")
def test_run_hcl_file_workflow_failback(
    mock_makedirs,
    mock_open_func,
    mock_hcl2,
    mock_read_local,
    mock_read_tf,
    mock_validate,
    mock_create_llm_provider, # Updated mock name
    tmp_path,
):
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")
    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {
                "enabled": True,
                "type": "resource",
                "options": {"target": "target"},
            },
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf",
                "default_search_resource": "target"
            }
        }
    }

    mock_provider_instance = MagicMock()
    # First call raises PayloadTooLargeError, subsequent chunk calls succeed
    mock_provider_instance.invoke_single.side_effect = [
        PayloadTooLargeError("main call failed"),
        '{"result": "success1"}',
        '{"result": "success2"}' # If there are multiple resource chunks
    ]
    mock_create_llm_provider.return_value = mock_provider_instance

    with patch("hcl_processor.file_processor.output_md") as mock_output_md:
        run_hcl_file_workflow(str(file_path), config, system_config)
        mock_output_md.assert_called()
        # Assert provider.invoke_single was called for main call + each chunk
        assert mock_provider_instance.invoke_single.call_count > 1


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.hcl2.loads")
@patch("hcl_processor.file_processor.validate_output_json")
@patch("hcl_processor.file_processor.get_modules_name")
@patch("hcl_processor.file_processor.output_md")
def test_failback_resource_type_branch(mock_output_md, mock_get_module, mock_validate, mock_hcl2, mock_create_llm_provider, tmp_path):
    """Test resource type branch in failback processing (lines 68-70)"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {
                "enabled": True,
                "type": "resource",  # Test resource type branch
                "options": {"target": "monitors"},
            },
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf",
                "default_search_resource": "monitors"
            }
        }
    }

    # Mock resource structure for resource type failback
    mock_hcl2.return_value = {
        "resource": [{"res1": {}}, {"res2": {}}],
        "module": [{"test_module": {"monitors": [{}]}}]
    }
    mock_get_module.return_value = "test_module"

    mock_provider_instance = MagicMock()
    # First call raises PayloadTooLargeError, subsequent calls succeed
    mock_provider_instance.invoke_single.side_effect = [
        PayloadTooLargeError("main call failed"),
        '{"result": "success1"}',
        '{"result": "success2"}'
    ]
    mock_create_llm_provider.return_value = mock_provider_instance

    mock_validate.side_effect = [
        [{"result": "success1"}],
        [{"result": "success2"}]
    ]

    run_hcl_file_workflow(str(file_path), config, system_config)
    mock_output_md.assert_called()
    assert mock_provider_instance.invoke_single.call_count > 1


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.hcl2.loads")
@patch("hcl_processor.file_processor.validate_output_json")
@patch("hcl_processor.file_processor.get_modules_name")
@patch("hcl_processor.file_processor.output_md")
def test_failback_chunk_error_pass_strategy(mock_output_md, mock_get_module, mock_validate, mock_hcl2, mock_create_llm_provider, tmp_path):
    """Test individual chunk error handling with pass strategy (lines 84-85)"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {
                "enabled": True,
                "type": "module",
                "options": {"target": "monitors"},
            },
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf",
                "default_search_resource": "monitors"
            }
        }
    }

    mock_hcl2.return_value = {
        "module": [{"test_module": {"monitors": [{"chunk1": {}}, {"chunk2": {}}, {"chunk3": {}}]}}]
    }
    mock_get_module.return_value = "test_module"

    mock_provider_instance = MagicMock()
    # First call raises PayloadTooLargeError, then mixed chunk results
    mock_provider_instance.invoke_single.side_effect = [
        PayloadTooLargeError("main call failed"),
        '{"result": "chunk1_success"}',  # Chunk 1 succeeds
        Exception("Chunk 2 error"),     # Chunk 2 fails (tests pass strategy)
        '{"result": "chunk3_success"}'   # Chunk 3 succeeds
    ]
    mock_create_llm_provider.return_value = mock_provider_instance

    mock_validate.side_effect = [
        [{"result": "chunk1_success"}],
        [{"result": "chunk3_success"}]
    ]

    # Should not raise exception due to pass strategy
    run_hcl_file_workflow(str(file_path), config, system_config)
    mock_output_md.assert_called()
    assert mock_provider_instance.invoke_single.call_count > 1 # Main call + at least 2 successful chunks


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.hcl2.loads")
@patch("hcl_processor.file_processor.validate_output_json")
@patch("hcl_processor.file_processor.get_modules_name")
@patch("hcl_processor.file_processor.output_md")
def test_failback_extend_error_handling(mock_output_md, mock_get_module, mock_validate, mock_hcl2, mock_create_llm_provider, tmp_path):
    """Test error in flattened list extend operation (lines 88-91)"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {
                "enabled": True,
                "type": "module",
                "options": {"target": "monitors"},
            },
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf",
                "default_search_resource": "monitors"
            }
        }
    }

    mock_hcl2.return_value = {
        "module": [{"test_module": {"monitors": [{"chunk1": {}}]}}]
    }
    mock_get_module.return_value = "test_module"

    mock_provider_instance = MagicMock()
    mock_provider_instance.invoke_single.side_effect = [
        PayloadTooLargeError("main call failed"),
        '{"result": "success"}'
    ]
    mock_create_llm_provider.return_value = mock_provider_instance

    # Return non-iterable to trigger extend error in flatten logic
    mock_validate.return_value = "not_a_list" 

    # Should handle extend error gracefully and not raise an unhandled exception
    run_hcl_file_workflow(str(file_path), config, system_config)

    assert mock_provider_instance.invoke_single.call_count > 1


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.hcl2.loads")
@patch("hcl_processor.file_processor.logger")
def test_failback_disabled_debug_mode(mock_logger, mock_hcl2, mock_create_llm_provider, tmp_path):
    """Test failback disabled with debug mode (lines 101-105)"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": False},
            "failback": {"enabled": False},
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf"
            }
        }
    }

    mock_hcl2.return_value = {"resource": []}
    mock_provider_instance = MagicMock()
    mock_provider_instance.invoke_single.side_effect = PayloadTooLargeError("test")
    mock_create_llm_provider.return_value = mock_provider_instance
    mock_logger.isEnabledFor.return_value = True  # Debug mode enabled

    # Should raise exception in debug mode
    with pytest.raises(PayloadTooLargeError): # Expect PayloadTooLargeError now
        run_hcl_file_workflow(str(file_path), config, system_config)

    mock_provider_instance.invoke_single.assert_called_once()


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.hcl2.loads")
@patch("hcl_processor.file_processor.logger")
def test_failback_disabled_non_debug_mode(mock_logger, mock_hcl2, mock_create_llm_provider, tmp_path):
    """Test failback disabled without debug mode (lines 101-105)"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": False},
            "failback": {"enabled": False},
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf"
            }
        }
    }

    mock_hcl2.return_value = {"resource": []}
    mock_provider_instance = MagicMock()
    mock_provider_instance.invoke_single.side_effect = PayloadTooLargeError("test")
    mock_create_llm_provider.return_value = mock_provider_instance
    mock_logger.isEnabledFor.return_value = False  # Debug mode disabled

    # Should return without raising exception
    result = run_hcl_file_workflow(str(file_path), config, system_config)
    assert result is None
    mock_provider_instance.invoke_single.assert_called_once()


@patch("hcl_processor.file_processor.create_llm_provider") # Patch the actual function
@patch("hcl_processor.file_processor.open", new_callable=mock_open)
@patch("hcl_processor.file_processor.os.makedirs")
@patch("hcl_processor.file_processor.get_modules_name", return_value="module_name")
@patch(
    "hcl_processor.file_processor.hcl2.loads",
    return_value={
        "resource": [{"r1": {}}],
        "module": [{"module_name": {"target": [{}]}}],
    },
)
@patch("hcl_processor.file_processor.read_tf_file", return_value=("content", "dir"))
@patch("hcl_processor.file_processor.read_local_files", return_value="locals")
def test_empty_result_triggers_failback(
    mock_read_local,
    mock_read_tf,
    mock_hcl2,
    mock_get_module,
    mock_makedirs,
    mock_open_func,
    mock_create_llm_provider, # Updated mock name
    tmp_path,
):
    """Test that empty result from API triggers failback strategy"""
    file_path = tmp_path / "test.tf"
    file_path.write_text("content")

    config = {
        "input": {
            "local_files": [],
            "modules": {"enabled": True, "path": str(file_path)},
            "failback": {
                "enabled": True,
                "type": "module",
                "options": {"target": "target"},
            },
        },
        "output": {"json_path": str(tmp_path / "out.json")},
        "bedrock": {"output_json": {}},
    }
    system_config = {
        "constants": {
            "file_processing": {
                "terraform_extension": ".tf",
                "default_search_resource": "target"
            }
        }
    }

    mock_provider_instance = MagicMock()
    # First call returns empty list, subsequent calls in failback succeed
    mock_provider_instance.invoke_single.side_effect = [
        '[]',  # Main API call returns empty result
        '{"result": "success1"}',  # Failback chunk 1 succeeds
    ]
    mock_create_llm_provider.return_value = mock_provider_instance

    with patch(
        "hcl_processor.file_processor.validate_output_json",
        side_effect=[[], [{"result": "success1"}]],  # First empty, then success
    ), patch("hcl_processor.file_processor.output_md") as mock_output_md:
        run_hcl_file_workflow(str(file_path), config, system_config)
        mock_output_md.assert_called()
        assert mock_provider_instance.invoke_single.call_count > 1
