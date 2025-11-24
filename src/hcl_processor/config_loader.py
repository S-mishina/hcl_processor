import json
from copy import deepcopy

import jsonschema
import yaml

from .config.system_config import get_system_config
from .utils import measure_time
from .logger_config import get_logger

logger = get_logger("config_loader")

# Constants for schema definitions
BEDROCK_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
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
            "required": ["anthropic_version", "max_tokens", "temperature", "top_p", "top_k"],
        },
        "read_timeout": {"type": "integer"},
        "connect_timeout": {"type": "integer"},
        "retries": {"type": "object"},
        "output_json": {"type": "object"},
        "aws_profile": {"type": "string"},
        "aws_region": {"type": "string"},
        "model_id": {"type": "string"},
    },
    "required": ["system_prompt", "payload", "output_json"],
    "additionalProperties": False
}

PROVIDER_KEYS = ["bedrock"] # This will be extended for other providers later

CONFIG_SCHEMA_BASE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "provider_config": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "enum": PROVIDER_KEYS},
                "settings": {"type": "object"} # This will be replaced with specific schema later
            },
            "required": ["name", "settings"],
        },
        "input": {
            "type": "object",
            "properties": {
                "resource_data": {
                    "type": "object",
                    "oneOf": [
                        {"required": ["files"], "properties": {"files": {"type": "array", "items": {"type": "string"}}}},
                        {"required": ["folder"], "properties": {"folder": {"type": "string"}}}
                    ]
                },
                "modules": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "enabled": {"type": "boolean"}},
                    "required": ["enabled"]
                },
                "local_files": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": {"type": "string"}}
                },
                "failback": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "type": {"type": "string", "enum": ["resource", "modules"]},
                        "options": {
                            "type": "object",
                            "properties": {"target": {"type": "string"}},
                            "required": ["target"]
                        }
                    },
                    "required": ["enabled", "type"]
                },
            },
            "required": ["resource_data", "modules", "local_files"]
        },
        "schema_columns": {"type": "array", "items": {"type": "string"}},
        "output": {
            "type": "object",
            "properties": {
                "json_path": {"type": "string"},
                "markdown_path": {"type": "string"},
                "template": {"oneOf": [{"type": "string"}, {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}]}
            },
            "required": ["json_path", "markdown_path"]
        },
    },
    "required": ["provider_config", "input", "output"],
    "additionalProperties": False
}


def get_default_config() -> dict:
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


def merge_defaults(config: dict, defaults: dict) -> dict:
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


def load_system_config(system_config: dict = get_system_config()) -> dict:
    """
    Load the system configuration from a config/system_config.py file.
    Args:
        system_config_path (str): Path to the system configuration file.
    Returns:
        dict: Parsed system configuration.
    Raises:
        ValueError: If the system configuration file is not found or cannot be loaded.
    """
    with measure_time("System configuration loading", logger):
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

        logger.debug("System configuration validation passed")
        logger.debug(f"System config contains {len(system_config)} top-level keys")
        return system_config


def load_config(config_path: str) -> dict:
    """
    Load the configuration from a YAML file, validate it, and normalize provider-specific settings.
    Args:
        config_path (str): Path to the configuration YAML file.
    Returns:
        dict: Parsed and normalized configuration.
    Raises:
        ValueError: If the configuration file is not found, cannot be loaded, or is invalid.
    """
    with measure_time(f"Configuration loading: {config_path}", logger):
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
        logger.debug(f"Loaded raw config:\n {raw_config}")

        # --- 1. Identify active provider and validate exclusivity (Pattern D-config) ---
        active_provider_name = None
        found_providers = [key for key in PROVIDER_KEYS if key in raw_config]

        if len(found_providers) == 0:
            raise ValueError(f"Invalid configuration: No LLM provider (e.g., '{PROVIDER_KEYS[0]}') specified at the top level. Supported providers: {', '.join(PROVIDER_KEYS)}")
        elif len(found_providers) > 1:
            raise ValueError(f"Invalid configuration: Multiple LLM providers specified at the top level: {', '.join(found_providers)}. Only one is allowed.")

        active_provider_name = found_providers[0]
        # Get provider-specific settings without removing from raw_config yet
        provider_specific_settings = raw_config[active_provider_name]

        # --- 2. Create normalized config (internal representation) ---
        # Initialize config_for_internal_use with provider_config and other expected top-level keys
        config_for_internal_use = {
            "provider_config": {
                "name": active_provider_name,
                "settings": provider_specific_settings
            }
        }
        # Copy other allowed top-level keys from raw_config
        allowed_top_level_keys = ["input", "output", "schema_columns"]
        for key in allowed_top_level_keys:
            if key in raw_config:
                config_for_internal_use[key] = raw_config[key]

        # Check for any unexpected top-level keys in raw_config that are not "active_provider_name" or "allowed_top_level_keys"
        # This acts as an additional check for extraneous keys that are not provider or common config
        for key in raw_config:
            if key != active_provider_name and key not in allowed_top_level_keys and key not in PROVIDER_KEYS: # Add PROVIDER_KEYS to avoid checking against itself if multiple are present
                raise ValueError(f"Invalid configuration: Unexpected top-level key '{key}' found. Only one LLM provider key and keys like {', '.join(allowed_top_level_keys)} are allowed.")


        config = config_for_internal_use
        logger.debug(f"Normalized config (internal representation for validation):\n {config}")

        # Load default configuration
        default_config = get_default_config()

        # --- 3. Dynamically construct the schema based on the active provider ---
        current_schema = deepcopy(CONFIG_SCHEMA_BASE)

        if active_provider_name == "bedrock":
            current_schema["properties"]["provider_config"]["properties"]["settings"] = BEDROCK_PROVIDER_SCHEMA
        else:
            raise ValueError(f"Unsupported provider: {active_provider_name}")


        # Handle output_json conversion before validation
        if "output_json" in config["provider_config"]["settings"] and isinstance(config["provider_config"]["settings"]["output_json"], str):
            try:
                config["provider_config"]["settings"]["output_json"] = json.loads(config["provider_config"]["settings"]["output_json"])
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in provider_config.settings.output_json: {e}")

        try:
            jsonschema.validate(instance=config, schema=current_schema)
            logger.debug("Configuration schema validation passed")

            config = merge_defaults(config, default_config)
            logger.debug("Configuration merged with defaults")

            logger.debug(f"Config after merging defaults:\n {config}")
            return config
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid configuration: {e.message}")
