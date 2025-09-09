import json
import logging
import os
import re

import jsonschema
from jinja2 import Environment, BaseLoader, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

from .utils import ensure_directory_exists, measure_time
from .logger_config import get_logger, log_exception

logger = get_logger("output_writer")


def output_md(md_title: str, config: dict) -> None:
    """
    Generate a Markdown file from the JSON output using Jinja2 templates.
    Args:
        md_title (str): The title for the Markdown file.
        config (dict): Configuration for the Markdown output.
    Raises:
        FileNotFoundError: If the JSON file or template file does not exist.
        ValueError: If the template configuration is invalid.
    """
    with measure_time(f"Markdown generation: {md_title}", logger):
        # Load and validate JSON data
        with open(config["output"]["json_path"], "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, str):
            data = json.loads(data)

        # Convert data to list if it's a dictionary
        if isinstance(data, dict):
            data = [data]

        # Filter data to include only schema columns
        schema_columns = config.get("schema_columns", [])
        filtered_data = []
        for item in data:
            filtered_item = {col: clean_cell(item.get(col, '')) for col in schema_columns}
            filtered_data.append(filtered_item)

        logger.debug(f"Processing {len(filtered_data)} data items with {len(schema_columns)} columns")

        # Setup template environment
        env = Environment(loader=BaseLoader(), autoescape=False)

        # Get template content
        template_config = config["output"].get("template")
        if isinstance(template_config, dict) and template_config.get("path"):
            # Load template from file
            template_dir = os.path.dirname(template_config["path"])
            template_file = os.path.basename(template_config["path"])
            env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
            try:
                template = env.get_template(template_file)
                logger.debug(f"Loaded template from file: {template_config['path']}")
            except TemplateNotFound as e:
                logger.error(f"Template file not found: {e}")
                raise ValueError(f"Template file not found: {str(e)}")
            except TemplateSyntaxError as e:
                logger.error(f"Syntax error in template file: {e}")
                raise ValueError(f"Syntax error in template file: {str(e)}")
        else:
            # Use template string from config or default template
            template_str = template_config if isinstance(template_config, str) else get_default_template()
            template = env.from_string(template_str)
            logger.debug("Using default template or config template string")

        # Render template
        ensure_directory_exists(config["output"]["markdown_path"])
        try:
            rendered = template.render(
                title=md_title,
                data=filtered_data,
                columns=schema_columns
            )
            rendered_size_kb = len(rendered) / 1024
            logger.debug(f"Rendered Markdown size: {rendered_size_kb:.2f} KB")

            with open(config["output"]["markdown_path"], "a", encoding="utf-8") as md_file:
                logger.debug(f"Rendered Markdown:\n {rendered}")
                md_file.write(rendered + "\n")
            logger.info(f"Saved to Markdown file: {config['output']['markdown_path']}")
            logger.info(f"Deleting JSON file: {config['output']['json_path']}")
            if not logger.isEnabledFor(logging.DEBUG):
                os.remove(config["output"]["json_path"])
        except Exception as e:
            log_exception(logger, e, "Error writing Markdown output")
            raise


def get_default_template() -> str:
    """
    Returns the default Jinja2 template for Markdown output.
    """
    return """#### {{ title }}

| {% for col in columns %}{{ col }} | {% endfor %}
|{% for col in columns %}:---|{% endfor %}
{% for row in data %}| {% for col in columns %}{{ row[col] }} | {% endfor %}
{% endfor %}"""


def clean_cell(cell) -> str:
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
    return str(cell) if cell is not None else ''


def validate_output_json(output_str: str, schema: dict) -> dict | list:
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
    with measure_time(f"JSON validation (size: {len(output_str)//1024:.1f}KB)", logger):
        try:
            parsed = json.loads(output_str)
            logger.debug(f"JSON parsed successfully: {len(parsed) if isinstance(parsed, list) else 1} items")
            jsonschema.validate(instance=parsed, schema=schema)
            logger.debug("JSON schema validation passed")
            return parsed
        except json.JSONDecodeError as e:
            log_exception(logger, e, "Invalid JSON format")
            raise
        except jsonschema.ValidationError as e:
            log_exception(logger, e, "Output JSON does not match schema")
            raise
