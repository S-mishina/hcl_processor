from .llm_provider import LLMProvider # Import LLMProvider abstract class
from .bedrock_client import BedrockProvider # Import BedrockProvider concrete class


def create_llm_provider(config: dict, system_config: dict) -> LLMProvider:
    """
    Factory function to create an LLMProvider instance based on configuration.
    It expects a normalized config with a 'provider_config' key.
    Currently only supports BedrockProvider.
    """
    provider_name = config["provider_config"]["name"]
    # The provider constructor might need the full config for non-provider-specific settings
    # (e.g., 'modules'), so we pass the full config object.

    if provider_name == "bedrock":
        return BedrockProvider(config, system_config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")