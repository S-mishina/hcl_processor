import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 ReadTimeoutError)

from .llm_provider import LLMProvider, PayloadTooLargeError
from .logger_config import get_logger, log_exception
from .utils import measure_time

logger = get_logger("bedrock_provider")


class BedrockProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider for AWS Bedrock.
    Handles Bedrock-specific API calls, configuration, and error translation.
    """

    def __init__(self, config: dict, system_config: dict):
        super().__init__(config, system_config) # Call super with full config and system_config
        self.config = config # Store full config for non-provider specific items (e.g. modules)
        self.system_config = system_config
        self.provider_settings = config["provider_config"]["settings"] # Store specific provider settings
        self.bedrock_client = self._setup_bedrock_client()
        self._output_schema = self.provider_settings["output_json"] # Extract output_json from provider_settings
        self._schema_wrapped = False  # Track if array schema was wrapped in object

    @property
    def output_schema(self) -> dict:
        """
        Returns the output JSON schema for the provider.
        """
        return self._output_schema

    def _setup_bedrock_client(self):
        """
        Sets up and returns a boto3 Bedrock runtime client.
        """
        timeout_config = {
            "read_timeout": self.provider_settings.get( # Use provider_settings
                "read_timeout",
                self.system_config["default_bedrock"]["timeout_config"]["read_timeout"],
            ),
            "connect_timeout": self.provider_settings.get( # Use provider_settings
                "connect_timeout",
                self.system_config["default_bedrock"]["timeout_config"]["connect_timeout"],
            ),
            "retries": self.provider_settings.get( # Use provider_settings
                "retries",
                {
                    "max_attempts": self.system_config["default_bedrock"]["timeout_config"][
                        "retries"
                    ]["max_attempts"],
                    "mode": self.system_config["default_bedrock"]["timeout_config"]["retries"][
                        "mode"
                    ],
                },
            ),
        }
        bedrock_config = Config(**timeout_config)

        session = None
        if self.provider_settings.get("aws_profile") is not None: # Use provider_settings
            logger.info(
                f"Using AWS profile: {self.provider_settings.get('aws_profile')}" # Use provider_settings
            )
            session = boto3.Session(profile_name=self.provider_settings.get("aws_profile")) # Use provider_settings
        else:
            logger.info(
                "No AWS profile specified, using environment variables for credentials."
            )
            aws_access_key_id = self.provider_settings.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID") # Use provider_settings
            aws_secret_access_key = self.provider_settings.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY") # Use provider_settings
            aws_session_token = self.provider_settings.get("aws_session_token") or os.getenv("AWS_SESSION_TOKEN") # Use provider_settings
            if aws_access_key_id and aws_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                )
            else:
                logger.error(
                    "No AWS credentials provided. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
                )
                raise Exception("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")

        logger.info(
            f"Using AWS region: {self.provider_settings.get('aws_region','us-east-1')}" # Use provider_settings
        )
        return session.client(
            "bedrock-runtime", region_name=self.provider_settings.get('aws_region','us-east-1'), config=bedrock_config # Use provider_settings
        )

    def _build_tool_config(self) -> dict:
        """
        Builds the Bedrock-specific toolConfig for structured output.
        Bedrock Converse API requires inputSchema.json.type to be "object".
        If user's schema is an array type, wrap it in an object with a "data" property.
        """
        schema = self.output_schema
        # Bedrock Converse API requires inputSchema.json.type to be "object"
        if schema.get("type") == "array":
            wrapped_schema = {
                "type": "object",
                "properties": {
                    "data": schema
                },
                "required": ["data"]
            }
            self._schema_wrapped = True
            logger.debug("Array schema detected, wrapping in object for Bedrock API compatibility")
        else:
            wrapped_schema = schema
            self._schema_wrapped = False

        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": self.system_config["constants"]["bedrock"]["tool_name"],
                        "description": "Validates and formats JSON output",
                        "inputSchema": {
                            "json": wrapped_schema
                        }
                    }
                }
            ],
            "toolChoice": {
                "tool": {
                    "name": self.system_config["constants"]["bedrock"]["tool_name"]
                }
            }
        }
        return tool_config

    def invoke_single(self, prompt: str, modules_data: str | None) -> str:
        """
        Performs a single API call to the AWS Bedrock converse API.
        Translates size-related ClientErrors into PayloadTooLargeError.
        """
        modules_enabled = self.config.get("modules", {}).get("enabled", True) # Keep self.config for global modules config
        modules_data_str = modules_data if (modules_data is not None) else ""

        final_system_prompt = (
            self.system_config["system_prompt"]
            + "\n"
            + self.provider_settings["system_prompt"] # Use provider_settings
        )
        final_system_prompt = final_system_prompt.replace(
            "{modules_data}", modules_data_str if modules_enabled else ""
        )
        logger.debug(f"Prompt: {prompt}")
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system = [{"text": final_system_prompt}]

        inference_config = {
            "maxTokens": self.provider_settings["payload"].get( # Use provider_settings
                "max_tokens", self.system_config["default_bedrock"]["payload"]["max_tokens"]
            ),
            "temperature": self.provider_settings["payload"].get( # Use provider_settings
                "temperature", self.system_config["default_bedrock"]["payload"]["temperature"]
            ),
            "topP": self.provider_settings["payload"].get( # Use provider_settings
                "top_p", self.system_config["default_bedrock"]["payload"]["top_p"]
            )
        }

        tool_config = self._build_tool_config()

        try:
            model_id = self.provider_settings.get("model_id", self.system_config["constants"]["bedrock"]["default_model_id"]) # Use provider_settings
            with measure_time(f"AWS Bedrock API call: {model_id}", logger):
                response = self.bedrock_client.converse(
                    modelId=model_id,
                    messages=messages,
                    system=system,
                    inferenceConfig=inference_config,
                    toolConfig=tool_config
                )
            logger.debug(f"Bedrock response:\n {response}")

            # --- Response Parsing (from original bedrock_client.py) ---
            output = response.get("output", {})
            message = output.get("message", {})
            if message is None:
                logger.error(f"Response structure: {response}")
                raise AttributeError("Response message is None")
            content = message.get("content", [{}])[0]

            if "toolUse" in content:
                tool_use = content["toolUse"]
                logger.debug(f"Tool use response: {json.dumps(tool_use, indent=2, ensure_ascii=False)}")
                if tool_use["name"] == self.system_config["constants"]["bedrock"]["tool_name"]:
                    result = tool_use["input"]
                    # Unwrap if schema was wrapped for Bedrock API compatibility
                    if self._schema_wrapped and isinstance(result, dict) and "data" in result:
                        result = result["data"]
                        logger.debug("Unwrapping array data from object wrapper")
                    return json.dumps(result, ensure_ascii=False)

            if "text" in content:
                # Fallback to plain text if toolUse is not present
                return content.get("text", "")

            raise json.JSONDecodeError("Invalid response format: missing text or toolUse", "", 0)

        except ClientError as e:
            # ★ Translate Bedrock-specific ClientError to common PayloadTooLargeError
            if "Input token size exceeds limit" in str(e):
                logger.warning(f"Bedrock API call failed due to payload size: {e}")
                raise PayloadTooLargeError(f"Payload too large for Bedrock: {e}") from e
            else:
                log_exception(logger, e, "Bedrock client error")
                raise
        except EndpointConnectionError as e:
            log_exception(logger, e, "Bedrock endpoint connection failed")
            raise
        except ReadTimeoutError as e:
            log_exception(logger, e, "Bedrock read timeout")
            raise
        except Exception as e:
            log_exception(logger, e, "Unexpected error during Bedrock invocation")
            raise
