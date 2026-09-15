"""
Thin client for a local Ollama instance.

This is the one deliberately non-deterministic component in the DeepCore
kernel. Every layer below this (Registry, Context Engine, Planner, etc.)
must stay deterministic per the Development Protocol; this module is the
single, isolated seam where a probabilistic reasoning model is allowed in,
and only to turn an already-deterministic ContextPackage into a natural
language answer.
"""
import httpx

from deepcore2.config import settings


class LLMUnavailableError(Exception):
    """Raised when the configured local LLM cannot be reached or errors out."""
    pass


class OllamaClient:
    """Minimal synchronous client for Ollama's /api/generate endpoint."""

    def __init__(self, host: str = None, model: str = None, timeout: float = None):
        self.host = (host or settings.OLLAMA_HOST).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS

    def generate(self, prompt: str) -> str:
        """Send a prompt to the local model and return the generated text.

        Raises LLMUnavailableError (never a raw httpx exception) so callers
        can degrade gracefully instead of crashing the conversation turn.
        """
        try:
            response = httpx.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Could not reach Ollama at {self.host}. "
                f"Is 'ollama serve' running? ({exc})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(
                f"Ollama at {self.host} timed out after {self.timeout}s "
                f"generating with model '{self.model}'."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMUnavailableError(
                f"Ollama returned {exc.response.status_code} for model "
                f"'{self.model}': {exc.response.text[:300]}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMUnavailableError(
                f"Ollama returned a non-JSON response: {response.text[:300]}"
            ) from exc

        return (data.get("response") or "").strip()

    def chat(
        self,
        messages: list,
        tools: list = None,
    ) -> dict:
        """Send a structured chat request to Ollama with optional function calling tools.

        Returns the response message dict (e.g. {'role': 'assistant', 'content': '...', 'tool_calls': [...]}).
        Raises LLMUnavailableError on network, timeout, or server failures.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            response = httpx.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Could not reach Ollama at {self.host}. Is 'ollama serve' running? ({exc})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(
                f"Ollama at {self.host} timed out after {self.timeout}s during chat with '{self.model}'."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMUnavailableError(
                f"Ollama returned {exc.response.status_code} for model '{self.model}': {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise LLMUnavailableError(
                f"Unexpected error communicating with Ollama: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMUnavailableError(
                f"Ollama returned a non-JSON response: {response.text[:300]}"
            ) from exc

        return data.get("message", {"role": "assistant", "content": ""})
