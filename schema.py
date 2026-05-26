"""
Structured output shape for Gemini (JSON schema).

Edit this file when you change labels, scores, or fields you want back from the model.
Keep the model **flat** (nested models can work, but flat is easiest to tune).
"""

from typing import Literal

from pydantic import BaseModel, Field

# --- Tweak: allowed labels (must match what you describe in prompts/*.md) ---
PrimaryLabel = Literal[
    "very_negative",
    "negative",
    "neutral",
    "positive",
    "very_positive",
]

Aspect = Literal[
    "ui",
    "performance",
    "support",
    "transfers",
    "fees",
    "kyc",
    "notifications",
    "crashes",
    "login",
    "security",
    "cards",
    "rewards",
    "other",
]


class ClassificationOutput(BaseModel):
    """One classification result per input document."""

    primary_label: PrimaryLabel = Field(
        description="Single best-matching label from the allowed set."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence in the chosen label.",
    )
    rationale: str = Field(
        description="Brief justification grounded in the document text.",
    )
    aspects: list[Aspect] = Field(
        default_factory=list,
        description="Relevant app-review aspects mentioned by the reviewer.",
        max_length=6,
    )
    improvement_signals: list[str] = Field(
        default_factory=list,
        description="Up to five short phrases capturing what the user wants fixed or improved.",
        max_length=5,
    )
    language: str = Field(
        description="BCP-47 language code for the review text, for example en, es, de, fr, or pt.",
    )


def response_json_schema() -> dict:
    """JSON Schema passed to Gemini (`response_json_schema` config)."""
    return ClassificationOutput.model_json_schema()
