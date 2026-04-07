"""Shared exceptions for synthesizer service modules."""

from __future__ import annotations


class LLMJsonValidationAbort(Exception):
    """Controlled abort when LLM JSON is invalid and policy disallows fallback."""

    def __init__(
        self,
        *,
        stage: str,
        reason: str,
        raw_output: str = "",
        retry_output: str = "",
    ) -> None:
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.reason = reason
        self.raw_output = raw_output
        self.retry_output = retry_output
