import json
import logging
from copy import deepcopy

import jsonschema
import yaml

from .config.system_config import get_system_config

logger = logging.getLogger(__name__)


def get_default_config():
    """
    Returns the default configuration for the HCL processor.
    """
    return {
        "output": {
            "template": """#### {{ title }}

{% if description %}{{ description }}{% endif %}

| {% for col in columns %}{{ col }} |{% endfor %}
|{% for col in columns %}:---|{% endfor %}
{% for row in data %}| {% for col in columns %}{{ row[col] }} |{% endfor %}
{% endfor %}""",
        },
        "schema_columns": [
            "name",
            "description",
            "severity",
            "threshold",
            "evaluation_period"
        ]
    }


def merge_defaults(config, defaults):
    """
    Recursively merge default values into config.
    Args:
        config (dict): Configuration to update
        defaults (dict): Default values to merge
    Returns:
        dict: Updated configuration
    """
    result = deepcopy(config)
    for key, value in defaults.items():
        if key not in result:
            result[key] = deepcopy(value)
        elif isinstance(value, dict) and isinstance(result[key], dict):
            result[key] = merge_defaults(result[key], value)
    return result


def load_system_config(system_config=get_system_config()):
    """
    Load the system configuration from a config/system_config.py file.
    Args:
        system_config_path (str): Path to the system configuration file.
    Returns:
        dict: Parsed system configuration.
    Raises:
        ValueError: If the system configuration file is not found or cannot be loaded.
    """

    if system_config is None:
        logger.warning(
            "system_config.yaml is empty or could not be loaded, returning None"
        )
        raise ValueError("System config is None")

    if not isinstance(system_config, dict):
        logger.error(
            "system_config.yaml does not contain a valid dictionary, returning None"
        )
        raise ValueError("System config is not a dictionary")

    if "system_prompt" not in system_config or not isinstance(
        system_config["system_prompt"], str
    ):
        logger.warning(
            "system_prompt key missing or not a string in system_config, returning None"
        )
        raise ValueError("System prompt is missing or not a string")

    return system_config


def load_config(config_path):
    """
    Load the configuration from a YAML file.
    Args:
        config_path (str): Path to the configuration YAML file.
    Returns:
        dict: Parsed configuration.
    Raises:
        ValueError: If the configuration file is not found or cannot be loaded.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.debug(f"Loaded config:\n {config}")

    # Load default configuration
    default_config = get_default_config()

    # Define schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "bedrock": {
                "type": "object",
                "properties": {
                    "aws_profile": {"type": "string"},
                    "aws_region": {"type": "string"},
                    "model_id": {"type": "string"},
                    "system_prompt": {"type": "string"},
                    "payload": {
                        "type": "object",
                        "properties": {
                            "anthropic_version": {"type": "string"},
                            "max_tokens": {"type": "integer"},
                            "temperature": {"type": "number"},
                            "top_p": {"type": "number"},
                            "top_k": {"type": "number"},
                        },
                        "required": [
                            "anthropic_version",
                            "max_tokens",
                            "temperature",
                            "top_p",
                            "top_k",
                        ],
                    },
                    "read_timeout": {"type": "integer"},
                    "connect_timeout": {"type": "integer"},
                    "retries": {"type": "object"},
                    "output_json": {"type": "object"},
                },
                "required": ["system_prompt", "payload", "output_json"],
            },
            "input": {
                "type": "object",
                "properties": {
                    "resource_data": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "files": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                },
                                "required": ["files"],
                                "not": {"required": ["folder"]},
                            },
                            {
                                "properties": {"folder": {"type": "string"}},
                                "required": ["folder"],
                                "not": {"required": ["files"]},
                            },
                        ],
                    },
                    "modules": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "enabled": {"type": "boolean"},
                        },
                        "required": ["enabled"],
                    },
                    "local_files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "failback": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "type": {"type": "string", "enum": ["resource", "modules"]},
                            "options": {
                                "type": "object",
                                "properties": {"target": {"type": "string"}},
                                "required": ["target"],
                            },
                        },
                        "required": ["enabled", "type"],
                        "allOf": [
                            {
                                "if": {"properties": {"type": {"const": "modules"}}},
                                "then": {"required": ["options"]},
                            },
                            {
                                "if": {"properties": {"type": {"const": "resource"}}},
                                "then": {"not": {"required": ["options"]}},
                            },
                        ],
                    },
                },
                "required": ["resource_data", "modules", "local_files"],
            },
            "schema_columns": {
                "type": "array",
                "items": {"type": "string"}
            },
            "output": {
                "type": "object",
                "properties": {
                    "json_path": {"type": "string"},
                    "markdown_path": {"type": "string"},
                    "template": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"}
                                },
                                "required": ["path"]
                            }
                        ]
                    }
                },
                "required": ["json_path", "markdown_path"],
            },
        },
        "required": ["bedrock", "input", "output"],
    }

    if "bedrock" in config and "output_json" in config["bedrock"]:
        if isinstance(config["bedrock"]["output_json"], str):
            try:
                config["bedrock"]["output_json"] = json.loads(
                    config["bedrock"]["output_json"]
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in output_json: {e}")

    try:
        # First validate the base configuration
        jsonschema.validate(instance=config, schema=schema)
        
        # Then merge with defaults
        config = merge_defaults(config, default_config)
        
        logger.debug(f"Config after merging defaults:\n {config}")
        return config
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid configuration: {e.message}")
