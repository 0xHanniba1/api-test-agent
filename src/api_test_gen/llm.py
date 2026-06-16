"""LLM client wrapper around litellm.

Provides a unified interface for calling any LLM model supported by litellm,
with a per-request timeout, bounded retries, and response validation so that
network hiccups or empty completions surface as a clear error instead of
crashing deep inside the generation pipeline.
"""

from litellm import completion

DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_NUM_RETRIES = 2


class LlmError(RuntimeError):
    """Raised when the LLM request fails or returns no usable content."""


class LlmClient:
    """Wrapper for LLM API calls via litellm."""

    def __init__(
        self,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        num_retries: int = DEFAULT_NUM_RETRIES,
    ):
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self.num_retries = num_retries

    def call(self, system: str, user: str) -> str:
        """Send a system+user message to the LLM and return the response text.

        Retries transient failures up to ``num_retries`` times and aborts each
        attempt after ``timeout`` seconds.

        Raises:
            LlmError: if the request fails or the response carries no text.
        """
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=self.timeout,
                num_retries=self.num_retries,
            )
        except Exception as error:
            raise LlmError(
                f"LLM request failed for model {self.model!r}: {error}"
            ) from error

        content = response.choices[0].message.content
        if content is None or not content.strip():
            raise LlmError(f"LLM returned empty response for model {self.model!r}")
        return content
