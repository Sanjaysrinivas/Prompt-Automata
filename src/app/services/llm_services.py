from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

import litellm
from flask import session

logger = logging.getLogger(__name__)


class BaseLLMService:
    def __init__(self):
        self.provider = None
        self.default_model = None
        logger.debug(f"Initialized {self.__class__.__name__}")

    def _get_token(self) -> str | None:
        """Get the API token for this provider from session."""
        try:
            token = session.get(f"{self.provider}_token")
            logger.debug(f"Retrieving token for {self.provider}")
            if token:
                logger.debug(f"Token found for {self.provider}")
                return token
            logger.warning(f"No token found for {self.provider}")
            return None
        except Exception:
            logger.exception(f"Error retrieving token for {self.provider}")
            return None

    def generate_completion(
        self, prompt: str, model: str | None = None
    ) -> dict[str, Any]:
        """Generate completion using litellm."""
        try:
            logger.debug(f"Generating completion with {self.provider}")
            token = self._get_token()
            if not token:
                error_msg = f"No token found for provider: {self.provider}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            model_name = model or self.default_model
            logger.debug(f"Using model: {model_name}")

            logger.debug(f"Sending request to {self.provider}")
            response = litellm.completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                api_key=token,
            )
            logger.debug(f"Received response from {self.provider}")

            return self._standardize_response(response)
        except Exception as e:
            logger.exception(f"{self.provider} completion error: {e!s}")
            raise

    def generate_stream(
        self, prompt: str, model: str | None = None
    ) -> Generator[str, None, None]:
        """Stream completion using litellm."""
        try:
            logger.debug(f"Starting stream generation with {self.provider}")
            token = self._get_token()
            if not token:
                error_msg = f"No token found for provider: {self.provider}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            model_name = model or self.default_model
            logger.debug(f"Using model: {model_name}")

            logger.debug(f"Starting stream request to {self.provider}")
            response = litellm.completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                api_key=token,
                stream=True,
            )

            logger.debug(f"Stream established with {self.provider}")
            for chunk in response:
                if hasattr(chunk.choices[0], "delta"):
                    content = chunk.choices[0].delta.content
                else:
                    content = chunk.choices[0].message.content
                if content:
                    logger.debug(
                        f"Received chunk from {self.provider}: {content[:50]}..."
                    )  # Log first 50 chars
                    yield content

        except Exception as e:
            logger.exception(f"{self.provider} streaming error: {e!s}")
            raise

    def _standardize_response(self, response: Any) -> dict[str, Any]:
        """Standardize the response format."""
        try:
            logger.debug(f"Standardizing response from {self.provider}")
            standardized = {
                "content": response.choices[0].message.content,
                "model": response.model,
                "provider": self.provider,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
            logger.debug(
                f"Response standardized. Total tokens: {standardized['usage']['total_tokens']}"
            )
            return standardized
        except Exception as e:
            logger.exception(f"Error standardizing response: {e!s}")
            raise


class OpenAIService(BaseLLMService):
    def __init__(self):
        super().__init__()
        self.provider = "openai"
        self.default_model = "gpt-4"
        logger.debug("OpenAI service initialized")


class AnthropicService(BaseLLMService):
    def __init__(self):
        super().__init__()
        self.provider = "anthropic"
        self.default_model = "claude-3.5-sonnet"
        logger.debug("Anthropic service initialized")


class GoogleService(BaseLLMService):
    def __init__(self):
        super().__init__()
        self.provider = "google"
        self.default_model = "gemini/gemini-1.5-pro"
        logger.debug("Google service initialized")
