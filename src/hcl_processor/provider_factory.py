from .llm_provider import LLMProvider # Import LLMProvider abstract class
from .bedrock_client import BedrockProvider # Import BedrockProvider concrete class
from .gemini_client import GeminiProvider # Import GeminiProvider concrete class


def create_llm_provider(config: dict, system_config: dict) -> LLMProvider:
    """
    Factory function to create an LLMProvider instance based on configuration.
    It expects a normalized config with a 'provider_config' key.
    Supports BedrockProvider and GeminiProvider.
    """
    provider_name = config["provider_config"]["name"]
    # The provider constructor might need the full config for non-provider-specific settings
    # (e.g., 'modules'), so we pass the full config object.

    if provider_name == "bedrock":
        return BedrockProvider(config, system_config)
    elif provider_name == "gemini":
        return GeminiProvider(config, system_config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
