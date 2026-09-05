"""Application-facing LLM service for Anpurna Properties.

Business code imports this module instead of knowing which provider is used.
The provider implementation remains isolated in integrations/llm/client.py.
"""

from integrations.llm.client import LLMClient, LLMError

__all__ = ["LLMClient", "LLMError"]
