"""Local Ollama claim extraction; never executes reported code."""

from .extraction import (
    ClaimExtractionResult,
    ExtractionError,
    OllamaSettings,
    extract_claims,
)

__all__ = [
    "ClaimExtractionResult",
    "ExtractionError",
    "OllamaSettings",
    "extract_claims",
]
