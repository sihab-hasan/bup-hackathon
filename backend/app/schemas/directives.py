from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import DirectiveType


class DirectiveInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_index: int = Field(ge=0)
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: dict[str, Any] | None
    explanation: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def normalize_explanation(self) -> DirectiveInterpretation:
        self.explanation = self.explanation.strip()
        if not self.explanation:
            raise ValueError("explanation cannot be blank")
        return self
