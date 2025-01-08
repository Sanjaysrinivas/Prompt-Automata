from __future__ import annotations

import logging
from typing import Any

import litellm
from flask import has_request_context, session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    PROVIDER_MODELS = {
        "anthropic": "claude-3.5-sonnet",
        "openai": "gpt-4",
        "google": "gemini-1.5-pro-1m",
    }

    def __init__(self):
        self.completion_map = {
            "anthropic": self._anthropic_completion,
            "openai": self._openai_completion,
            "google": self._google_completion,
        }
        self._token = None

    def set_token(self, token: str) -> None:
        """Set the token for the current service instance."""
        self._token = token

    def _get_provider_token(self, provider: str) -> str | None:
        """Get and validate the API token for a provider from session or instance."""
        try:
            if self._token:
                return self._token

            if not has_request_context():
                logger.warning("Attempted to access session outside request context")
                return None

            token_key = f"{provider}_token"
            token = session.get(token_key)
            logger.info(f"Retrieving token for {provider} with key {token_key}")

            if not token:
                logger.warning(f"No token data found for {provider}")
                return None

            logger.info(f"Validating token for {provider}")
            from src.app.routes.llm_token_management import validate_llm_token

            is_valid, error = validate_llm_token(provider, token)

            if not is_valid:
                logger.warning(f"Token validation failed for {provider}: {error}")
                session.pop(token_key, None)
                return None

            logger.info(f"Token validated successfully for {provider}")
            return token

        except Exception as e:
            logger.exception(f"Error retrieving/validating token for {provider}: {e!s}")
            return None

    def _anthropic_completion(self, prompt: str, token: str) -> dict[str, Any]:
        """Handle Anthropic completion."""
        try:
            response = litellm.completion(
                model=self.PROVIDER_MODELS["anthropic"],
                messages=[{"role": "user", "content": prompt}],
                api_key=token,
                timeout=60,
            )
            return self._standardize_response(response)
        except Exception as e:
            logger.exception(f"Anthropic completion error: {e!s}")
            raise

    def _openai_completion(self, prompt: str, token: str) -> dict[str, Any]:
        """Handle OpenAI completion."""
        try:
            response = litellm.completion(
                model=self.PROVIDER_MODELS["openai"],
                messages=[{"role": "user", "content": prompt}],
                api_key=token,
                timeout=60,
            )
            return self._standardize_response(response)
        except Exception as e:
            logger.exception(f"OpenAI completion error: {e!s}")
            raise

    def _google_completion(self, prompt: str, token: str) -> dict[str, Any]:
        """Handle Google completion."""
        try:
            response = litellm.completion(
                model=self.PROVIDER_MODELS["google"],
                messages=[{"role": "user", "content": prompt}],
                api_key=token,
                timeout=60,
            )
            return self._standardize_response(response)
        except Exception as e:
            logger.exception(f"Google completion error: {e!s}")
            raise

    def _standardize_response(self, response: Any) -> dict[str, Any]:
        """Standardize the response format across all providers."""
        try:
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "provider": response.model.split("/")[0]
                if "/" in response.model
                else response.model.split("-")[0],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except Exception as e:
            logger.exception(f"Error standardizing response: {e!s}")
            raise

    def generate_completion(self, provider: str, prompt: str) -> dict[str, Any]:
        """Generate completion using the specified provider."""
        try:
            token = self._get_provider_token(provider)
            if not token:
                raise ValueError(f"No token found for provider: {provider}")

            completion_func = self.completion_map.get(provider)
            if not completion_func:
                raise ValueError(f"Unsupported provider: {provider}")

            return completion_func(prompt, token)

        except Exception as e:
            logger.exception(f"Error generating completion: {e!s}")
            raise

    def generate_stream(self, provider: str, prompt: str) -> Any:
        """Generate streaming completion using the specified provider."""
        try:
            logger.info(f"Starting stream generation for provider: {provider}")
            token = self._get_provider_token(provider)
            if not token:
                logger.error(f"No token found for provider: {provider}")
                raise ValueError(f"No token found for provider: {provider}")

            model = self.PROVIDER_MODELS.get(provider)
            if not model:
                logger.error(f"Unsupported provider: {provider}")
                raise ValueError(f"Unsupported provider: {provider}")

            logger.info(f"Using model {model} for provider {provider}")

            logger.info("Starting litellm streaming completion")
            messages = [{"role": "user", "content": prompt}]
            logger.debug(f"Sending messages: {messages}")
            logger.info(f"Total prompt length: {len(prompt)} characters")
            logger.debug(f"Full prompt content: {prompt[:500]}...")

            buffer = []
            buffer_size = 0
            max_buffer_size = 100

            for chunk in litellm.completion(
                model=model,
                messages=messages,
                api_key=token,
                timeout=60,
                stream=True,
            ):
                try:
                    if hasattr(chunk.choices[0], "delta"):
                        content = chunk.choices[0].delta.content
                    else:
                        content = chunk.choices[0].text

                    if content:
                        buffer.append(content)
                        buffer_size += len(content)

                        if buffer_size >= max_buffer_size or any(
                            p in content for p in [".", "!", "?", "\n"]
                        ):
                            combined_content = "".join(buffer)
                            logger.debug(
                                f"Yielding buffered content: {combined_content[:50]}..."
                            )
                            yield combined_content
                            buffer = []
                            buffer_size = 0

                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    continue

            if buffer:
                combined_content = "".join(buffer)
                logger.debug(
                    f"Yielding final buffered content: {combined_content[:50]}..."
                )
                yield combined_content

        except Exception as e:
            logger.exception(f"Error in generate_stream: {e!s}")
            raise
