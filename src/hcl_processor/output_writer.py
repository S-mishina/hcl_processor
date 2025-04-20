import json
import logging
import os
import re
import string

import jsonschema
import pandas as pd

logger = logging.getLogger(__name__)


def output_md(md_title, config):
    """
    Generate a Markdown file from the JSON output.
    Args:
        md_title (str): The title for the Markdown file.
        config (dict): Configuration for the Markdown output.
    Raises:
        FileNotFoundError: If the JSON file does not exist or is empty.
        ValueError: If the JSON data is not valid.
    """
    with open(config["output"]["json_path"], "r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    else:
        df = pd.DataFrame(data)
    df = df.applymap(clean_cell)

    schema_columns = config.get("schema_columns")
    df = df[schema_columns]
    markdown_table = df.to_markdown(index=False)

    template = config["output"].get("markdown_template", "#### {title} \n {table}")
    validate_template_placeholders(template, {"title", "table"})
    os.makedirs(os.path.dirname(config["output"]["markdown_path"]), exist_ok=True)
    try:
        with open(config["output"]["markdown_path"], "a", encoding="utf-8") as md_file:
            rendered = template.format(title=md_title, table=markdown_table)
            logger.debug(f"Rendered Markdown:\n {rendered}")
            # TODO: Need to consider creating a temporary file.
            md_file.write(rendered + "\n")
        logger.info(f"Saved to Markdown file: {config['output']['markdown_path']}")
        logger.info(f"Deleting JSON file: {config['output']['json_path']}")
        if not logger.isEnabledFor(logging.DEBUG):
            os.remove(config["output"]["json_path"])
    except Exception as e:
        logger.debug(f"{e}")
        logger.error(f"Error writing Markdown output: {type(e).__name__}")
        raise


def clean_cell(cell):
    # TODO: Later, this should also be manageable from config.
    """
    Clean the cell content for Markdown formatting.
    Args:
        cell (str): The cell content to clean.
    Returns:
        str: The cleaned cell content.
    """
    if isinstance(cell, str):
        cell = (
            cell.replace("\n", "<br>")
            .replace("|", "\\|")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )
        cell = re.sub(r"(\$\{.*\})(<br>|$)", r"\1 \2", cell)
        cell = re.sub(r"(<br>)", r" \1 ", cell)
        return cell.strip()
    return cell


def validate_template_placeholders(template: str, allowed_keys: set):
    """
    Validate the placeholders in the template string.
    Args:
        template (str): The template string to validate.
        allowed_keys (set): Set of allowed keys for placeholders.
    Raises:
        ValueError: If any placeholder in the template is not in the allowed keys.
    """
    formatter = string.Formatter()
    for _, field_name, _, _ in formatter.parse(template):
        if field_name and field_name not in allowed_keys:
            raise ValueError(
                f"Unsupported template variable: '{field_name}' (allowed: {allowed_keys})"
            )


def validate_output_json(output_str, schema):
    """
    Validate the output JSON against the provided schema.
    Args:
        output_str (str): The output JSON string to validate.
        schema (dict): The JSON schema to validate against.
    Returns:
        dict: The parsed and validated JSON object.
    Raises:
        json.JSONDecodeError: If the output string is not valid JSON.
        jsonschema.ValidationError: If the output JSON does not match the schema.
    """
    try:
        parsed = json.loads(output_str)
        jsonschema.validate(instance=parsed, schema=schema)
        return parsed
    except json.JSONDecodeError as e:
        logger.debug(f"{e}")
        logger.error(f"Invalid JSON format: {type(e).__name__}")
        raise
    except jsonschema.ValidationError as e:
        logger.debug(f"{e}")
        logger.error(f"Output JSON does not match schema: {type(e).__name__}")
        raise
