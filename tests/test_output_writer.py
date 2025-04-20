import json
from unittest.mock import patch

import pytest

from hcl_processor.output_writer import (clean_cell, output_md,
                                         validate_output_json,
                                         validate_template_placeholders)


# ----- output_md -----
def test_output_md_with_dict(tmp_path):
    config = {
        "output": {
            "json_path": str(tmp_path / "test.json"),
            "markdown_path": str(tmp_path / "output.md"),
            "markdown_template": "#### {title} \n {table}",
        },
        "schema_columns": ["col1", "col2"],
    }
    data = {"col1": "val1", "col2": "val2"}
    with open(config["output"]["json_path"], "w") as f:
        json.dump(data, f)

    with patch("hcl_processor.output_writer.os.remove") as mock_remove:
        output_md("Test Title", config)
        with open(config["output"]["markdown_path"], "r") as f:
            content = f.read()
            assert "#### Test Title" in content
            assert "val1" in content
        mock_remove.assert_called_once()


def test_output_md_with_list(tmp_path):
    config = {
        "output": {
            "json_path": str(tmp_path / "test.json"),
            "markdown_path": str(tmp_path / "output.md"),
        },
        "schema_columns": ["col1", "col2"],
    }
    data = [{"col1": "val1", "col2": "val2"}, {"col1": "val3", "col2": "val4"}]
    with open(config["output"]["json_path"], "w") as f:
        json.dump(data, f)

    with patch("hcl_processor.output_writer.os.remove") as mock_remove:
        output_md("Test Title", config)
        with open(config["output"]["markdown_path"], "r") as f:
            content = f.read()
            assert "val3" in content
        mock_remove.assert_called_once()


def test_output_md_missing_json(tmp_path):
    config = {
        "output": {
            "json_path": str(tmp_path / "missing.json"),
            "markdown_path": str(tmp_path / "output.md"),
        },
        "schema_columns": ["col1", "col2"],
    }
    with pytest.raises(FileNotFoundError):
        output_md("Test Title", config)


def test_output_md_invalid_template(tmp_path):
    config = {
        "output": {
            "json_path": str(tmp_path / "test.json"),
            "markdown_path": str(tmp_path / "output.md"),
            "markdown_template": "#### {invalid}",
        },
        "schema_columns": ["col1", "col2"],
    }
    data = {"col1": "val1", "col2": "val2"}
    with open(config["output"]["json_path"], "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Unsupported template variable"):
        output_md("Test Title", config)


def test_clean_cell_string():
    input_str = "line1\nline2|with{braces}"
    cleaned = clean_cell(input_str)
    assert "<br>" in cleaned
    assert "\\|" in cleaned


def test_clean_cell_non_string():
    value = 123
    assert clean_cell(value) == 123


def test_validate_template_placeholders_valid():
    template = "#### {title} \n {table}"
    allowed = {"title", "table"}
    validate_template_placeholders(template, allowed)  # should not raise


def test_validate_template_placeholders_invalid():
    template = "#### {unknown}"
    allowed = {"title", "table"}
    with pytest.raises(ValueError, match="Unsupported template variable"):
        validate_template_placeholders(template, allowed)


def test_validate_output_json_success():
    schema = {
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    }
    output_str = json.dumps({"key": "value"})
    result = validate_output_json(output_str, schema)
    assert result["key"] == "value"


def test_validate_output_json_invalid_json():
    schema = {}
    with pytest.raises(json.JSONDecodeError):
        validate_output_json("{bad json}", schema)


def test_validate_output_json_schema_error():
    schema = {
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    }
    output_str = json.dumps({"wrong": "value"})
    with pytest.raises(Exception):
        validate_output_json(output_str, schema)
