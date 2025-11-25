import json
import os

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from .llm_provider import LLMProvider, PayloadTooLargeError
from .logger_config import get_logger, log_exception
from .utils import measure_time

logger = get_logger("gemini_provider")


class GeminiProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider for Google Gemini via Vertex AI.
    Handles Gemini-specific API calls, configuration, and error translation.
    """

    def __init__(self, config: dict, system_config: dict):
        super().__init__(config, system_config)
        self.config = config
        self.system_config = system_config
        self.provider_settings = config["provider_config"]["settings"]
        self.gemini_client = self._setup_gemini_client()
        self._output_schema = self.provider_settings["output_json"]

    @property
    def output_schema(self) -> dict:
        """
        Returns the output JSON schema for the provider.
        """
        return self._output_schema

    def _setup_gemini_client(self) -> genai.Client:
        """
        Sets up and returns a Google GenAI client configured for Vertex AI.
        """
        gcp_project = self.provider_settings.get("gcp_project")
        gcp_region = self.provider_settings.get(
            "gcp_region",
            self.system_config["default_gemini"]["gcp_region"]
        )

        if not gcp_project:
            gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not gcp_project:
                logger.error(
                    "No GCP project specified. Please set gcp_project in config or GOOGLE_CLOUD_PROJECT environment variable."
                )
                raise ValueError(
                    "GCP project not found. Please set gcp_project in config or GOOGLE_CLOUD_PROJECT environment variable."
                )

        # Handle credentials file if specified
        credentials_file = self.provider_settings.get("gcp_credentials_file")
        if credentials_file:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
            logger.info(f"Using credentials file: {credentials_file}")
        else:
            logger.info(
                "No credentials file specified, using Application Default Credentials (ADC)."
            )

        logger.info(f"Using GCP project: {gcp_project}")
        logger.info(f"Using GCP region: {gcp_region}")

        # Configure client for Vertex AI
        client = genai.Client(
            vertexai=True,
            project=gcp_project,
            location=gcp_region,
        )

        return client

    def _convert_schema_to_gemini_format(self, schema: dict) -> dict:
        """
        Converts JSON Schema from Bedrock-compatible format (lowercase types)
        to Gemini format (uppercase types).

        Args:
            schema: JSON Schema with lowercase type values

        Returns:
            JSON Schema with uppercase type values for Gemini API
        """
        if not isinstance(schema, dict):
            return schema

        converted = {}
        for key, value in schema.items():
            if key == "type" and isinstance(value, str):
                # Convert type to uppercase for Gemini
                converted[key] = value.upper()
            elif isinstance(value, dict):
                converted[key] = self._convert_schema_to_gemini_format(value)
            elif isinstance(value, list):
                converted[key] = [
                    self._convert_schema_to_gemini_format(item)
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                converted[key] = value

        return converted

    def invoke_single(self, prompt: str, modules_data: str | None) -> str:
        """
        Performs a single API call to the Google Gemini API via Vertex AI.
        Translates size-related errors into PayloadTooLargeError.
        """
        modules_enabled = self.config.get("modules", {}).get("enabled", True)
        modules_data_str = modules_data if (modules_data is not None) else ""

        final_system_prompt = (
            self.system_config["system_prompt"]
            + "\n"
            + self.provider_settings["system_prompt"]
        )
        final_system_prompt = final_system_prompt.replace(
            "{modules_data}", modules_data_str if modules_enabled else ""
        )

        logger.debug(f"Prompt: {prompt}")

        # Build generation config
        payload = self.provider_settings.get("payload", {})
        default_payload = self.system_config["default_gemini"]["payload"]

        # Convert output schema to Gemini format
        gemini_schema = self._convert_schema_to_gemini_format(self.output_schema)

        generation_config = types.GenerateContentConfig(
            system_instruction=final_system_prompt,
            max_output_tokens=payload.get(
                "max_tokens", default_payload["max_tokens"]
            ),
            temperature=payload.get(
                "temperature", default_payload["temperature"]
            ),
            top_p=payload.get("top_p", default_payload["top_p"]),
            top_k=payload.get("top_k", default_payload["top_k"]),
            response_mime_type="application/json",
            response_schema=gemini_schema,
        )

        try:
            model_name = self.provider_settings.get(
                "model_name",
                self.system_config["constants"]["gemini"]["default_model_name"]
            )
            with measure_time(f"Google Gemini API call: {model_name}", logger):
                response = self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=generation_config,
                )

            logger.debug(f"Gemini response:\n {response}")

            # Extract text from response
            if response.text:
                return response.text

            raise json.JSONDecodeError(
                "Invalid response format: empty response text", "", 0
            )

        except ClientError as e:
            # Translate Gemini-specific ClientError to common PayloadTooLargeError
            error_message = str(e).lower()
            if any(keyword in error_message for keyword in [
                "token", "limit", "too large", "exceeds", "maximum"
            ]):
                logger.warning(f"Gemini API call failed due to payload size: {e}")
                raise PayloadTooLargeError(f"Payload too large for Gemini: {e}") from e
            else:
                log_exception(logger, e, "Gemini client error")
                raise
        except Exception as e:
            log_exception(logger, e, "Unexpected error during Gemini invocation")
            raise
