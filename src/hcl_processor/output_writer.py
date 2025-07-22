import json
import logging
import os
import re

import jsonschema
from jinja2 import Environment, BaseLoader, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

logger = logging.getLogger(__name__)


def output_md(md_title, config):
    """
    Generate a Markdown file from the JSON output using Jinja2 templates.
    Args:
        md_title (str): The title for the Markdown file.
        config (dict): Configuration for the Markdown output.
    Raises:
        FileNotFoundError: If the JSON file or template file does not exist.
        ValueError: If the template configuration is invalid.
    """
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

    # Render template
    os.makedirs(os.path.dirname(config["output"]["markdown_path"]), exist_ok=True)
    try:
        rendered = template.render(
            title=md_title,
            data=filtered_data,
            columns=schema_columns
        )
        with open(config["output"]["markdown_path"], "a", encoding="utf-8") as md_file:
            logger.debug(f"Rendered Markdown:\n {rendered}")
            md_file.write(rendered + "\n")
        logger.info(f"Saved to Markdown file: {config['output']['markdown_path']}")
        logger.info(f"Deleting JSON file: {config['output']['json_path']}")
        if not logger.isEnabledFor(logging.DEBUG):
            os.remove(config["output"]["json_path"])
    except Exception as e:
        logger.debug(f"{e}")
        logger.error(f"Error writing Markdown output: {type(e).__name__}")
        raise


def get_default_template():
    """
    Returns the default Jinja2 template for Markdown output.
    """
    return """#### {{ title }}

| {% for col in columns %}{{ col }} | {% endfor %}
|{% for col in columns %}:---|{% endfor %}
{% for row in data %}| {% for col in columns %}{{ row[col] }} | {% endfor %}
{% endfor %}"""


def clean_cell(cell):
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
