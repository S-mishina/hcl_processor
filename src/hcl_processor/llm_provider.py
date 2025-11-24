from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class PayloadTooLargeError(Exception):
    """Custom exception for when the payload to the LLM is too large."""
    pass


class LLMProvider(ABC):
    """
    Abstract Base Class defining the interface for all LLM providers.
    """
    def __init__(self, config: dict, system_config: dict):
        self.config = config
        self.system_config = system_config

    @abstractmethod
    def invoke_single(self, prompt: str, modules_data: str | None) -> str:
        """
        Performs a single API call to the specific LLM provider.
        This method must be implemented by concrete provider classes.
        It should raise PayloadTooLargeError if the input size is the cause of failure.

        Returns:
            str: The raw JSON string response from the LLM.
        """
        pass

    @property
    @abstractmethod
    def output_schema(self) -> dict:
        """
        Returns the output JSON schema for the provider.
        """
        pass
